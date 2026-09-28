from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, Literal

import jwt
from fastapi import Depends, FastAPI, HTTPException, Query, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field

from .services.chatbot_service import answer as chatbot_answer
from .services.city_service import get_city_risk_map, get_city_summary
from .services.data_store import (
    alert_details,
    daily_weather_for,
    get_ward_10day_history,
    get_ward_current,
    get_ward_facilities,
    get_seasonal_windows,
    indices_for,
    load_wards,
    ward_or_404,
    weather_for,
)
from .services.forecast_service import forecast_service
from .services.location_service import (
    get_cities,
    get_districts,
    get_states,
    get_wards_for_city,
)
from .services.location_weather_service import LocationWeatherError, get_location_weather, search_locations
from .services.recommendation_service import get_ward_recommendations
from .services.risk_service import calculate_ward_risk_and_impact
from .services.thermal_engine import ThermalStressEngine, WeatherInput

ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = next((candidate for candidate in (PACKAGE_ROOT / "data", ROOT / "data") if candidate.exists()), PACKAGE_ROOT / "data")
DB_PATH = Path(os.getenv("TAAP_DATABASE_PATH", "/tmp/taap_kavach.db" if os.getenv("VERCEL") else str(ROOT / "data" / "taap_kavach.db")))
JWT_SECRET = os.getenv("TAAP_JWT_SECRET", "local-prototype-secret-change-me")
ALGORITHM = "HS256"
security = HTTPBearer(auto_error=False)

app = FastAPI(
    title="Taap Kavach V2 API",
    version="2.0.0",
    description="Ward-level human thermal stress intelligence, 4-day early warning, and municipal decision-support system.",
)

origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://taap-kavach.vercel.app",
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(KeyError)
async def key_error_handler(request, exc):
    return JSONResponse(status_code=404, content={"detail": f"Resource not found: {str(exc)}"})



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
    connection.execute(
        "CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, user_type TEXT NOT NULL, organization TEXT NOT NULL)"
    )
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(users)")}
    if "role" not in columns:
        connection.execute("ALTER TABLE users ADD COLUMN role TEXT")
    if "user_type_selection" not in columns:
        connection.execute("ALTER TABLE users ADD COLUMN user_type_selection TEXT")
    connection.execute(
        "UPDATE users SET role = 'government' WHERE role IS NULL AND user_type IN ('local_administration', 'healthcare_facility')"
    )
    connection.commit()
    return connection


def init_users() -> None:
    connection = db()
    demos = [
        ("ADMIN_001", "admin.bhopal@taapkavach.gov.in", "demo-admin", "local_administration", "Bhopal Municipal Corporation"),
        ("HEALTH_001", "healthcare.hospital@taapkavach.gov.in", "demo-health", "healthcare_facility", "Bhopal Medical College"),
    ]
    for user in demos:
        connection.execute(
            "INSERT OR IGNORE INTO users (user_id, email, password_hash, user_type, organization, role, user_type_selection) VALUES (?, ?, ?, ?, ?, 'government', NULL)",
            (user[0], user[1], password_hash(user[2]), user[3], user[4]),
        )
    connection.commit()
    connection.close()


@app.on_event("startup")
def startup() -> None:
    init_users()


def token_for(row: sqlite3.Row) -> str:
    payload = {
        "sub": row["user_id"],
        "email": row["email"],
        "user_type": row["user_type"],
        "role": row["role"],
        "user_type_selection": row["user_type_selection"],
        "exp": datetime.now(timezone.utc) + timedelta(hours=24),
    }
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
        if user.get("user_type") != role or (role in {"local_administration", "healthcare_facility"} and user.get("role") != "government"):
            raise HTTPException(status_code=403, detail=f"Requires {role} access")
        return user

    return dependency


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class RegisterRequest(LoginRequest):
    user_type: Literal["local_administration", "healthcare_facility"] = "local_administration"
    organization_name: str = Field(default="Taap Kavach User", min_length=2, max_length=120)
    ward_jurisdiction: list[str] = Field(default_factory=list)


class ProfileSelection(BaseModel):
    role: Literal["government", "citizen"] | None = None
    user_type: Literal["outdoor_worker", "citizen"] | None = None


class WeatherInputPayload(BaseModel):
    temperature: float
    humidity: float
    wind_speed: float
    atmospheric_pressure: float = 1005.0
    uv_index: float = 6.0
    solar_radiation: float = 500.0


class ForecastRunPayload(BaseModel):
    ward_id: str
    days_ahead: int = Field(default=4, ge=1, le=7)


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=500)
    ward_id: str = Field(pattern=r"^[A-Z]{3}_W\d{3}$")


# ==========================================
# SYSTEM & METADATA ENDPOINTS
# ==========================================


@app.get("/", tags=["System"])
def root() -> dict:
    return {
        "name": "Taap Kavach API",
        "version": "2.0.0",
        "positioning": "Ward-level human thermal stress intelligence and early-warning decision support for extreme heat.",
        "status": "V2_PROTOTYPE",
        "geography_demonstrated": "Madhya Pradesh -> Bhopal -> Bhopal Municipal Corporation -> 10 Wards",
        "data_status": {
            "environmental_observations": "OBSERVED (MET Norway supplied snapshot 14-18 Sep 2026)",
            "ward_spatialization": "DERIVED (Spatial microclimatic offsets)",
            "early_warning_models": "PROTOTYPE (XGBoost Multivariate + sktime SARIMA Combined)",
            "planning_indicators": "SIMULATED_PLANNING_ESTIMATES",
        },
        "disclaimer": "Prototype decision-support platform for SIH; does not claim official IMD authority or medical diagnosis.",
    }


@app.get("/api/health", tags=["System"])
def health() -> dict:
    return {
        "status": "healthy",
        "version": "2.0.0",
        "period": "2026-09-09 to 2026-09-22",
        "observed_range": "2026-09-14 to 2026-09-18",
        "forecast_range": "2026-09-19 to 2026-09-22",
    }


@app.get("/api/methodology", tags=["System"])
def methodology() -> dict:
    return {
        "title": "Taap Kavach Methodology & Technical Framework",
        "paradigm": "Shifting heatwave intelligence from 'What will the weather be?' to 'What will the heat do to people and municipal services?'",
        "four_tier_structure": {
            "Tier 1": "National meteorological forecast (IMD)",
            "Tier 2": "Regional outlook",
            "Tier 3": "District aggregation",
            "Tier 4 (Taap Kavach)": "Hyper-local ward/zone human thermal stress, population exposure, and municipal action triggers",
        },
        "thermal_indices": {
            "WBGT": "Wet-Bulb Globe Temperature: ISO 7243 occupational heat stress standard combining wet-bulb, globe, and dry-bulb temperatures.",
            "UTCI": "Universal Thermal Climate Index: Equivalent perceived temperature from multi-node human thermoregulation model.",
            "Heat_Index": "Rothfusz regression combining ambient temperature and relative humidity.",
            "HTSI": "Taap Kavach Human Thermal Stress Index: 0-100 composite score combining UTCI (35%), WBGT (25%), HI (20%), Solar Radiation (12%), and Humidity (8%) with convective wind mitigation.",
        },
        "forecasting_architecture": {
            "input_window": "Previous 10 days rolling meteorological & thermal observations",
            "forecast_horizon": "Next 4 days early warning (Day +1 to Day +4)",
            "models": {
                "XGBoost": "Multivariate non-linear tree regressor mapping weather variables, diurnal timing, and ward characteristics to perceived heat stress.",
                "SARIMA": "Classical time-series seasonal autoregressive integrated moving average capturing temporal trends, cyclic inertia, and diurnal autocorrelation.",
                "Ensemble": "Weighted complementary blend (60% XGBoost, 40% SARIMA) with confidence intervals.",
            },
        },
        "validation_roadmap": {
            "current_status": "Prototype pipeline validated on supplied Bhopal environmental snapshot.",
            "next_stage": "Integration of 3-year summer station archives with walk-forward temporal cross-validation.",
            "target_metrics": ["MAE (°C)", "RMSE (°C)", "Alert Classification Precision", "Alert Recall", "Missed-Event Rate", "False Alarm Rate"],
        },
    }


# ==========================================
# GEOGRAPHIC HIERARCHY ENDPOINTS
# ==========================================


@app.get("/api/locations/states", tags=["Geographic Hierarchy"])
def get_states_list() -> dict:
    return {"states": get_states()}


@app.get("/api/locations/districts", tags=["Geographic Hierarchy"])
def get_districts_list(state_id: str = Query("MP")) -> dict:
    return {"state_id": state_id, "districts": get_districts(state_id)}


@app.get("/api/locations/cities", tags=["Geographic Hierarchy"])
def get_cities_list(district_id: str = Query("bhopal")) -> dict:
    return {"district_id": district_id, "cities": get_cities(district_id)}


@app.get("/api/locations/wards", tags=["Geographic Hierarchy"])
def get_wards_list(city_id: str = Query("bhopal_bmc")) -> dict:
    wards = get_wards_for_city(city_id)
    return {"city_id": city_id, "total_wards": len(wards), "wards": wards}


@app.get("/api/location/weather", tags=["Location Weather"])
def location_weather(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
) -> dict:
    try:
        return get_location_weather(latitude, longitude)
    except LocationWeatherError as error:
        raise HTTPException(status_code=503, detail="Location weather is temporarily unavailable") from error


@app.get("/api/location/search", tags=["Location Weather"])
def location_search(q: str = Query(..., min_length=2, max_length=80)) -> dict:
    try:
        return {"locations": search_locations(q)}
    except LocationWeatherError as error:
        raise HTTPException(status_code=503, detail="Location search is temporarily unavailable") from error


# Backwards compatibility
@app.get("/api/bhopal/wards", tags=["Geographic Hierarchy"])
def bhopal_wards() -> dict:
    return {
        "city": "Bhopal",
        "wards": [
            {
                "ward_id": w["ward_id"],
                "ward_name": w["ward_name"],
                "zone": w["zone"],
                "population_count": w["population"],
                "primary_demographics": {
                    "elderly_percent": w["elderly_percentage"],
                    "outdoor_workers_percent": w["outdoor_workers_percentage"],
                },
                **w,
            }
            for w in load_wards()
        ],
    }


# ==========================================
# CITY OVERVIEW & RISK MAP ENDPOINTS
# ==========================================


@app.get("/api/city/{city_id}/summary", tags=["City Overview"])
def city_summary(city_id: str = "bhopal_bmc") -> dict:
    return get_city_summary(city_id)


@app.get("/api/city/{city_id}/risk-map", tags=["City Overview"])
def city_risk_map(city_id: str = "bhopal_bmc") -> dict:
    return get_city_risk_map(city_id)


# ==========================================
# WARD LEVEL INTELLIGENCE ENDPOINTS
# ==========================================


@app.get("/api/ward/{ward_id}/current", tags=["Ward Intelligence"])
def ward_current(ward_id: str) -> dict:
    try:
        return get_ward_current(ward_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Ward '{ward_id}' not found.")


@app.get("/api/ward/{ward_id}/history", tags=["Ward Intelligence"])
def ward_history(ward_id: str, days_back: int = Query(10, ge=1, le=30)) -> dict:
    ward_or_404(ward_id)
    records = get_ward_10day_history(ward_id)
    return {
        "ward_id": ward_id,
        "requested_days": days_back,
        "history_count": len(records),
        "history": records[-days_back:],
        "data_status": {
            "type": "OBSERVED_AND_BASELINE",
            "observed_subset": "2026-09-14 to 2026-09-18",
            "historical_baseline_subset": "2026-09-09 to 2026-09-13",
        },
    }


@app.get("/api/ward/{ward_id}/forecast", tags=["Ward Intelligence"])
def ward_forecast(ward_id: str, days_ahead: int = Query(4, ge=1, le=7)) -> dict:
    try:
        return forecast_service.get_4day_forecast(ward_id, days_ahead=days_ahead)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Ward '{ward_id}' not found.")


@app.get("/api/ward/{ward_id}/risk", tags=["Ward Intelligence"])
def ward_risk(ward_id: str) -> dict:
    try:
        return calculate_ward_risk_and_impact(ward_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Ward '{ward_id}' not found.")


@app.get("/api/ward/{ward_id}/recommendations", tags=["Ward Intelligence"])
def ward_recommendations(ward_id: str) -> dict:
    try:
        return get_ward_recommendations(ward_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Ward '{ward_id}' not found.")


@app.get("/api/ward/{ward_id}/seasonal-windows", tags=["Ward Intelligence"])
def ward_seasonal_windows(ward_id: str) -> dict:
    try:
        return get_seasonal_windows(ward_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Ward '{ward_id}' not found.")


# Backwards compatibility endpoints
@app.get("/api/ward/{ward_id}/weather", tags=["Monitoring"])
def ward_weather_legacy(ward_id: str, days_back: int = Query(5, ge=1, le=90)) -> dict:
    ward_or_404(ward_id)
    records = weather_for(ward_id, days_back)
    return {
        "ward_id": ward_id,
        "weather_data": records,
        "data_source": "MET Norway city observations with ward-level interpolation",
        "granularity": "8 observations per day",
    }


@app.get("/api/ward/{ward_id}/thermal-indices", tags=["Monitoring"])
def ward_thermal_indices_legacy(ward_id: str, days_back: int = Query(5, ge=1, le=90)) -> dict:
    ward_or_404(ward_id)
    return {
        "ward_id": ward_id,
        "thermal_indices": indices_for(daily_weather_for(ward_id, days_back)),
        "data_source": "Supplied ward-level daily analysis",
        "granularity": "daily summary",
    }


@app.get("/api/ward/{ward_id}/alert-status", tags=["Alerts"])
def ward_alert_status_legacy(ward_id: str) -> dict:
    try:
        return alert_details(ward_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Ward '{ward_id}' not found.")


# ==========================================
# ADMINISTRATION WORKSPACE ENDPOINTS
# ==========================================


@app.get("/api/admin/overview", tags=["Administration"])
def admin_overview() -> dict:
    summary = get_city_summary("bhopal_bmc")
    priority_table = []
    for w in summary["all_wards"]:
        priority_table.append({
            "ward_id": w["ward_id"],
            "ward_name": w["ward_name"],
            "zone": w["zone"],
            "alert_level": w["alert_level"],
            "htsi": w["htsi"],
            "utci": w["utci"],
            "peak_day": w["peak_forecast_day"],
            "vulnerable_population": int(w["population"] * ((w["elderly_percentage"] + w["outdoor_workers_percentage"]) / 100.0)),
            "priority_action": w["priority_action"],
        })

    return {
        "situation_summary": summary["status_summary"],
        "priority_wards_table": priority_table,
        "municipal_action_plans": summary["priority_municipal_actions"],
        "timestamp": summary["timestamp"],
    }


@app.get("/api/admin/actions", tags=["Administration"])
def admin_actions(ward_id: str = Query("BPL_W003")) -> dict:
    recs = get_ward_recommendations(ward_id)
    risk = calculate_ward_risk_and_impact(ward_id)
    return {
        "ward_id": ward_id,
        "ward_name": recs["ward_name"],
        "alert_level": recs["current_alert_level"],
        "planning_estimates": risk["planning_estimates"],
        "municipal_actions": recs["municipal_actions"],
        "cooling_centres": recs["cooling_centres"],
        "simulated_sms_broadcast": {
            "status": "SIMULATED_READY",
            "recipients_estimated": risk["planning_estimates"]["population_exposed"],
            "message": f"TAAP KAVACH ALERT: {recs['current_alert_level']} heat warning active for {recs['ward_name']}. Free cooling shelter open at {recs['cooling_centres'][0]['name']}. Emergency water tankers deployed.",
        },
    }


# Backwards compatibility
@app.get("/api/admin/municipality-suggestions", tags=["Administration"])
def municipality_suggestions_legacy(
    ward_id: str = Query(...),
    user: Annotated[dict, Depends(require_role("local_administration"))] = None,
) -> dict:
    actions_data = admin_actions(ward_id)
    ward = ward_or_404(ward_id)
    return {
        "prototype_notice": "Prototype recommendations only; this system does not directly control municipal infrastructure.",
        "ward_id": ward_id,
        "risk_level": actions_data["alert_level"],
        "high_risk_areas": [
            {
                "name": f"{ward['ward_name']} central market corridor",
                "severity": actions_data["alert_level"],
                "latitude": ward["latitude"],
                "longitude": ward["longitude"],
            }
        ],
        "suggested_cooling_centers": actions_data["cooling_centres"],
        "recommended_work_hour_adjustments": "Shift outdoor work toward 05:30-10:00 and after 17:00; mandate hydration breaks.",
        "grid_load_management_tips": "Prioritise uninterrupted feeder supply for public cooling spaces and residential feeders during peak afternoon hours.",
        "resource_deployment_recommendations": "Position water tankers, ORS kiosks, and trained volunteers near markets and transit terminals.",
        "sms_alert_simulation": actions_data["simulated_sms_broadcast"],
    }


# ==========================================
# HEALTHCARE WORKSPACE ENDPOINTS
# ==========================================


@app.get("/api/healthcare/overview", tags=["Healthcare"])
def healthcare_overview() -> dict:
    summary = get_city_summary("bhopal_bmc")
    return {
        "city": "Bhopal",
        "total_monitored_wards": summary["status_summary"]["total_monitored_wards"],
        "high_risk_wards_count": summary["status_summary"]["alert_counts"]["Orange"] + summary["status_summary"]["alert_counts"]["Red"],
        "total_vulnerable_exposed": summary["status_summary"]["total_vulnerable_exposed"],
        "overall_status": summary["status_summary"]["overall_status"],
        "priority_wards": summary["highest_risk_wards"],
    }


@app.get("/api/healthcare/readiness", tags=["Healthcare"])
def healthcare_readiness(ward_id: str = Query("BPL_W003")) -> dict:
    ward = ward_or_404(ward_id)
    current = get_ward_current(ward_id)
    recs = get_ward_recommendations(ward_id)
    risk = calculate_ward_risk_and_impact(ward_id)
    forecast = forecast_service.get_4day_forecast(ward_id, 4)

    return {
        "ward_id": ward_id,
        "ward_name": ward["ward_name"],
        "current_alert": current["alert"]["current_alert_level"],
        "peak_forecast_day": forecast["peak_forecast"]["day_label"],
        "peak_forecast_date": forecast["peak_forecast"]["date"],
        "peak_alert_level": forecast["peak_forecast"]["alert_level"],
        "expected_heat_stress_severity": current["thermal_metrics"]["thermal_stress_level"],
        "demographics": risk["demographics"],
        "patient_surge_planning_estimate": risk["planning_estimates"]["projected_heat_illness_patient_surge"],
        "heat_beds_available": risk["planning_estimates"]["available_heat_beds"],
        "bed_readiness_percentage": risk["planning_estimates"]["bed_readiness_percentage"],
        "healthcare_facilities": recs["healthcare_facilities"],
        "readiness_checklist": recs["readiness_checklist"],
        "priority_clinical_protocols": recs["healthcare_actions"],
        "health_impact_risk": risk["health_impact_risk"],
    }


# Backwards compatibility
@app.get("/api/healthcare/hospital-readiness", tags=["Healthcare"])
def hospital_readiness_legacy(
    ward_id: str = Query(...),
    user: Annotated[dict, Depends(require_role("healthcare_facility"))] = None,
) -> dict:
    ready = healthcare_readiness(ward_id)
    ward = ward_or_404(ward_id)
    return {
        "prototype_notice": "Simulated readiness planning; not a medical diagnosis or hospital command system.",
        "hospital_id": f"HOSP-{ward_id}",
        "served_ward": ward["ward_name"],
        "risk_level": ready["current_alert"],
        "predicted_patient_load_increase": int(ready["patient_surge_planning_estimate"]),
        "recommended_bed_capacity": ready["heat_beds_available"] + 15,
        "priority_care_items": [item["item"] for item in ready["readiness_checklist"]],
        "risk_groups": ["older adults (60+)", "children under 10", "outdoor manual workers", "patients with cardiovascular illness"],
    }


# ==========================================
# COMPUTATION & SIMULATION ENDPOINTS
# ==========================================


@app.post("/api/thermal/calculate", tags=["Computation"])
def calculate_thermal(payload: WeatherInputPayload) -> dict:
    try:
        w_input = WeatherInput(**payload.model_dump())
        return ThermalStressEngine.calculate(w_input)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.post("/api/forecast/run", tags=["Computation"])
def run_forecast(payload: ForecastRunPayload) -> dict:
    try:
        return forecast_service.get_4day_forecast(payload.ward_id, days_ahead=payload.days_ahead)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Ward '{payload.ward_id}' not found.")


# ==========================================
# AUTHENTICATION & CHAT ENDPOINTS
# ==========================================


@app.post("/api/auth/login", tags=["Authentication"])
def login(request: LoginRequest) -> dict:
    connection = db()
    row = connection.execute("SELECT * FROM users WHERE email = ?", (request.email,)).fetchone()
    connection.close()
    if not row or not password_matches(request.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {
        "access_token": token_for(row),
        "token_type": "bearer",
        "expires_in": 86400,
        "user_type": row["user_type"],
        "organization": row["organization"],
        "role": row["role"],
        "user_type_selection": row["user_type_selection"],
        "user_id": row["user_id"],
    }


@app.post("/api/auth/register", tags=["Authentication"])
def register(request: RegisterRequest) -> dict:
    connection = db()
    user_id = f"USER_{secrets.token_hex(4).upper()}"
    try:
        connection.execute(
            "INSERT INTO users (user_id, email, password_hash, user_type, organization, role, user_type_selection) VALUES (?, ?, ?, ?, ?, NULL, NULL)",
            (user_id, request.email, password_hash(request.password), request.user_type, request.organization_name),
        )
        connection.commit()
        row = connection.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    except sqlite3.IntegrityError as error:
        raise HTTPException(status_code=409, detail="An account with this email already exists") from error
    finally:
        connection.close()
    return {
        "access_token": token_for(row),
        "token_type": "bearer",
        "expires_in": 86400,
        "user_type": request.user_type,
        "user_id": user_id,
        "organization": request.organization_name,
        "role": row["role"],
        "user_type_selection": row["user_type_selection"],
    }


@app.get("/api/auth/me", tags=["Authentication"])
def me(user: Annotated[dict, Depends(current_user)]) -> dict:
    connection = db()
    row = connection.execute("SELECT * FROM users WHERE user_id = ?", (user["sub"],)).fetchone()
    connection.close()
    if row is None:
        raise HTTPException(status_code=401, detail="User account not found")
    return {
        "user_id": row["user_id"],
        "email": row["email"],
        "user_type": row["user_type"],
        "organization": row["organization"],
        "role": row["role"],
        "user_type_selection": row["user_type_selection"],
    }


@app.patch("/api/auth/profile", tags=["Authentication"])
def update_profile(selection: ProfileSelection, user: Annotated[dict, Depends(current_user)]) -> dict:
    if selection.role == "government" and selection.user_type is not None:
        raise HTTPException(status_code=400, detail="Government users do not need a user type")
    if selection.role == "citizen" and selection.user_type is not None and selection.user_type not in {"outdoor_worker", "citizen"}:
        raise HTTPException(status_code=400, detail="Citizen users must select a user type")
    if selection.role is None and selection.user_type is None:
        raise HTTPException(status_code=400, detail="A role or user type is required")

    connection = db()
    row = connection.execute("SELECT * FROM users WHERE user_id = ?", (user["sub"],)).fetchone()
    if row is None:
        connection.close()
        raise HTTPException(status_code=401, detail="User account not found")
    role = selection.role if selection.role is not None else row["role"]
    user_type_selection = selection.user_type if selection.user_type is not None else row["user_type_selection"]
    connection.execute(
        "UPDATE users SET role = ?, user_type_selection = ? WHERE user_id = ?",
        (role, user_type_selection, user["sub"]),
    )
    connection.commit()
    updated = connection.execute("SELECT * FROM users WHERE user_id = ?", (user["sub"],)).fetchone()
    connection.close()
    return {
        "user_id": updated["user_id"],
        "email": updated["email"],
        "user_type": updated["user_type"],
        "organization": updated["organization"],
        "role": updated["role"],
        "user_type_selection": updated["user_type_selection"],
    }


@app.post("/api/chat", tags=["Assistant"])
def chat(request: ChatRequest) -> dict:
    try:
        return chatbot_answer(request.question, request.ward_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=f"Unknown ward: {request.ward_id}") from error
