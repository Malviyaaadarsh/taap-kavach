from __future__ import annotations

import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"

CITY_DATA = {
    "2026-09-14": [("00:30", 28, 62, 8, 1005, 0, 0), ("03:30", 27, 67, 7, 1003, 0, 0), ("06:30", 27, 73, 27, 1005, 2, 100), ("09:30", 29, 65, 10, 1006, 5, 350), ("12:30", 33, 47, 13, 1005, 9, 700), ("15:30", 35, 41, 12, 1002, 8, 650), ("18:30", 33, 43, 17, 1001, 2, 150), ("21:30", 29, 60, 8, 1004, 0, 0)],
    "2026-09-15": [("00:30", 26, 80, 4, 1004, 0, 0), ("03:30", 26, 78, 6, 1004, 0, 0), ("06:30", 27, 67, 10, 1005, 2, 100), ("09:30", 33, 49, 12, 1006, 5, 350), ("12:30", 37, 33, 10, 1004, 9, 700), ("15:30", 38, 30, 11, 1002, 8, 650), ("18:30", 35, 35, 35, 1002, 2, 150), ("21:30", 28, 64, 7, 1006, 0, 0)],
    "2026-09-16": [("00:30", 25, 82, 5, 1005, 0, 0), ("03:30", 24, 84, 6, 1005, 0, 0), ("06:30", 25, 78, 8, 1005, 2, 100), ("09:30", 32, 52, 13, 1006, 5, 350), ("12:30", 38, 32, 12, 1003, 9, 700), ("15:30", 39, 29, 13, 1002, 8, 650), ("18:30", 36, 33, 16, 1001, 2, 150), ("21:30", 28, 62, 8, 1006, 0, 0)],
    "2026-09-17": [("00:30", 24, 83, 5, 1006, 0, 0), ("03:30", 23, 85, 5, 1006, 0, 0), ("06:30", 24, 79, 7, 1006, 2, 100), ("09:30", 33, 50, 14, 1006, 5, 350), ("12:30", 39, 30, 13, 1003, 9, 700), ("15:30", 40, 28, 14, 1001, 8, 650), ("18:30", 37, 32, 17, 1000, 2, 150), ("21:30", 28, 61, 8, 1006, 0, 0)],
    "2026-09-18": [("00:30", 23, 84, 5, 1006, 0, 0), ("03:30", 22, 86, 5, 1006, 0, 0), ("06:30", 23, 80, 7, 1006, 2, 100), ("09:30", 34, 48, 14, 1006, 5, 350), ("12:30", 40, 29, 14, 1002, 9, 700), ("15:30", 41, 27, 15, 1001, 8, 650), ("18:30", 38, 31, 18, 999, 2, 150), ("21:30", 29, 60, 8, 1006, 0, 0)],
}

WARD_DEFINITIONS = [
    ("BPL_W001", "Berasia", "North", 150000, 15, 25, 23.18, 77.40, 3, 510, "High", "Medium", -0.8, 3, -1.2),
    ("BPL_W002", "Arera Colony", "South", 120000, 12, 20, 23.16, 77.58, 2, 520, "Low", "High", 1.2, -2, 0.5),
    ("BPL_W003", "Habibganj", "Central", 180000, 14, 30, 23.21, 77.45, 4, 523, "Very Low", "Very High", 2.1, -4, 1.8),
    ("BPL_W004", "Jehangirabad", "East", 110000, 11, 22, 23.22, 77.50, 2, 515, "Medium", "Medium", -0.2, 1, -0.3),
    ("BPL_W005", "Raisen Road", "West", 95000, 16, 18, 23.20, 77.35, 1, 505, "High", "Low", -1.5, 5, -2.1),
    ("BPL_W006", "Kolar Road", "Central", 140000, 13, 28, 23.19, 77.42, 3, 525, "Low", "High", 1.8, -3, 1.5),
    ("BPL_W007", "Bhel Nagar", "Industrial", 130000, 10, 35, 23.24, 77.46, 2, 495, "Very Low", "High", 2.5, -5, 2.2),
    ("BPL_W008", "Shahpura", "South", 125000, 13, 23, 23.15, 77.52, 2, 518, "Medium", "Medium", 0.5, 2, 0.2),
    ("BPL_W009", "New Market", "Central", 160000, 12, 32, 23.20, 77.43, 3, 523, "Very Low", "Very High", 2.3, -5, 2.0),
    ("BPL_W010", "Chunar Ganj", "East", 105000, 11, 26, 23.23, 77.48, 2, 516, "Low", "High", 1.0, -1, 0.8),
]

DAILY_SUMMARIES = {
    "BPL_W001": [(27.6, 64, 8.4, 26.0, 28.2, 29.0, "Green"), (29.8, 58, 10.0, 28.1, 30.7, 31.5, "Yellow"), (30.4, 55, 11.6, 28.6, 31.4, 32.3, "Yellow"), (31.3, 51, 12.3, 29.4, 32.6, 33.8, "Orange"), (32.7, 48, 12.9, 30.3, 34.1, 35.1, "Orange")],
    "BPL_W002": [(29.6, 59, 10.1, 27.8, 30.8, 31.8, "Yellow"), (31.8, 53, 11.7, 30.1, 33.2, 34.3, "Orange"), (32.4, 50, 13.3, 30.6, 33.9, 35.0, "Orange"), (33.3, 46, 14.0, 31.4, 35.2, 36.3, "Orange"), (34.7, 43, 14.6, 32.3, 36.6, 37.8, "Red")],
    "BPL_W003": [(30.5, 57, 11.4, 28.6, 32.2, 33.3, "Orange"), (32.7, 51, 13.0, 30.9, 34.8, 36.1, "Orange"), (33.3, 48, 14.6, 31.5, 35.6, 37.0, "Orange"), (34.2, 44, 15.3, 32.2, 36.8, 38.2, "Red"), (35.6, 41, 15.9, 33.2, 38.2, 39.6, "Red")],
    "BPL_W004": [(28.2, 62, 9.3, 26.7, 29.6, 30.6, "Yellow"), (30.4, 56, 10.9, 28.8, 31.9, 32.9, "Orange"), (31.0, 53, 12.5, 29.3, 32.7, 33.7, "Orange"), (31.9, 49, 13.2, 30.1, 33.9, 34.9, "Orange"), (33.3, 46, 13.8, 31.1, 35.3, 36.3, "Orange")],
    "BPL_W005": [(26.9, 66, 7.5, 25.3, 27.2, 28.0, "Green"), (29.1, 60, 9.1, 27.3, 29.8, 30.6, "Yellow"), (29.7, 57, 10.7, 27.9, 30.6, 31.5, "Yellow"), (30.6, 53, 11.4, 28.7, 31.8, 32.9, "Orange"), (32.0, 50, 12.0, 29.6, 33.2, 34.2, "Orange")],
    "BPL_W006": [(30.2, 58, 11.1, 28.3, 31.9, 33.0, "Orange"), (32.4, 52, 12.7, 30.6, 34.5, 35.7, "Orange"), (33.0, 49, 14.3, 31.2, 35.3, 36.5, "Orange"), (33.9, 45, 15.0, 31.9, 36.5, 37.9, "Red"), (35.3, 42, 15.6, 32.9, 37.9, 39.2, "Red")],
    "BPL_W007": [(30.9, 56, 11.8, 28.8, 32.7, 33.9, "Orange"), (33.1, 50, 13.4, 31.2, 35.4, 36.7, "Orange"), (33.7, 47, 15.0, 31.9, 36.2, 37.6, "Red"), (34.6, 43, 15.7, 32.6, 37.5, 39.0, "Red"), (36.0, 40, 16.3, 33.6, 38.9, 40.4, "Red")],
    "BPL_W008": [(28.9, 63, 9.8, 27.1, 30.1, 31.2, "Yellow"), (31.1, 57, 11.4, 29.3, 32.3, 33.4, "Orange"), (31.7, 54, 13.0, 29.9, 33.1, 34.3, "Orange"), (32.6, 50, 13.7, 30.7, 34.3, 35.5, "Orange"), (34.0, 47, 14.3, 31.6, 35.8, 36.9, "Red")],
    "BPL_W009": [(30.7, 56, 11.6, 28.7, 32.5, 33.7, "Orange"), (32.9, 50, 13.2, 31.0, 35.2, 36.5, "Orange"), (33.5, 47, 14.8, 31.7, 36.0, 37.4, "Red"), (34.4, 43, 15.5, 32.4, 37.3, 38.8, "Red"), (35.8, 40, 16.1, 33.4, 38.7, 40.1, "Red")],
    "BPL_W010": [(29.4, 60, 10.4, 27.5, 30.7, 31.8, "Yellow"), (31.6, 54, 12.0, 29.8, 32.9, 34.0, "Orange"), (32.2, 51, 13.6, 30.4, 33.7, 34.9, "Orange"), (33.1, 47, 14.3, 31.1, 34.9, 36.1, "Orange"), (34.5, 44, 14.9, 32.1, 36.3, 37.5, "Red")],
}


def build_wards() -> list[dict]:
    fields = ["ward_id", "ward_name", "zone", "population", "elderly_percentage", "outdoor_workers_percentage", "latitude", "longitude", "healthcare_facilities", "elevation_m", "vegetation_coverage", "urban_density", "temp_offset", "humidity_offset", "wind_offset"]
    return [dict(zip(fields, definition)) for definition in WARD_DEFINITIONS]


def generate() -> None:
    wards = build_wards()
    records = []
    offsets = {ward["ward_id"]: ward for ward in wards}
    for day, observations in CITY_DATA.items():
        for time, temperature, humidity, wind_speed, pressure, uv_index, solar_radiation in observations:
            for ward_id, ward in offsets.items():
                records.append({"ward_id": ward_id, "date": day, "time": time,
                                "temperature": round(temperature + ward["temp_offset"], 2),
                                "humidity": round(max(0, min(100, humidity + ward["humidity_offset"])), 1),
                                "wind_speed": round(max(0, wind_speed + ward["wind_offset"]), 1),
                                "atmospheric_pressure": pressure, "uv_index": uv_index,
                                "solar_radiation": solar_radiation})
    daily_records = []
    dates = list(CITY_DATA)
    for ward_id, values in DAILY_SUMMARIES.items():
        for day, value in zip(dates, values):
            temperature, humidity, wind_speed, wbgt, utci, heat_index, alert_level = value
            daily_records.append({"ward_id": ward_id, "date": day, "temperature": temperature, "humidity": humidity,
                                  "wind_speed": wind_speed, "wbgt": wbgt, "utci": utci,
                                  "heat_index": heat_index, "alert_level": alert_level})
    DATA_DIR.mkdir(exist_ok=True)
    (DATA_DIR / "wards.json").write_text(json.dumps({"wards": wards}, indent=2), encoding="utf-8")
    (DATA_DIR / "weather_history.json").write_text(json.dumps({"weather_records": records, "data_source": "MET Norway city observations with ward-level interpolation", "period": "2026-09-14 to 2026-09-18"}, indent=2), encoding="utf-8")
    (DATA_DIR / "ward_daily_summary.json").write_text(json.dumps({"daily_records": daily_records, "data_source": "Supplied Taap Kavach ward-level analysis", "confidence": "Medium; approximately 5-8 percent variance from city average"}, indent=2), encoding="utf-8")
    print(f"Generated {len(records)} hourly records and {len(daily_records)} daily ward summaries for {len(wards)} wards")


if __name__ == "__main__":
    generate()
