from __future__ import annotations

import hashlib
import hmac
import os
import pickle
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, Literal

import jwt
from fastapi import Depends, FastAPI, HTTPException, Query, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field

from .services.chatbot_service import answer as chatbot_answer
from .services.data_store import alert_details, daily_weather_for, indices_for, load_wards, ward_or_404, weather_for
from .services.thermal_engine import ThermalStressEngine, WeatherInput

ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = next((candidate for candidate in (PACKAGE_ROOT / "data", ROOT / "data") if candidate.exists()), PACKAGE_ROOT / "data")
MODEL_ROOT = next((candidate for candidate in (PACKAGE_ROOT / "ml-models", ROOT / "ml-models") if candidate.exists()), PACKAGE_ROOT / "ml-models")
DB_PATH = Path(os.getenv("TAAP_DATABASE_PATH", "/tmp/taap_kavach.db" if os.getenv("VERCEL") else str(ROOT / "data" / "taap_kavach.db")))
MODEL_PATH = MODEL_ROOT / "xgboost_model.pkl"
JWT_SECRET = os.getenv("TAAP_JWT_SECRET", "local-prototype-secret-change-me")
ALGORITHM = "HS256"
security = HTTPBearer(auto_error=False)

app = FastAPI(title="Taap Kavach API", version="1.1.0", description="Bhopal ward-level thermal stress monitoring using supplied MET Norway and ward-interpolated data.")
origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://taap-kavach.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def password_hash(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 120_000)
    return f"{salt.hex()}${digest.hex()}"


def password_matches(password: str, stored: str) -> bool:
    salt, expected = stored.split("$", 1)
    actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 120_000).hex()
    return hmac.compare_digest(actual, expected)


def db() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, user_type TEXT NOT NULL, organization TEXT NOT NULL)")
    return connection


def init_users() -> None:
    connection = db()
    demos = [("ADMIN_001", "admin.bhopal@taapkavach.gov.in", "demo-admin", "local_administration", "Bhopal Municipal Corporation"),
             ("HEALTH_001", "healthcare.hospital@taapkavach.gov.in", "demo-health", "healthcare_facility", "Bhopal Medical College")]
    for user in demos:
        connection.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?, ?)", (user[0], user[1], password_hash(user[2]), user[3], user[4]))
    connection.commit(); connection.close()


@app.on_event("startup")
def startup() -> None:
    init_users()


def token_for(row: sqlite3.Row) -> str:
    payload = {"sub": row["user_id"], "email": row["email"], "user_type": row["user_type"], "exp": datetime.now(timezone.utc) + timedelta(hours=24)}
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)


def current_user(credentials: Annotated[HTTPAuthorizationCredentials | None, Security(security)]) -> dict:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        return jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[ALGORITHM])
    except jwt.PyJWTError as error:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from error


def require_role(role: str):
    def dependency(user: Annotated[dict, Depends(current_user)]) -> dict:
        if user.get("user_type") != role:
            raise HTTPException(status_code=403, detail=f"Requires {role} access")
        return user
    return dependency


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class RegisterRequest(LoginRequest):
    user_type: Literal["local_administration", "healthcare_facility"]
    organization_name: str = Field(min_length=2, max_length=120)
    ward_jurisdiction: list[str] = Field(default_factory=list)


class WeatherInputPayload(BaseModel):
    temperature: float
    humidity: float
    wind_speed: float
    atmospheric_pressure: float
    uv_index: float
    solar_radiation: float


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=500)
    ward_id: str = Field(pattern=r"^BPL_W\d{3}$")


@app.get("/", tags=["System"])
def root() -> dict:
    return {"name": "Taap Kavach API", "status": "prototype", "data_source": "MET Norway observations with ward-level interpolation", "disclaimer": "Data is supplied prototype analysis; not an official IMD or medical system."}


@app.get("/api/health", tags=["System"])
def health() -> dict:
    return {"status": "ok", "data_mode": "supplied_real_world_snapshot", "period": "2026-09-14 to 2026-09-18"}


@app.post("/api/chat", tags=["Assistant"])
def chat(request: ChatRequest) -> dict:
    try:
        return chatbot_answer(request.question, request.ward_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=f"Unknown Bhopal ward: {request.ward_id}") from error


@app.get("/api/bhopal/wards", tags=["Wards"])
def wards() -> dict:
    return {"city": "Bhopal", "wards": [{"ward_id": w["ward_id"], "ward_name": w["ward_name"], "zone": w["zone"], "population_count": w["population"], "primary_demographics": {"elderly_percent": w["elderly_percentage"], "outdoor_workers_percent": w["outdoor_workers_percentage"]}, **w} for w in load_wards()]}


def validate_ward(ward_id: str) -> dict:
    try:
        return ward_or_404(ward_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=f"Unknown Bhopal ward: {ward_id}") from error


@app.get("/api/ward/{ward_id}/weather", tags=["Monitoring"])
def weather(ward_id: str, days_back: int = Query(5, ge=1, le=90)) -> dict:
    validate_ward(ward_id)
    records = weather_for(ward_id, days_back)
    return {"ward_id": ward_id, "weather_data": records, "data_source": "MET Norway city observations with ward-level interpolation", "granularity": "8 observations per day"}


@app.get("/api/ward/{ward_id}/thermal-indices", tags=["Monitoring"])
def thermal_indices(ward_id: str, days_back: int = Query(5, ge=1, le=90)) -> dict:
    validate_ward(ward_id)
    return {"ward_id": ward_id, "thermal_indices": indices_for(daily_weather_for(ward_id, days_back)), "data_source": "Supplied ward-level daily analysis", "granularity": "daily summary"}


def forecast_rows(ward_id: str, days_ahead: int) -> list[dict]:
    ward = validate_ward(ward_id)
    recent = weather_for(ward_id, 1)[-1]
    model = None
    if MODEL_PATH.exists():
        try:
            with MODEL_PATH.open("rb") as handle: model = pickle.load(handle)
        except Exception: model = None
    rows = []
    base_date = datetime.fromisoformat(recent["date"])
    for offset in range(1, days_ahead + 1):
        weather_value = dict(recent)
        weather_value["temperature"] += 0.25 * offset
        weather_value["humidity"] += (-0.5 if offset % 2 else 0.8)
        weather_value["solar_radiation"] += 8 * offset
        weather_value["wind_speed"] = max(3, weather_value["wind_speed"] - 0.3 * offset)
        thermal = ThermalStressEngine.calculate(WeatherInput(**{k: weather_value[k] for k in WeatherInput.__annotations__}))
        if model is not None:
            try:
                date_value = base_date + timedelta(days=offset)
                prediction = float(model.predict([[weather_value["temperature"], weather_value["humidity"], weather_value["wind_speed"], weather_value["atmospheric_pressure"], weather_value["uv_index"], weather_value["solar_radiation"], date_value.timetuple().tm_yday, int(ward_id[-3:]) - 1, 21]])[0])
                thermal["utci"] = round(prediction, 2)
                thermal["alert_level"] = ThermalStressEngine.classify_alert_level(max(thermal["utci"], thermal["heat_index"]))
            except Exception:
                pass
        level = thermal["alert_level"]
        rows.append({"date": (base_date + timedelta(days=offset)).date().isoformat(), "predicted_wbgt": thermal["wbgt"], "predicted_utci": thermal["utci"], "predicted_heat_index": thermal["heat_index"], "predicted_alert_level": level, "confidence_score": max(58, 90 - offset * 6), "recommendations": {"Green": ["Maintain normal hydration."], "Yellow": ["Reduce prolonged sun exposure.", "Plan outdoor work around cooler hours."], "Orange": ["Open cooling spaces.", "Schedule frequent rest and water breaks."], "Red": ["Avoid non-essential outdoor activity.", "Activate heat-health protocols."]}[level]})
    return rows


@app.get("/api/ward/{ward_id}/forecast", tags=["Forecast"])
def forecast(ward_id: str, days_ahead: int = Query(5, ge=1, le=5)) -> dict:
    model_note = "XGBoost forecast trained on the supplied five-day ward/hourly dataset; confidence is not a guarantee." if MODEL_PATH.exists() else "Deterministic thermal projection fallback; the optional XGBoost artifact was not loaded in this serverless runtime."
    return {"ward_id": ward_id, "forecast": forecast_rows(ward_id, days_ahead), "data_source": "Supplied Bhopal snapshot plus ward interpolation", "model_note": model_note}


@app.get("/api/ward/{ward_id}/alert-status", tags=["Alerts"])
def alert_status(ward_id: str) -> dict:
    return alert_details(ward_id)


@app.post("/api/auth/login", tags=["Authentication"])
def login(request: LoginRequest) -> dict:
    connection = db(); row = connection.execute("SELECT * FROM users WHERE email = ?", (request.email,)).fetchone(); connection.close()
    if not row or not password_matches(request.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"access_token": token_for(row), "token_type": "bearer", "expires_in": 86400, "user_type": row["user_type"], "organization": row["organization"]}


@app.post("/api/auth/register", tags=["Authentication"])
def register(request: RegisterRequest) -> dict:
    connection = db(); user_id = f"USER_{secrets.token_hex(4).upper()}"
    try:
        connection.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?)", (user_id, request.email, password_hash(request.password), request.user_type, request.organization_name)); connection.commit()
        row = connection.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    except sqlite3.IntegrityError as error:
        raise HTTPException(status_code=409, detail="An account with this email already exists") from error
    finally: connection.close()
    return {"access_token": token_for(row), "token_type": "bearer", "expires_in": 86400, "user_type": request.user_type, "user_id": user_id}


@app.get("/api/admin/municipality-suggestions", tags=["Administration"])
def municipality_suggestions(ward_id: str = Query(...), user: Annotated[dict, Depends(require_role("local_administration"))] = None) -> dict:
    ward = validate_ward(ward_id); alert = alert_details(ward_id)
    return {"prototype_notice": "Prototype recommendations only; this system does not control municipal infrastructure.", "ward_id": ward_id, "risk_level": alert["current_alert_level"], "high_risk_areas": [{"name": f"{ward['ward_name']} market corridor", "severity": alert["current_alert_level"], "latitude": ward["latitude"], "longitude": ward["longitude"]}], "suggested_cooling_centers": [{"location": "Ward community centre", "capacity": 180}, {"location": "Public school auditorium", "capacity": 260}], "recommended_work_hour_adjustments": "Shift outdoor work toward 05:00-10:00 and after 17:00; enforce water and rest breaks.", "grid_load_management_tips": "Prioritise reliable supply for cooling centres and residential feeders during the afternoon peak.", "resource_deployment_recommendations": "Position water tankers, ORS supplies, and trained volunteers near markets and transit stops.", "sms_alert_simulation": {"status": "SIMULATED", "recipients": "registered ward contacts", "message": f"{alert['current_alert_level']} heat alert for {ward['ward_name']}"}}


@app.get("/api/healthcare/hospital-readiness", tags=["Healthcare"])
def hospital_readiness(ward_id: str = Query(...), user: Annotated[dict, Depends(require_role("healthcare_facility"))] = None) -> dict:
    ward = validate_ward(ward_id); alert = alert_details(ward_id); uplift = {"Green": 8, "Yellow": 18, "Orange": 31, "Red": 46}[alert["current_alert_level"]]
    return {"prototype_notice": "Simulated readiness planning; not a medical diagnosis or hospital command system.", "hospital_id": f"HOSP-{ward_id}", "served_ward": ward["ward_name"], "risk_level": alert["current_alert_level"], "predicted_patient_load_increase": uplift, "recommended_bed_capacity": 20 + uplift, "priority_care_items": ["Cooling equipment readiness", "IV fluid and ORS stock check", "Emergency heat-stroke protocol review", "Staff briefing checklist", "Triage and transport plan", "Cold water and ice availability"], "risk_groups": ["older adults", "children", "people with chronic illness", "outdoor workers"]}


@app.post("/api/thermal/calculate", tags=["Monitoring"])
def calculate_thermal(payload: WeatherInputPayload) -> dict:
    try:
        return ThermalStressEngine.calculate(WeatherInput(**payload.model_dump()))
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
