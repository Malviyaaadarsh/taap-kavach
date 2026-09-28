# Taap Kavach

Taap Kavach is a locally runnable heat intelligence prototype. It translates a supplied five-day Bhopal(initially) environmental snapshot and ward-level interpolation into WBGT, UTCI, Heat Index, alert levels, five-day forecasts, and preparedness recommendations for citizens, municipal teams, and healthcare facilities.

> **Prototype disclaimer:** the current snapshot is supplied MET Norway city data with ward-level interpolation and medium confidence. Forecasts are demonstration outputs, recommendations are informational, and this is neither an official IMD alerting system nor a medical diagnosis tool.

## Stack

- **Frontend:** React, Vite, React Router, Recharts, React Leaflet, Axios
- **Backend:** FastAPI, Pydantic, SQLite user store, PyJWT, XGBoost, NumPy/Pandas
- **Data:** 10 Bhopal wards, 400 supplied/interpolated hourly observations from September 14-18, 2026, 400 persisted calculated index records, and 50 daily ward summaries

## Run

See [SETUP.md](SETUP.md) for Windows-first commands. In brief, start the backend on `http://localhost:8000`, then the frontend on `http://localhost:5173`. Swagger is available at `http://localhost:8000/docs`.

## Features

- Public ward dashboard with current alert, metrics, five-day history and forecast
- WBGT, UTCI, Heat Index, thermal classification, and consistent Green/Yellow/Orange/Red thresholds
- XGBoost artifact retrained on the supplied hourly observations and reproducible data/model scripts
- JWT login with local administration and healthcare facility roles
- Prototype municipal suggestions, hospital readiness, and simulated SMS record
- Leaflet representative ward map and rule-based contextual chatbot
- Context-aware chatbot with presentation prompts, backend chat contract, and future Gemini/time-series provider boundaries
- Future integration placeholders documented in [ROADMAP.md](ROADMAP.md)

See [working.md](working.md) for the complete system explanation and presentation runbook.

## Repository map

`backend/` FastAPI app, services, scripts, and dependency file  
`frontend/` React/Vite application  
`data/` supplied/interpolated ward/weather data, daily summaries, and SQLite file  
`ml-models/` generated XGBoost artifact  
`docs/` API and integration notes  
`raw/` original project specifications
