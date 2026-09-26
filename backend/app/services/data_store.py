from __future__ import annotations

import json
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .thermal_engine import ThermalStressEngine, WeatherInput

ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = next((candidate for candidate in (PACKAGE_ROOT / "data", ROOT / "data") if candidate.exists()), PACKAGE_ROOT / "data")
WARDS_PATH = DATA_DIR / "wards.json"
WEATHER_PATH = DATA_DIR / "weather_history.json"
DAILY_SUMMARY_PATH = DATA_DIR / "ward_daily_summary.json"


def load_wards() -> list[dict[str, Any]]:
    return json.loads(WARDS_PATH.read_text(encoding="utf-8"))["wards"]


def load_weather() -> list[dict[str, Any]]:
    return json.loads(WEATHER_PATH.read_text(encoding="utf-8"))["weather_records"]


def load_daily_summary() -> list[dict[str, Any]]:
    return json.loads(DAILY_SUMMARY_PATH.read_text(encoding="utf-8"))["daily_records"]


def ward_or_404(ward_id: str) -> dict[str, Any]:
    ward = next((item for item in load_wards() if item["ward_id"] == ward_id), None)
    if not ward:
        raise KeyError(ward_id)
    return ward


def weather_for(ward_id: str, days: int = 5) -> list[dict[str, Any]]:
    ward_or_404(ward_id)
    records = sorted((r for r in load_weather() if r["ward_id"] == ward_id), key=lambda r: (r["date"], r["time"]))
    return records[-days * 8 :]


def daily_weather_for(ward_id: str, days: int = 5) -> list[dict[str, Any]]:
    ward_or_404(ward_id)
    records = sorted((r for r in load_daily_summary() if r["ward_id"] == ward_id), key=lambda r: r["date"])
    return records[-days:]


def indices_for(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for record in records:
        w_input = WeatherInput(
            temperature=record["temperature"],
            humidity=record["humidity"],
            wind_speed=record["wind_speed"],
            atmospheric_pressure=record.get("atmospheric_pressure", 1004.0),
            uv_index=record.get("uv_index", 6.0),
            solar_radiation=record.get("solar_radiation", 500.0),
        )
        htsi = ThermalStressEngine.calculate_htsi(w_input, wbgt=record.get("wbgt"), utci=record.get("utci"), heat_index=record.get("heat_index"))
        output.append({
            "date": record["date"],
            "temperature": record["temperature"],
            "humidity": record["humidity"],
            "wind_speed": record["wind_speed"],
            "wbgt": record.get("wbgt", ThermalStressEngine.calculate_wbgt(w_input)),
            "utci": record.get("utci", ThermalStressEngine.calculate_utci(w_input)),
            "heat_index": record.get("heat_index", ThermalStressEngine.calculate_heat_index(w_input)),
            "htsi": htsi["score"],
            "htsi_details": htsi,
            "thermal_stress_level": ThermalStressEngine.classify_thermal_stress(record.get("wbgt", 28.0)),
            "alert_level": record.get("alert_level", "Green"),
        })
    return output


def get_ward_10day_history(ward_id: str) -> list[dict[str, Any]]:
    """Returns 10-day history (Sep 9 - Sep 18, 2026).
    Sep 14-18 is OBSERVED snapshot from MET Norway with ward offsets.
    Sep 9-13 is HISTORICAL_BASELINE deterministic series leading up to the heatwave.
    """
    ward = ward_or_404(ward_id)
    daily_records = daily_weather_for(ward_id, 5)  # Sep 14-18
    earliest_observed = daily_records[0]

    history_10days = []

    # Generate Sep 9 to Sep 13 (5 days baseline before Sep 14)
    base_date = datetime.fromisoformat("2026-09-14")
    for i in range(5, 0, -1):
        hist_date = (base_date - timedelta(days=i)).date().isoformat()
        # Gradual build up of temperature towards Sep 14
        cooling_factor = i * 0.45
        hist_temp = round(earliest_observed["temperature"] - cooling_factor, 1)
        hist_hum = round(min(82.0, earliest_observed["humidity"] + (i * 1.8)), 1)
        hist_wind = round(max(5.0, earliest_observed["wind_speed"] - (i * 0.3)), 1)
        solar_rad = round(max(200.0, 520.0 - (i * 35.0)), 1)
        uv = round(max(3.0, 6.5 - (i * 0.5)), 1)

        w_input = WeatherInput(
            temperature=hist_temp,
            humidity=hist_hum,
            wind_speed=hist_wind,
            atmospheric_pressure=1006.0 + i * 0.5,
            uv_index=uv,
            solar_radiation=solar_rad,
        )
        thermal = ThermalStressEngine.calculate(w_input, vegetation=ward.get("vegetation_coverage", "Medium"))

        history_10days.append({
            "date": hist_date,
            "day_index": -(i - 1),
            "data_status": "HISTORICAL_BASELINE",
            "temperature": hist_temp,
            "humidity": hist_hum,
            "wind_speed": hist_wind,
            "solar_radiation": solar_rad,
            "wbgt": thermal["wbgt"],
            "utci": thermal["utci"],
            "heat_index": thermal["heat_index"],
            "htsi": thermal["htsi"],
            "alert_level": thermal["alert_level"],
            "thermal_stress_level": thermal["thermal_stress_level"],
        })

    # Append Sep 14 to Sep 18 (Observed)
    for index, rec in enumerate(daily_records):
        w_input = WeatherInput(
            temperature=rec["temperature"],
            humidity=rec["humidity"],
            wind_speed=rec["wind_speed"],
            atmospheric_pressure=1003.0 - index * 0.8,
            uv_index=round(6.0 + index * 0.5, 1),
            solar_radiation=round(500.0 + index * 30.0, 1),
        )
        htsi = ThermalStressEngine.calculate_htsi(w_input, wbgt=rec["wbgt"], utci=rec["utci"], heat_index=rec["heat_index"])
        history_10days.append({
            "date": rec["date"],
            "day_index": index + 1,
            "data_status": "OBSERVED",
            "temperature": rec["temperature"],
            "humidity": rec["humidity"],
            "wind_speed": rec["wind_speed"],
            "solar_radiation": w_input.solar_radiation,
            "wbgt": rec["wbgt"],
            "utci": rec["utci"],
            "heat_index": rec["heat_index"],
            "htsi": htsi["score"],
            "alert_level": rec["alert_level"],
            "thermal_stress_level": ThermalStressEngine.classify_thermal_stress(rec["wbgt"]),
            "is_today": (rec["date"] == "2026-09-18"),
        })

    return history_10days


def get_ward_current(ward_id: str) -> dict[str, Any]:
    ward = ward_or_404(ward_id)
    latest_hourly = weather_for(ward_id, 1)[-1]
    latest_daily = daily_weather_for(ward_id, 1)[0]

    w_input = WeatherInput(
        temperature=latest_hourly["temperature"],
        humidity=latest_hourly["humidity"],
        wind_speed=latest_hourly["wind_speed"],
        atmospheric_pressure=latest_hourly.get("atmospheric_pressure", 1002.0),
        uv_index=latest_hourly.get("uv_index", 8.0),
        solar_radiation=latest_hourly.get("solar_radiation", 650.0),
    )
    thermal = ThermalStressEngine.calculate(w_input, vegetation=ward.get("vegetation_coverage", "Medium"))

    alert = alert_details(ward_id)

    return {
        "ward_id": ward_id,
        "ward_name": ward["ward_name"],
        "zone": ward["zone"],
        "timestamp": f"{latest_hourly['date']}T{latest_hourly.get('time', '15:30:00')}",
        "data_status": {
            "type": "OBSERVED",
            "label": "Supplied Bhopal MET Norway observation with ward interpolation",
            "date": latest_hourly["date"],
            "is_prototype": True,
        },
        "weather": {
            "temperature": latest_hourly["temperature"],
            "humidity": latest_hourly["humidity"],
            "wind_speed": latest_hourly["wind_speed"],
            "atmospheric_pressure": latest_hourly.get("atmospheric_pressure", 1002.0),
            "uv_index": latest_hourly.get("uv_index", 8.0),
            "solar_radiation": latest_hourly.get("solar_radiation", 650.0),
        },
        "thermal_metrics": {
            "wbgt": thermal["wbgt"],
            "utci": thermal["utci"],
            "heat_index": thermal["heat_index"],
            "htsi": thermal["htsi"],
            "thermal_stress_level": thermal["thermal_stress_level"],
            "alert_level": alert["current_alert_level"],
        },
        "htsi_details": thermal["htsi_details"],
        "risk_drivers": thermal["risk_drivers"],
        "alert": alert,
        "demographics": {
            "population": ward["population"],
            "elderly_percentage": ward["elderly_percentage"],
            "outdoor_workers_percentage": ward["outdoor_workers_percentage"],
            "elevation_m": ward.get("elevation_m", 515),
            "vegetation_coverage": ward.get("vegetation_coverage", "Medium"),
            "urban_density": ward.get("urban_density", "Medium"),
            "healthcare_facilities_count": ward.get("healthcare_facilities", 2),
        },
    }


def alert_details(ward_id: str) -> dict[str, Any]:
    ward = ward_or_404(ward_id)
    latest = daily_weather_for(ward_id, 1)[0]
    level = latest["alert_level"]
    details = {
        "Green": (
            "Normal thermal condition. General populace can continue standard outdoor routines.",
            ["None identified; routine baseline"],
            "Drink plenty of water. Maintain routine hydration.",
            "#15803d",
        ),
        "Yellow": (
            "Precautionary heat advisory. Thermal discomfort noticeable during peak solar hours.",
            ["elderly", "infants", "outdoor workers with prolonged exposure"],
            "Reduce direct sun exposure between 12:00-15:00. Carry water while commuting.",
            "#b45309",
        ),
        "Orange": (
            "High caution alert. Severe thermal stress risks heat exhaustion and rapid dehydration.",
            ["elderly", "children", "outdoor laborers", "street vendors", "chronic patients"],
            "Stay in shaded/cooled areas. Mandate rest breaks. Check on elderly neighbors.",
            "#c2410c",
        ),
        "Red": (
            "Severe heat emergency warning. Extreme physiological strain with high heat stroke risk.",
            ["all populations; critical danger to outdoor workers and vulnerable groups"],
            "Halt strenuous outdoor labor. Open municipal cooling shelters. Seek immediate medical aid if dizzy or delirious.",
            "#b91c1c",
        ),
    }[level]

    calculated = {
        "wbgt": latest["wbgt"],
        "utci": latest["utci"],
        "heat_index": latest["heat_index"],
        "thermal_stress_level": ThermalStressEngine.classify_thermal_stress(latest["wbgt"]),
        "alert_level": level,
    }
    valid_from = datetime.fromisoformat(latest["date"])
    return {
        "ward_id": ward_id,
        "ward_name": ward["ward_name"],
        "current_alert_level": level,
        "alert_color": details[3],
        "alert_message": details[0],
        "affected_populations": details[1],
        "valid_from": valid_from.isoformat(),
        "valid_until": (valid_from + timedelta(days=1)).isoformat(),
        "action_recommended": details[2],
        "indices": calculated,
    }


def get_ward_facilities(ward_id: str) -> dict[str, Any]:
    ward = ward_or_404(ward_id)
    name = ward["ward_name"]

    cooling_centres = [
        {
            "id": f"CC_{ward_id}_1",
            "name": f"{name} Community Hall & Cooling Space",
            "address": f"Near {name} Main Road",
            "capacity": 180 + (ward["population"] // 2000),
            "distance_km": 0.8,
            "has_drinking_water": True,
            "has_air_conditioning": True,
            "status": "ACTIVE_PREPARED",
            "contact": "0755-2740111",
        },
        {
            "id": f"CC_{ward_id}_2",
            "name": f"{name} Public High School Auditorium",
            "address": f"Civic Center, {name}",
            "capacity": 260 + (ward["population"] // 1500),
            "distance_km": 1.4,
            "has_drinking_water": True,
            "has_air_conditioning": False,
            "status": "STANDBY",
            "contact": "0755-2740222",
        },
    ]

    hospitals = [
        {
            "id": f"HOSP_{ward_id}_1",
            "name": f"{name} Civil & Community Health Centre",
            "type": "Public Community Health Centre",
            "distance_km": 1.2,
            "total_beds": 60,
            "heat_stroke_beds": 12,
            "ors_packet_stock": 850,
            "saline_iv_stock": 420,
            "readiness_score": 88,
            "ambulance_available": True,
            "alert_status": "HIGH_READINESS",
        },
        {
            "id": f"HOSP_{ward_id}_2",
            "name": "Bhopal District & Medical College Hospital",
            "type": "Tertiary Referral Hospital",
            "distance_km": 4.5,
            "total_beds": 450,
            "heat_stroke_beds": 45,
            "ors_packet_stock": 3500,
            "saline_iv_stock": 1800,
            "readiness_score": 94,
            "ambulance_available": True,
            "alert_status": "MAXIMUM_READINESS",
        },
    ]

    return {
        "ward_id": ward_id,
        "ward_name": name,
        "cooling_centres": cooling_centres,
        "healthcare_facilities": hospitals,
    }


def get_seasonal_windows(ward_id: str) -> dict[str, Any]:
    """Generates seasonal calendar windows for:
    - 2026: Sep 9 - Sep 18 (10 days history) -> Sep 19 - Sep 22 (4 days forecast)
    - 2025: Sep 9 - Sep 18 (Year -1 same calendar window, DEMONSTRATION)
    - 2024: Sep 9 - Sep 18 (Year -2 same calendar window, DEMONSTRATION)
    """
    ward = ward_or_404(ward_id)
    history_2026 = get_ward_10day_history(ward_id)

    # 2026 current window
    win_2026 = [
        {"date": h["date"], "day": f"D{h['day_index']}", "utci": h["utci"], "htsi": h["htsi"], "alert": h["alert_level"], "type": "OBSERVED" if h["data_status"] == "OBSERVED" else "BASELINE"}
        for h in history_2026
    ]

    # 2025 demonstration window
    win_2025 = []
    for h in history_2026:
        d2025 = h["date"].replace("2026-", "2025-")
        utci_2025 = round(h["utci"] - 1.1 + ((int(h["date"][-2:]) % 3) * 0.6), 1)
        alert_2025 = ThermalStressEngine.classify_alert_level(utci_2025)
        win_2025.append({"date": d2025, "day": f"D{h['day_index']}", "utci": utci_2025, "htsi": round(max(30, h["htsi"] - 6.0), 1), "alert": alert_2025, "type": "DEMONSTRATION"})

    # 2024 demonstration window
    win_2024 = []
    for h in history_2026:
        d2024 = h["date"].replace("2026-", "2024-")
        utci_2024 = round(h["utci"] - 2.2 + ((int(h["date"][-2:]) % 4) * 0.5), 1)
        alert_2024 = ThermalStressEngine.classify_alert_level(utci_2024)
        win_2024.append({"date": d2024, "day": f"D{h['day_index']}", "utci": utci_2024, "htsi": round(max(25, h["htsi"] - 10.0), 1), "alert": alert_2024, "type": "DEMONSTRATION"})

    return {
        "ward_id": ward_id,
        "ward_name": ward["ward_name"],
        "seasonal_comparison": {
            "2026_current_window": {
                "year": 2026,
                "label": "2026 Current Seasonal Window (Observed 10-Day Pre-Forecast)",
                "data_status": "OBSERVED_SNAPSHOT",
                "days": win_2026,
                "avg_utci": round(sum(d["utci"] for d in win_2026) / len(win_2026), 1),
                "avg_htsi": round(sum(d["htsi"] for d in win_2026) / len(win_2026), 1),
            },
            "2025_same_window": {
                "year": 2025,
                "label": "2025 Same Seasonal Window (Sep 09 - Sep 18)",
                "data_status": "DEMONSTRATION",
                "days": win_2025,
                "avg_utci": round(sum(d["utci"] for d in win_2025) / len(win_2025), 1),
                "avg_htsi": round(sum(d["htsi"] for d in win_2025) / len(win_2025), 1),
            },
            "2024_same_window": {
                "year": 2024,
                "label": "2024 Same Seasonal Window (Sep 09 - Sep 18)",
                "data_status": "DEMONSTRATION",
                "days": win_2024,
                "avg_utci": round(sum(d["utci"] for d in win_2024) / len(win_2024), 1),
                "avg_htsi": round(sum(d["htsi"] for d in win_2024) / len(win_2024), 1),
            },
        },
        "methodology_note": "Seasonal comparative windows align multi-year calendar thermal profiles to evaluate inter-annual heat severity. Historical years use structured demonstration baselines pending long-term IMD station archive link.",
    }
