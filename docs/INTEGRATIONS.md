# Integration placeholders

The current application uses `data/wards.json` and `data/weather_history.json` as stable interfaces.

- **IMD:** add an ingestion adapter that maps authoritative forecast observations into the weather schema before thermal calculation.
- **OpenWeatherMap:** add a provider adapter behind the same interface; keep keys in environment variables.
- **Stations:** add timestamped observation ingestion and data-quality checks.
- **PostgreSQL/PostGIS:** migrate ward and facility records first; retain `ward_id` as the API identifier and add geometry columns for official boundaries.
- **Hospitals:** replace simulated readiness values with an approved capacity feed.
- **SMS/WhatsApp:** replace the recorded `SIMULATED` alert object with a reviewed provider adapter and consent-aware recipient service.
