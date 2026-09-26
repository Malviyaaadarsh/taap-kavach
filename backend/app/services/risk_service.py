from __future__ import annotations

from typing import Any

from .data_store import alert_details, get_ward_current, get_ward_facilities, ward_or_404
from .forecast_service import forecast_service


def calculate_ward_risk_and_impact(ward_id: str) -> dict[str, Any]:
    ward = ward_or_404(ward_id)
    current = get_ward_current(ward_id)
    facilities = get_ward_facilities(ward_id)
    forecast = forecast_service.get_4day_forecast(ward_id, days_ahead=4)

    pop = ward["population"]
    elderly_pct = ward["elderly_percentage"]
    outdoor_pct = ward["outdoor_workers_percentage"]
    children_pct = round(pop * 0.14)  # ~14% children under 10

    elderly_count = int(pop * (elderly_pct / 100.0))
    outdoor_count = int(pop * (outdoor_pct / 100.0))
    vulnerable_total = elderly_count + children_pct

    alert_level = current["alert"]["current_alert_level"]
    htsi = current["thermal_metrics"]["htsi"]
    peak_forecast = forecast["peak_forecast"]

    # Exposure ratios based on current alert level
    exposure_multiplier = {
        "Green": 0.20,
        "Yellow": 0.45,
        "Orange": 0.75,
        "Red": 0.95,
    }.get(alert_level, 0.50)

    population_exposed = int(pop * exposure_multiplier)
    vulnerable_exposed = int(vulnerable_total * min(1.0, exposure_multiplier * 1.15))
    outdoor_exposed = int(outdoor_count * min(1.0, exposure_multiplier * 1.25))

    # Cooling demand estimate (seats needed vs seats available)
    cooling_capacity = sum(c["capacity"] for c in facilities["cooling_centres"])
    cooling_demand_index = round(min(100.0, (outdoor_exposed * 0.12) / max(1, cooling_capacity) * 50), 1)

    # Water demand planning estimate (litres per day for public kiosks, misting, hydration)
    water_litres_per_day = int(population_exposed * (4.5 if alert_level in ("Orange", "Red") else 2.5))

    # Healthcare readiness assessment
    total_beds = sum(h["total_beds"] for h in facilities["healthcare_facilities"])
    heat_beds = sum(h["heat_stroke_beds"] for h in facilities["healthcare_facilities"])
    projected_heat_cases = int(vulnerable_exposed * (0.003 if alert_level == "Red" else 0.0012 if alert_level == "Orange" else 0.0004))
    bed_readiness_pct = min(100, int((heat_beds / max(1, projected_heat_cases)) * 100)) if projected_heat_cases > 0 else 95

    # Health Impact Risk: Prototype Planning Score (0-100)
    # Combines thermal stress (40%), exposure duration (25%), vulnerable proportion (20%), health capacity (15%)
    consecutive_hot_days = sum(1 for f in forecast["forecast"] if f["alert_level"] in ("Orange", "Red")) + (1 if alert_level in ("Orange", "Red") else 0)
    duration_score = min(100.0, consecutive_hot_days * 20.0)
    vulnerability_score = min(100.0, ((elderly_pct + outdoor_pct) / 50.0) * 100.0)
    capacity_deficit = max(0.0, 100.0 - bed_readiness_pct)

    health_impact_score = round(
        0.40 * htsi + 0.25 * duration_score + 0.20 * vulnerability_score + 0.15 * capacity_deficit,
        1,
    )

    if health_impact_score < 40:
        health_impact_level = "Low"
    elif health_impact_score < 60:
        health_impact_level = "Moderate"
    elif health_impact_score < 78:
        health_impact_level = "High"
    else:
        health_impact_level = "Severe"

    health_impact_drivers = []
    if htsi >= 60:
        health_impact_drivers.append(f"Elevated thermal stress index (HTSI: {htsi}/100)")
    if consecutive_hot_days >= 3:
        health_impact_drivers.append(f"Prolonged heat duration ({consecutive_hot_days} consecutive days at Orange/Red)")
    if outdoor_pct >= 25:
        health_impact_drivers.append(f"High outdoor worker concentration ({outdoor_pct}% of ward population)")
    if elderly_pct >= 13:
        health_impact_drivers.append(f"High elderly vulnerability density ({elderly_pct}% aged 60+)")
    if capacity_deficit > 20:
        health_impact_drivers.append("Projected surge exceeds local dedicated heat-bed buffer")

    return {
        "ward_id": ward_id,
        "ward_name": ward["ward_name"],
        "zone": ward["zone"],
        "alert_level": alert_level,
        "current_htsi": htsi,
        "demographics": {
            "total_population": pop,
            "elderly_population": elderly_count,
            "elderly_percentage": elderly_pct,
            "outdoor_worker_population": outdoor_count,
            "outdoor_worker_percentage": outdoor_pct,
            "children_population_estimate": children_pct,
            "total_vulnerable_population": vulnerable_total,
        },
        "planning_estimates": {
            "population_exposed": population_exposed,
            "vulnerable_population_exposed": vulnerable_exposed,
            "outdoor_worker_exposure": outdoor_exposed,
            "cooling_centres_capacity": cooling_capacity,
            "cooling_demand_index": cooling_demand_index,
            "estimated_water_requirement_litres_day": water_litres_per_day,
            "projected_heat_illness_patient_surge": projected_heat_cases,
            "available_heat_beds": heat_beds,
            "bed_readiness_percentage": bed_readiness_pct,
        },
        "health_impact_risk": {
            "label": "Health Impact Risk — Prototype Planning Estimate",
            "score": health_impact_score,
            "level": health_impact_level,
            "disclaimer": "Prototype planning estimate — not a clinical mortality prediction or medical diagnosis.",
            "consecutive_elevated_days": consecutive_hot_days,
            "peak_forecast_day": peak_forecast["day_label"],
            "peak_forecast_alert": peak_forecast["alert_level"],
            "key_drivers": health_impact_drivers,
        },
        "facilities": facilities,
        "data_status": {
            "type": "DERIVED_PLANNING_MODEL",
            "label": "Demographic & Physiological Impact Planning Matrix",
            "basis": "Bhopal Ward Demographic Census + Met Norway Thermal Indices",
        },
    }
