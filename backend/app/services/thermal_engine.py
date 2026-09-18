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
    def calculate(cls, weather: WeatherInput) -> dict:
        wbgt = cls.calculate_wbgt(weather)
        utci = cls.calculate_utci(weather)
        heat_index = cls.calculate_heat_index(weather)
        return {
            "wbgt": wbgt,
            "utci": utci,
            "heat_index": heat_index,
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
