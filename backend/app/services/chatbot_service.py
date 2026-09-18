from __future__ import annotations

from dataclasses import dataclass

from .data_store import daily_weather_for, load_daily_summary, load_wards, ward_or_404


@dataclass(frozen=True)
class ChatContext:
    ward_id: str
    question: str


def _latest_summary(ward_id: str) -> dict:
    return daily_weather_for(ward_id, 1)[0]


def _comparison() -> tuple[dict, dict]:
    latest_by_ward = {ward_id: daily_weather_for(ward_id, 1)[0] for ward_id in {row["ward_id"] for row in load_daily_summary()}}
    wards = {ward["ward_id"]: ward for ward in load_wards()}
    hottest_id = max(latest_by_ward, key=lambda ward_id: latest_by_ward[ward_id]["temperature"])
    coolest_id = min(latest_by_ward, key=lambda ward_id: latest_by_ward[ward_id]["temperature"])
    return ({**latest_by_ward[hottest_id], "ward_name": wards[hottest_id]["ward_name"]},
            {**latest_by_ward[coolest_id], "ward_name": wards[coolest_id]["ward_name"]})


def answer(question: str, ward_id: str) -> dict:
    ward = ward_or_404(ward_id)
    latest = _latest_summary(ward_id)
    hottest, coolest = _comparison()
    text = question.lower().strip()
    level = latest["alert_level"]

    if any(word in text for word in ("source", "data", "updated", "real")):
        message = "This dashboard uses the supplied MET Norway Bhopal snapshot for 14-18 September 2026 with ward-level interpolation. It is not a live feed."
    elif any(word in text for word in ("hottest", "coolest", "compare", "ranking")):
        message = f"On 18 September, {hottest['ward_name']} is hottest at {hottest['temperature']:.1f} C ({hottest['alert_level']}), while {coolest['ward_name']} is coolest at {coolest['temperature']:.1f} C ({coolest['alert_level']})."
    elif any(word in text for word in ("why", "risk", "reason", "hot")):
        message = f"{ward['ward_name']} is currently {level}. Its latest ward summary is {latest['temperature']:.1f} C, WBGT {latest['wbgt']:.1f} C, UTCI {latest['utci']:.1f} C, and Heat Index {latest['heat_index']:.1f} C. Local characteristics such as urban density, vegetation, elevation, and ward offsets influence this result."
    elif any(word in text for word in ("forecast", "tomorrow", "next five")):
        message = f"{ward['ward_name']} is currently {level}. The five-day XGBoost forecast is available in the dashboard; its confidence score is a prototype model signal, not a guarantee."
    elif any(word in text for word in ("worker", "outdoor", "delivery", "construction")):
        message = f"For {ward['ward_name']} ({level}), shift strenuous outdoor work to cooler hours, take shade and water breaks, and stop for dizziness, confusion, or unusual weakness."
    elif any(word in text for word in ("hospital", "health", "bed", "fluid")):
        message = f"Healthcare teams serving {ward['ward_name']} should check cooling equipment, IV fluid and ORS stock, triage protocols, staff briefings, and surge beds."
    elif any(word in text for word in ("wbgt", "utci", "heat index", "thermal")):
        message = f"{ward['ward_name']} latest values are WBGT {latest['wbgt']:.1f} C, UTCI {latest['utci']:.1f} C, and Heat Index {latest['heat_index']:.1f} C. UTCI drives the alert colour in this prototype."
    elif any(word in text for word in ("elderly", "older", "children", "child", "sick")):
        message = f"During {level} conditions in {ward['ward_name']}, vulnerable people should avoid peak afternoon heat, stay hydrated, use a cool room, and have someone check on them."
    elif any(word in text for word in ("colour", "color", "green", "yellow", "orange", "red", "alert")):
        message = "Green is normal monitoring; Yellow means precautions; Orange prioritises vulnerable groups; Red means severe heat stress and avoiding non-essential outdoor activity."
    else:
        message = "I can answer about this ward's alert, local ward comparison, five-day forecast, WBGT/UTCI, data source, or safety actions."
    return {"answer": message, "ward_id": ward_id, "ward_name": ward["ward_name"], "alert_level": level, "provider": "local-rule-engine", "data_period": "2026-09-14 to 2026-09-18"}
