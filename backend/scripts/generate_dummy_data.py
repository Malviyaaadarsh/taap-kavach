from __future__ import annotations

import json
import math
import random
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"

WARD_NAMES = [("Berasia", "North"), ("Arera Colony", "South"), ("Kolar", "South-West"), ("Govindpura", "East"), ("Bairagarh", "West"), ("TT Nagar", "Central"), ("Shahpura", "South-East"), ("Karond", "North-East"), ("Ayodhya Bypass", "North-East"), ("Jehangirabad", "Central")]
WARD_COORDINATES = [
    (23.350, 77.415),  # Berasia corridor, north edge
    (23.215, 77.433),  # Arera Colony
    (23.170, 77.365),  # Kolar Road
    (23.270, 77.475),  # Govindpura
    (23.286, 77.337),  # Bairagarh
    (23.230, 77.405),  # TT Nagar
    (23.190, 77.470),  # Shahpura
    (23.320, 77.425),  # Karond
    (23.315, 77.485),  # Ayodhya Bypass
    (23.280, 77.420),  # Jehangirabad
]

def wards() -> list[dict]:
    result = []
    for index, (name, zone) in enumerate(WARD_NAMES, 1):
        latitude, longitude = WARD_COORDINATES[index - 1]
        result.append({"ward_id": f"BPL_W{index:03d}", "ward_name": name, "zone": zone,
                       "population": 92000 + index * 7100, "elderly_percentage": 8 + index % 9,
                   "outdoor_workers_percentage": 16 + index % 14, "latitude": latitude,
                   "longitude": longitude, "healthcare_facilities": 2 + index % 4})
    return result

def generate(days: int = 90, seed: int = 2026) -> None:
    random.seed(seed)
    ward_list = wards()
    start = date.today() - timedelta(days=days - 1)
    records = []
    for ward_index, ward in enumerate(ward_list):
        for offset in range(days):
            seasonal = 3.8 * math.sin((offset / days) * math.pi * 1.5)
            urban = ward_index * 0.12
            temperature = 34.5 + seasonal + urban + random.uniform(-1.8, 1.8)
            humidity = 43 - seasonal * 1.7 + random.uniform(-7, 7)
            humidity = max(22, min(78, humidity))
            records.append({"ward_id": ward["ward_id"], "date": (start + timedelta(days=offset)).isoformat(),
                            "temperature": round(temperature, 2), "humidity": round(humidity, 2),
                            "wind_speed": round(max(3, 12 + random.uniform(-4, 7)), 2),
                            "atmospheric_pressure": round(1001 + random.uniform(-4, 4), 2),
                            "uv_index": round(max(4, min(12, 8 + seasonal / 2 + random.uniform(-1, 1))), 1),
                            "solar_radiation": round(max(380, min(980, 660 + seasonal * 25 + random.uniform(-70, 70))), 1)})
    DATA.mkdir(exist_ok=True)
    (DATA / "wards.json").write_text(json.dumps({"wards": ward_list}, indent=2), encoding="utf-8")
    (DATA / "weather_history.json").write_text(json.dumps({"weather_records": records}, indent=2), encoding="utf-8")

if __name__ == "__main__":
    generate()
