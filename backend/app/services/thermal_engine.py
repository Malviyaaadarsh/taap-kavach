from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class WeatherInput:
    temperature: float
    humidity: float
    wind_speed: float
    atmospheric_pressure: float
    uv_index: float
    solar_radiation: float

    def validate(self) -> None:
        if not -20 <= self.temperature <= 60:
            raise ValueError("temperature must be between -20 and 60 C")
        if not 0 <= self.humidity <= 100:
            raise ValueError("humidity must be between 0 and 100 percent")
        if not 0 <= self.wind_speed <= 150:
            raise ValueError("wind_speed must be between 0 and 150 km/h")
        if not 850 <= self.atmospheric_pressure <= 1100:
            raise ValueError("atmospheric_pressure must be between 850 and 1100 hPa")
        if not 0 <= self.uv_index <= 20 or not 0 <= self.solar_radiation <= 1400:
            raise ValueError("uv_index or solar_radiation is outside the supported range")


class ThermalStressEngine:
    """Practical prototype calculations; replace with validated operational models later."""

    @staticmethod
    def _vapour_pressure(temperature: float, humidity: float) -> float:
        return (humidity / 100) * 6.105 * math.exp((17.27 * temperature) / (237.7 + temperature))

    @classmethod
    def calculate_wbgt(cls, weather: WeatherInput) -> float:
        weather.validate()
        vapour = cls._vapour_pressure(weather.temperature, weather.humidity)
        wet_bulb = weather.temperature * math.atan(0.151977 * (vapour + 8.313659) ** 0.5)
        wet_bulb += math.atan(weather.temperature + weather.humidity) - math.atan(weather.humidity - 1.676331)
        wet_bulb += 0.00391838 * weather.humidity ** 1.5 * math.atan(0.023101 * weather.humidity) - 4.686035
        globe = weather.temperature + (weather.solar_radiation / 600) - (weather.wind_speed * 0.04)
        return round(0.7 * wet_bulb + 0.2 * globe + 0.1 * weather.temperature, 2)

    @classmethod
    def calculate_utci(cls, weather: WeatherInput) -> float:
        weather.validate()
        vapour = cls._vapour_pressure(weather.temperature, weather.humidity)
        radiant_delta = min(12, weather.solar_radiation / 80)
        wind_effect = min(8, weather.wind_speed * 0.08)
        value = weather.temperature + 0.18 * vapour + 0.12 * radiant_delta - 0.08 * wind_effect
        return round(value, 2)

    @staticmethod
    def calculate_heat_index(weather: WeatherInput) -> float:
        weather.validate()
        temperature_c, humidity = weather.temperature, weather.humidity
        temperature_f = temperature_c * 9 / 5 + 32
        if temperature_f < 80 or humidity < 40:
            return round(temperature_c + 0.1 * humidity * max(0, temperature_c - 20) / 10, 2)
        hi_f = (-42.379 + 2.04901523 * temperature_f + 10.14333127 * humidity - 0.22475541 * temperature_f * humidity
                - 0.00683783 * temperature_f ** 2 - 0.05481717 * humidity ** 2 + 0.00122874 * temperature_f ** 2 * humidity
                + 0.00085282 * temperature_f * humidity ** 2 - 0.00000199 * temperature_f ** 2 * humidity ** 2)
        return round((hi_f - 32) * 5 / 9, 2)

    @classmethod
    def calculate_htsi(cls, weather: WeatherInput, wbgt: float | None = None, utci: float | None = None, heat_index: float | None = None) -> dict:
        weather.validate()
        wbgt = wbgt if wbgt is not None else cls.calculate_wbgt(weather)
        utci = utci if utci is not None else cls.calculate_utci(weather)
        hi = heat_index if heat_index is not None else cls.calculate_heat_index(weather)

        # Normalized sub-scores on a 0-100 scale
        utci_norm = max(0.0, min(100.0, (utci - 20.0) / 30.0 * 100.0))
        wbgt_norm = max(0.0, min(100.0, (wbgt - 18.0) / 18.0 * 100.0))
        hi_norm = max(0.0, min(100.0, (hi - 22.0) / 30.0 * 100.0))
        rad_norm = max(0.0, min(100.0, weather.solar_radiation / 800.0 * 100.0))
        hum_norm = max(0.0, min(100.0, max(0.0, weather.humidity - 35.0) / 50.0 * 100.0))
        wind_mitigation = min(12.0, weather.wind_speed * 0.45)

        raw_score = (0.35 * utci_norm + 0.25 * wbgt_norm + 0.20 * hi_norm + 0.12 * rad_norm + 0.08 * hum_norm) - wind_mitigation
        score = round(max(0.0, min(100.0, raw_score)), 1)

        if score < 40:
            category = "Low"
            alert = "Green"
        elif score < 60:
            category = "Moderate"
            alert = "Yellow"
        elif score < 80:
            category = "High"
            alert = "Orange"
        else:
            category = "Extreme"
            alert = "Red"

        contributors = [
            {"factor": "Universal Thermal Climate Index (UTCI)", "weight_pct": 35, "contribution_score": round(0.35 * utci_norm, 1), "value": f"{utci} °C"},
            {"factor": "Wet-Bulb Globe Temperature (WBGT)", "weight_pct": 25, "contribution_score": round(0.25 * wbgt_norm, 1), "value": f"{wbgt} °C"},
            {"factor": "Heat Index (HI)", "weight_pct": 20, "contribution_score": round(0.20 * hi_norm, 1), "value": f"{hi} °C"},
            {"factor": "Solar Radiation Load", "weight_pct": 12, "contribution_score": round(0.12 * rad_norm, 1), "value": f"{weather.solar_radiation} W/m²"},
            {"factor": "Relative Humidity Stress", "weight_pct": 8, "contribution_score": round(0.08 * hum_norm, 1), "value": f"{weather.humidity}%"}
        ]
        contributors.sort(key=lambda item: item["contribution_score"], reverse=True)

        return {
            "score": score,
            "risk_category": category,
            "alert_level": alert,
            "label": "Taap Kavach HTSI — Prototype Composite Score",
            "scale": "0-100",
            "top_contributors": contributors[:3],
            "all_contributors": contributors,
            "mitigating_factors": [
                {"factor": "Wind Ventilation", "reduction_pts": round(wind_mitigation, 1), "value": f"{weather.wind_speed} km/h"}
            ]
        }

    @classmethod
    def get_risk_drivers(cls, weather: WeatherInput, utci: float, htsi: dict, vegetation: str = "Medium") -> dict:
        elevated = []
        if utci >= 38:
            elevated.append({"title": "Elevated UTCI perceived heat", "impact": "High", "detail": f"Perceived thermal temperature {utci}°C exceeds human comfort envelope."})
        elif utci >= 32:
            elevated.append({"title": "Moderate perceived thermal stress", "impact": "Medium", "detail": f"UTCI at {utci}°C requires caution for sustained exposure."})

        if weather.humidity >= 55:
            elevated.append({"title": "High humidity impedance", "impact": "High", "detail": f"Humidity at {weather.humidity}% severely inhibits evaporative cooling (sweat evaporation)."})
        elif weather.humidity >= 45:
            elevated.append({"title": "Sustained humidity level", "impact": "Moderate", "detail": f"Humidity at {weather.humidity}% compounds physiological thermal load."})

        if weather.solar_radiation >= 500:
            elevated.append({"title": "Intense direct solar irradiance", "impact": "High", "detail": f"Solar radiation of {weather.solar_radiation} W/m² delivers direct radiant energy."})
        elif weather.solar_radiation >= 250:
            elevated.append({"title": "Moderate solar radiation", "impact": "Moderate", "detail": f"Radiation at {weather.solar_radiation} W/m² adds to surface heating."})

        protective = []
        if weather.wind_speed >= 12:
            protective.append({"title": "Active wind ventilation", "impact": "High", "detail": f"Wind at {weather.wind_speed} km/h enhances convective and evaporative heat dissipation."})
        elif weather.wind_speed >= 7:
            protective.append({"title": "Moderate wind circulation", "impact": "Moderate", "detail": f"Breeze at {weather.wind_speed} km/h provides partial convective relief."})

        if vegetation == "High":
            protective.append({"title": "Dense canopy vegetation", "impact": "High", "detail": "Substantial tree cover produces localized microclimatic shading and cooling."})
        elif vegetation == "Medium":
            protective.append({"title": "Moderate urban green buffer", "impact": "Moderate", "detail": "Presence of vegetation partially softens urban heat island effects."})

        return {
            "elevated_contributors": elevated,
            "protective_contributors": protective
        }

    @classmethod
    def calculate(cls, weather: WeatherInput, vegetation: str = "Medium") -> dict:
        wbgt = cls.calculate_wbgt(weather)
        utci = cls.calculate_utci(weather)
        heat_index = cls.calculate_heat_index(weather)
        htsi = cls.calculate_htsi(weather, wbgt=wbgt, utci=utci, heat_index=heat_index)
        risk_drivers = cls.get_risk_drivers(weather, utci=utci, htsi=htsi, vegetation=vegetation)
        return {
            "wbgt": wbgt,
            "utci": utci,
            "heat_index": heat_index,
            "htsi": htsi["score"],
            "htsi_details": htsi,
            "risk_drivers": risk_drivers,
            "thermal_stress_level": cls.classify_thermal_stress(wbgt),
            "alert_level": cls.classify_alert_level(utci),
        }

    @staticmethod
    def classify_thermal_stress(wbgt: float) -> str:
        if wbgt < 26: return "Low"
        if wbgt < 29: return "Moderate"
        if wbgt < 32: return "High"
        return "Extreme"

    @staticmethod
    def classify_alert_level(stress_value: float) -> str:
        if stress_value < 35: return "Green"
        if stress_value < 38: return "Yellow"
        if stress_value < 40: return "Orange"
        return "Red"

