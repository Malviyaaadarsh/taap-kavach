# Mature Time-Series Pipeline Template

This document defines the next data boundary as the supplied five-day snapshot grows into a multi-year series.

## Canonical observation schema

One row represents one observation for one ward and timestamp:

```text
observation_id, ward_id, observed_at_utc, local_date, local_time,
temperature_c, relative_humidity_pct, wind_speed_kmh, pressure_hpa,
uv_index, solar_radiation_wm2, source, source_station_id,
quality_flag, interpolation_method, data_version
```

Thermal outputs should be stored separately and linked by `observation_id`:

```text
observation_id, wbgt_c, utci_c, heat_index_c,
thermal_stress_level, alert_level, engine_version, calculated_at_utc
```

## Five-year aggregation layers

Keep raw observations immutable. Build derived tables or parquet partitions for:

- hourly observations by `ward_id` and month
- daily min/mean/max and afternoon peak metrics
- rolling 3-day and 7-day thermal summaries
- summer-season baselines by ward and day-of-year
- alert duration, exceedance count, and confidence summaries
- model features and forecast verification records

## Recommended training split

Use time-based splits, never random row splitting:

- training: oldest 70 percent of dates
- validation: next 15 percent
- test: newest 15 percent
- hold out entire heat events when evaluating generalisation

Track MAE, RMSE, alert-level precision/recall, false alarms, missed severe alerts, and calibration by ward.

## Ingestion flow

```text
provider adapter -> schema validation -> quality checks -> raw store
-> ward interpolation -> thermal engine -> daily aggregates
-> feature store -> XGBoost retraining -> forecast verification -> API
```

## Data quality rules

- Reject impossible ranges and duplicate observation IDs.
- Preserve source values and record every interpolation or correction.
- Flag missing periods rather than filling silently.
- Store timezone explicitly; normalise model features to UTC while displaying IST.
- Version the ward metadata and thermal-engine formula.

## Gemini integration boundary

A future Gemini provider may summarise verified context, but it must not calculate authoritative alerts. The deterministic thermal engine and alert classifier remain the source of truth. Gemini should receive a compact, redacted context package and return a plain-language explanation with a provider label. If it fails, the local rule engine responds.
