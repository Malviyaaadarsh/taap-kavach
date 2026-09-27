from __future__ import annotations

import json
from math import isfinite
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .thermal_engine import ThermalStressEngine, WeatherInput


class LocationWeatherError(RuntimeError):
    pass


def _get_json(url: str, user_agent: str) -> dict:
    request = Request(url, headers={"User-Agent": user_agent, "Accept": "application/json"})
    try:
        with urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as error:
        raise LocationWeatherError from error


def _number(value: object, default: float) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if isfinite(result) else default


def get_location_weather(latitude: float, longitude: float) -> dict:
    weather_query = urlencode({
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,wind_speed_10m,pressure_msl,uv_index,shortwave_radiation",
        "timezone": "auto",
    })
    weather = _get_json(f"https://api.open-meteo.com/v1/forecast?{weather_query}", "Taap-Kavach/2.0 contact: taap-kavach@example.invalid")
    current = weather.get("current") or {}
    values = {
        "temperature": _number(current.get("temperature_2m"), 0),
        "humidity": _number(current.get("relative_humidity_2m"), 0),
        "wind_speed": _number(current.get("wind_speed_10m"), 0),
        "atmospheric_pressure": _number(current.get("pressure_msl"), 1013),
        "uv_index": _number(current.get("uv_index"), 0),
        "solar_radiation": _number(current.get("shortwave_radiation"), 0),
    }
    thermal = ThermalStressEngine.calculate(WeatherInput(**values))
    guidance = {
        "Green": {
            "headline": "Normal conditions",
            "summary": "Continue normal activities and keep drinking water through the day.",
            "steps": ["Drink water regularly.", "Wear light clothing outdoors."],
        },
        "Yellow": {
            "headline": "Take precautions",
            "summary": "Heat stress is rising. Reduce prolonged exposure during the hottest hours.",
            "steps": ["Carry water and take shade breaks.", "Avoid strenuous outdoor activity from midday to mid-afternoon."],
        },
        "Orange": {
            "headline": "High heat: protect yourself",
            "summary": "Sustained exposure can cause heat exhaustion. Move to a cool place if you feel unwell.",
            "steps": ["Drink water regularly, even before thirst.", "Limit prolonged outdoor exposure during peak afternoon heat."],
        },
        "Red": {
            "headline": "Severe heat: avoid outdoor activity",
            "summary": "Extreme heat can cause life-threatening illness. Stay in a cool place when possible.",
            "steps": ["Stop strenuous outdoor activity.", "Call emergency services for confusion, fainting, or severe symptoms."],
        },
    }[thermal["alert_level"]]

    location_query = urlencode({"lat": latitude, "lon": longitude, "format": "jsonv2", "zoom": 10})
    try:
        reverse = _get_json(f"https://nominatim.openstreetmap.org/reverse?{location_query}", "Taap-Kavach/2.0 contact: taap-kavach@example.invalid")
        address = reverse.get("address") or {}
        location_name = ", ".join(part for part in (address.get("city") or address.get("town") or address.get("village"), address.get("state")) if part) or "Detected location"
    except LocationWeatherError:
        location_name = "Detected location"

    return {
        "location": {"latitude": latitude, "longitude": longitude, "name": location_name},
        "current": {
            "observed_at": current.get("time"),
            "temperature": values["temperature"],
            "feels_like": _number(current.get("apparent_temperature"), values["temperature"]),
            "humidity": values["humidity"],
            "wind_speed": values["wind_speed"],
            "pressure": values["atmospheric_pressure"],
            "uv_index": values["uv_index"],
            "solar_radiation": values["solar_radiation"],
            "wbgt": thermal["wbgt"],
            "utci": thermal["utci"],
            "heat_index": thermal["heat_index"],
        },
        "risk": {
            "level": thermal["alert_level"],
            "htsi": thermal["htsi"],
            "thermal_stress_level": thermal["thermal_stress_level"],
            "explanation": "Risk classification is calculated by the Taap Kavach thermal engine from current weather conditions.",
        },
        "advisory": {
            **guidance,
            "warning_signs": ["Dizziness", "Unusual weakness", "Headache", "Nausea", "Confusion", "Fainting"],
            "emergency_contacts": [{"service": "Ambulance / Medical Emergency", "number": "108"}, {"service": "National Emergency Support System", "number": "112"}],
        },
        "resources": {
            "available": False,
            "message": "Verified nearby resource coordinates are not available for this location yet.",
            "items": [],
        },
        "data_source": "Open-Meteo current weather with Taap Kavach thermal calculations",
    }
