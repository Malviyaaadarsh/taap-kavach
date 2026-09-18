from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.thermal_engine import ThermalStressEngine, WeatherInput
from app.services.data_store import load_weather

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = ROOT / "data" / "thermal_indices_calculated.json"


def calculate() -> None:
    indices = []
    for record in load_weather():
        values = ThermalStressEngine.calculate(WeatherInput(**{key: record[key] for key in WeatherInput.__annotations__}))
        indices.append({"ward_id": record["ward_id"], "date": record["date"], "time": record["time"], **values})
    OUTPUT_PATH.write_text(json.dumps({"thermal_indices": indices, "data_source": "Taap Kavach thermal engine applied to supplied ward-interpolated observations"}, indent=2), encoding="utf-8")
    print(f"Calculated {len(indices)} thermal index records")


if __name__ == "__main__":
    calculate()
