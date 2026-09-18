from __future__ import annotations

import pickle
import sys
from datetime import date
from pathlib import Path

import numpy as np

# Make direct execution from the repository root resolve backend/app imports.
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.data_store import load_weather
from app.services.thermal_engine import ThermalStressEngine, WeatherInput

ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = ROOT / "ml-models" / "xgboost_model.pkl"
FEATURES = ["temperature", "humidity", "wind_speed", "atmospheric_pressure", "uv_index", "solar_radiation", "day_of_year", "ward_index"]

def train() -> None:
    import xgboost as xgb
    records = load_weather()
    X, y = [], []
    for index, record in enumerate(records):
        date_value = date.fromisoformat(record["date"])
        ward_index = int(record["ward_id"].split("_")[-1].lstrip("W")) - 1
        hour = int(record["time"].split(":")[0]) if "time" in record else 12
        X.append([record["temperature"], record["humidity"], record["wind_speed"], record["atmospheric_pressure"], record["uv_index"], record["solar_radiation"], date_value.timetuple().tm_yday, ward_index, hour])
        y.append(ThermalStressEngine.calculate(WeatherInput(**{k: record[k] for k in WeatherInput.__annotations__}))["utci"])
    model = xgb.XGBRegressor(n_estimators=120, max_depth=4, learning_rate=0.06, objective="reg:squarederror", random_state=2026, n_jobs=1)
    model.fit(np.asarray(X), np.asarray(y))
    MODEL_PATH.parent.mkdir(exist_ok=True)
    with MODEL_PATH.open("wb") as handle:
        pickle.dump(model, handle)
    print(f"Saved {MODEL_PATH} with {len(X)} records")

if __name__ == "__main__":
    train()
