# API Notes

FastAPI publishes the complete OpenAPI contract at `/docs`.

Public endpoints:

- `GET /api/bhopal/wards`
- `GET /api/ward/{ward_id}/weather?days_back=5`
- `GET /api/ward/{ward_id}/thermal-indices?days_back=5`
- `GET /api/ward/{ward_id}/forecast?days_ahead=5`
- `GET /api/ward/{ward_id}/alert-status`
- `GET /api/health`
- `POST /api/chat` with `{ "question": "Why is this ward at risk?", "ward_id": "BPL_W007" }`

Authentication:

- `POST /api/auth/login` with `{ "email": "...", "password": "..." }`
- `POST /api/auth/register` with email, password, role, organization, and optional jurisdiction
- Send `Authorization: Bearer <access_token>` to protected endpoints

Role-protected endpoints:

- `GET /api/admin/municipality-suggestions?ward_id=BPL_W001` requires `local_administration`
- `GET /api/healthcare/hospital-readiness?ward_id=BPL_W001` requires `healthcare_facility`

Validation endpoint:

- `POST /api/thermal/calculate` accepts temperature, humidity, wind speed, pressure, UV, and solar radiation and returns the three indices plus classifications.

Invalid ward IDs return `404`; invalid weather ranges return `422`; missing or wrong-role tokens return `401`/`403`.

The chat response includes `provider: local-rule-engine` and the active data period. The local provider is authoritative for the prototype conversation. Gemini is a future optional explanation provider and must be called server-side only; it must not replace deterministic thermal calculations or alert classification.
