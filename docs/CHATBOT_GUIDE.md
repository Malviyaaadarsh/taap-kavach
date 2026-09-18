# Taap Kavach Assistant Guide

## Current provider

The dashboard assistant uses a deterministic local rule engine. It requires no external API key, works offline once the frontend is running, and receives the selected ward, current alert, latest weather, thermal indices, and five-day forecast as context.

The backend equivalent is `POST /api/chat`:

```json
{
  "question": "Why is Bhel Nagar at risk?",
  "ward_id": "BPL_W007"
}
```

The response identifies the ward, alert level, data period, and `provider: local-rule-engine`.

## Presentation questions

| Question | Expected answer focus |
|---|---|
| What is the current alert for this ward? | Selected ward alert and recommended precautions |
| Why is this ward at risk? | Latest temperature, humidity, WBGT, UTCI, Heat Index, and local characteristics |
| Compare the hottest and coolest wards | Bhel Nagar versus Raisen Road on 18 September 2026 |
| What should outdoor workers do? | Cooler work hours, shade, water breaks, protective clothing, symptoms |
| What is the forecast for the next five days? | First and last forecast levels, UTCI range, prototype confidence disclaimer |
| What do the alert colours mean? | Green, Yellow, Orange, and Red public guidance |
| Explain WBGT and UTCI | Occupational heat stress and perceived thermal stress |
| Where does this data come from? | Supplied MET Norway Bhopal snapshot, 14-18 September 2026, ward interpolation |
| How confident is this forecast? | Prototype confidence, only five-day training window, not operational validation |
| What should a hospital prepare? | Cooling equipment, IV/ORS stock, triage, briefings, surge capacity |
| What is Taap Kavach? | Fourth ward-level layer complementing National, Regional, and District forecasting |

## Future provider contract

The frontend should continue calling one assistant interface even when the provider changes:

```text
question + ward context -> assistant provider -> answer + citations + provider metadata
```

Possible providers:

- `local-rule-engine`: current deterministic and demo-safe provider
- `historical-context-engine`: future provider using five-year summaries and seasonal baselines
- `gemini`: optional future provider, enabled only when a server-side `GEMINI_API_KEY` exists

Never expose a Gemini key in frontend code or browser storage. The backend should redact personal data, cap prompt size, log provider/version, and retain the local fallback when the external provider is unavailable.
