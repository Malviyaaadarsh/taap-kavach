from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from .thermal_engine import ThermalStressEngine, WeatherInput

ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = next((candidate for candidate in (PACKAGE_ROOT / "data", ROOT / "data") if candidate.exists()), PACKAGE_ROOT / "data")
WARDS_PATH = DATA_DIR / "wards.json"
WEATHER_PATH = DATA_DIR / "weather_history.json"
DAILY_SUMMARY_PATH = DATA_DIR / "ward_daily_summary.json"


def load_wards() -> list[dict]:
    return json.loads(WARDS_PATH.read_text(encoding="utf-8"))["wards"]


def load_weather() -> list[dict]:
    return json.loads(WEATHER_PATH.read_text(encoding="utf-8"))["weather_records"]


def load_daily_summary() -> list[dict]:
    return json.loads(DAILY_SUMMARY_PATH.read_text(encoding="utf-8"))["daily_records"]


def ward_or_404(ward_id: str) -> dict:
    ward = next((item for item in load_wards() if item["ward_id"] == ward_id), None)
    if not ward:
        raise KeyError(ward_id)
    return ward


def weather_for(ward_id: str, days: int = 5) -> list[dict]:
    ward_or_404(ward_id)
    records = sorted((r for r in load_weather() if r["ward_id"] == ward_id), key=lambda r: (r["date"], r["time"]))
    return records[-days * 8:]


def daily_weather_for(ward_id: str, days: int = 5) -> list[dict]:
    ward_or_404(ward_id)
    records = sorted((r for r in load_daily_summary() if r["ward_id"] == ward_id), key=lambda r: r["date"])
    return records[-days:]


def indices_for(records: list[dict]) -> list[dict]:
    if records and "wbgt" in records[0]:
        return [{"date": record["date"], "wbgt": record["wbgt"], "utci": record["utci"],
                 "heat_index": record["heat_index"], "thermal_stress_level": ThermalStressEngine.classify_thermal_stress(record["wbgt"]),
                 "alert_level": record["alert_level"]} for record in records]
    output = []
    for record in records:
        values = ThermalStressEngine.calculate(WeatherInput(**{k: record[k] for k in WeatherInput.__annotations__}))
        output.append({"date": record["date"], **values})
    return output


def alert_details(ward_id: str) -> dict:
    ward = ward_or_404(ward_id)
    latest = daily_weather_for(ward_id, 1)[0]
    level = latest["alert_level"]
    details = {
        "Green": ("Normal conditions. Continue routine activities with regular hydration.", [], "Use normal precautions and drink water regularly."),
        "Yellow": ("Precautionary alert. Heat exposure should be reduced.", ["general population"], "Limit prolonged sun exposure and plan outdoor work earlier or later."),
        "Orange": ("Cautious alert. High thermal stress is expected.", ["elderly", "children", "outdoor workers", "people with chronic illness"], "Use cooling spaces, schedule breaks, and avoid peak heat from 11:00 to 16:00."),
        "Red": ("Severe heat warning. Extreme thermal stress is expected.", ["all populations"], "Avoid non-essential outdoor activity, use a cooling shelter, and seek medical help for heat illness symptoms."),
    }[level]
    calculated = {"wbgt": latest["wbgt"], "utci": latest["utci"], "heat_index": latest["heat_index"],
                  "thermal_stress_level": ThermalStressEngine.classify_thermal_stress(latest["wbgt"]), "alert_level": level}
    valid_from = datetime.fromisoformat(latest["date"])
    return {"ward_id": ward_id, "ward_name": ward["ward_name"], "current_alert_level": level,
            "alert_message": details[0], "affected_populations": details[1],
            "valid_from": valid_from.isoformat(), "valid_until": (valid_from + timedelta(days=1)).isoformat(),
            "action_recommended": details[2], "indices": calculated}
