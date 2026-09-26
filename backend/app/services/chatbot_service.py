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
    elif any(word in text for word in ("htsi", "human thermal", "composite", "score")):
        message = f"In {ward['ward_name']}, the Taap Kavach HTSI composite score is derived from UTCI, WBGT, Heat Index, solar radiation, and humidity with wind mitigation. It provides an explainable 0-100 human stress index for civic heat action."
    elif any(word in text for word in ("forecast", "tomorrow", "peak", "warning", "early warning", "next")):
        message = f"For {ward['ward_name']}, early warning projects peak thermal stress around Day +2 with elevated conditions moderating by Day +4. Review the 10-day history and 4-day forecast charts for model breakdown."
    elif any(word in text for word in ("worker", "outdoor", "delivery", "construction")):
        message = f"For {ward['ward_name']} ({level}), shift strenuous outdoor work to 05:30-10:00 and post-17:00, enforce 15-minute shade/water breaks, and stop work for dizziness or confusion."
    elif any(word in text for word in ("hospital", "health", "bed", "fluid", "doctor")):
        message = f"Healthcare facilities serving {ward['ward_name']} should verify dedicated heat beds, oral rehydration solutions (ORS), IV saline, cold packs, and circulate heat illness protocols."
    elif any(word in text for word in ("wbgt", "utci", "heat index", "thermal")):
        message = f"{ward['ward_name']} latest values: WBGT {latest['wbgt']:.1f} °C, UTCI {latest['utci']:.1f} °C, and Heat Index {latest['heat_index']:.1f} °C. UTCI serves as the primary alert authority in this prototype."
    elif any(word in text for word in ("elderly", "older", "children", "child", "sick", "vulnerable")):
        message = f"During {level} alert in {ward['ward_name']}, elderly citizens and young children face higher physiological strain. Keep them in shaded/cooled rooms and hydrate frequently."
    elif any(word in text for word in ("colour", "color", "green", "yellow", "orange", "red", "alert")):
        message = "Green is normal routine; Yellow calls for daytime precaution; Orange requires caution for vulnerable workers and elders; Red is severe heat emergency requiring outdoor cessation and cooling shelters."
    else:
        message = "I can explain this ward's alert level, why risk is elevated, the 4-day early warning forecast, HTSI score, healthcare readiness, or recommended municipal actions."
    return {"answer": message, "ward_id": ward_id, "ward_name": ward["ward_name"], "alert_level": level, "provider": "local-rule-engine", "data_period": "2026-09-14 to 2026-09-18"}
