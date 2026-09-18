# Setup Guide

## Prerequisites

- Python 3.10+ (tested with the workspace Python 3.13.2)
- Node.js 18+
- Internet access for the OpenStreetMap tile layer in the browser (the rest runs locally)

## Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
cd ..
python backend\scripts\populate_real_weather_data.py
python backend\scripts\calculate_thermal_indices.py
python backend\scripts\train_model.py
python backend\run.py
```
API: `http://localhost:8000`  
Swagger: `http://localhost:8000/docs`  
Health check: `http://localhost:8000/api/health`

`populate_real_weather_data.py` writes 400 hourly records (10 wards x 5 days x 8 observations) and 50 daily ward summaries from the supplied September 14-18, 2026 Bhopal data. `train_model.py` then retrains the XGBoost artifact from those observations. Copy `backend/.env.example` to `backend/.env` if you want to set a local JWT secret or CORS origin. The built-in development fallback secret is only for local demonstration.

`requirements.txt` is intentionally lean for the Vercel serverless API and does not include XGBoost, Pandas, scikit-learn, or NumPy. Use `requirements-dev.txt` for local training, tests, and Uvicorn.

## Frontend

In a second terminal:

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Dashboard: `http://localhost:5173`

## Demo credentials

- Local administration: `admin.bhopal@taapkavach.gov.in` / `demo-admin`
- Healthcare facility: `healthcare.hospital@taapkavach.gov.in` / `demo-health`

The public dashboard does not require login. Use the stakeholder login to open the role-specific navigation.

## Useful checks

```powershell
pytest backend/tests -q
cd frontend
npm run build
```
