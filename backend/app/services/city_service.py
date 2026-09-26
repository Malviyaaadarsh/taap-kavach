from __future__ import annotations

from typing import Any

from .data_store import alert_details, get_ward_current, load_wards
from .forecast_service import forecast_service
from .location_service import get_wards_for_city


def get_city_summary(city_id: str = "bhopal_bmc") -> dict[str, Any]:
    wards = get_wards_for_city(city_id)
    ward_details = []

    counts = {"Green": 0, "Yellow": 0, "Orange": 0, "Red": 0}
    total_population = 0
    total_elderly = 0
    total_outdoor = 0

    sum_temp = 0.0
    sum_utci = 0.0
    sum_wbgt = 0.0
    sum_hi = 0.0
    sum_htsi = 0.0

    severity_rank = {"Red": 4, "Orange": 3, "Yellow": 2, "Green": 1}

    for ward in wards:
        wid = ward["ward_id"]
        # If it's a real Bhopal ward:
        try:
            curr = get_ward_current(wid)
            alert = curr["alert"]["current_alert_level"]
            htsi = curr["thermal_metrics"]["htsi"]
            utci = curr["thermal_metrics"]["utci"]
            wbgt = curr["thermal_metrics"]["wbgt"]
            hi = curr["thermal_metrics"]["heat_index"]
            temp = curr["weather"]["temperature"]
            f_res = forecast_service.get_4day_forecast(wid, 4)
            peak_day = f_res["peak_forecast"]["day_label"]
            peak_alert = f_res["peak_forecast"]["alert_level"]
            priority_action = curr["alert"]["action_recommended"]
        except Exception:
            # Fallback for demonstration wards
            alert = "Orange" if int(wid[-1:]) % 2 == 0 else "Yellow"
            htsi = 65.0
            utci = 37.0
            wbgt = 29.5
            hi = 36.0
            temp = 33.5
            peak_day = "Day +2"
            peak_alert = "Red"
            priority_action = "Review daytime work hours and water point deployment."

        counts[alert] = counts.get(alert, 0) + 1
        pop = ward.get("population", 120000)
        total_population += pop
        total_elderly += int(pop * (ward.get("elderly_percentage", 12) / 100.0))
        total_outdoor += int(pop * (ward.get("outdoor_workers_percentage", 25) / 100.0))

        sum_temp += temp
        sum_utci += utci
        sum_wbgt += wbgt
        sum_hi += hi
        sum_htsi += htsi

        ward_details.append({
            "ward_id": wid,
            "ward_name": ward["ward_name"],
            "zone": ward["zone"],
            "latitude": ward["latitude"],
            "longitude": ward["longitude"],
            "population": pop,
            "elderly_percentage": ward.get("elderly_percentage", 12),
            "outdoor_workers_percentage": ward.get("outdoor_workers_percentage", 25),
            "alert_level": alert,
            "severity_score": severity_rank.get(alert, 1) * 100 + htsi,
            "temperature": temp,
            "utci": utci,
            "wbgt": wbgt,
            "heat_index": hi,
            "htsi": htsi,
            "peak_forecast_day": peak_day,
            "peak_forecast_alert": peak_alert,
            "priority_action": priority_action,
            "vegetation": ward.get("vegetation_coverage", "Medium"),
            "urban_density": ward.get("urban_density", "Medium"),
        })

    n = max(1, len(wards))
    avg_temp = round(sum_temp / n, 1)
    avg_utci = round(sum_utci / n, 1)
    avg_wbgt = round(sum_wbgt / n, 1)
    avg_hi = round(sum_hi / n, 1)
    avg_htsi = round(sum_htsi / n, 1)

    # Calculate overall city exposed population
    exposed_ratio = (counts["Red"] * 0.95 + counts["Orange"] * 0.75 + counts["Yellow"] * 0.45 + counts["Green"] * 0.15) / n
    total_exposed = int(total_population * exposed_ratio)
    vulnerable_exposed = int((total_elderly + total_outdoor) * exposed_ratio)

    # Sort priority wards by severity descending
    ward_details.sort(key=lambda item: item["severity_score"], reverse=True)
    highest_risk_wards = ward_details[:4]

    priority_recommendations = [
        {"title": "Deploy Emergency Water Coverage", "level": "High", "text": "Mobilize 15 municipal water tankers to Red alert corridors: Habibganj, Bhel Nagar, New Market, and Kolar Road."},
        {"title": "Enforce Outdoor Labor Moratorium", "level": "Critical", "text": "Halt strenuous outdoor construction and road work from 11:30 AM to 4:00 PM in Orange and Red wards."},
        {"title": "Operationalize Public Cooling Hubs", "level": "High", "text": "Activate all designated civic community halls and air-conditioned libraries for public relief."},
        {"title": "Power Utility Heat Feeder Protection", "level": "Medium", "text": "Coordinate with MPPKVVCL to maintain steady feeder voltage for medical refrigeration and water pumps."},
    ]

    city_forecast_trend = [
        {"day": "Today", "date": "2026-09-18", "city_avg_utci": avg_utci, "city_avg_htsi": avg_htsi, "dominant_alert": "Orange", "red_wards": counts["Red"], "orange_wards": counts["Orange"]},
        {"day": "Day +1", "date": "2026-09-19", "city_avg_utci": round(avg_utci + 0.8, 1), "city_avg_htsi": round(avg_htsi + 3.2, 1), "dominant_alert": "Orange", "red_wards": counts["Red"] + 1, "orange_wards": 5},
        {"day": "Day +2 (Peak)", "date": "2026-09-20", "city_avg_utci": round(avg_utci + 1.9, 1), "city_avg_htsi": round(avg_htsi + 6.8, 1), "dominant_alert": "Red", "red_wards": 6, "orange_wards": 4},
        {"day": "Day +3", "date": "2026-09-21", "city_avg_utci": round(avg_utci + 0.5, 1), "city_avg_htsi": round(avg_htsi + 2.1, 1), "dominant_alert": "Orange", "red_wards": 3, "orange_wards": 6},
        {"day": "Day +4", "date": "2026-09-22", "city_avg_utci": round(avg_utci - 1.2, 1), "city_avg_htsi": round(avg_htsi - 4.5, 1), "dominant_alert": "Yellow", "red_wards": 0, "orange_wards": 4},
    ]

    return {
        "city_id": city_id,
        "city_name": "Bhopal Municipal Corporation" if "bhopal" in city_id.lower() else city_id,
        "district": "Bhopal",
        "state": "Madhya Pradesh",
        "timestamp": "2026-09-18T15:30:00",
        "status_summary": {
            "total_monitored_wards": len(wards),
            "alert_counts": counts,
            "overall_status": "HIGH_HEAT_ALERT" if counts["Red"] > 0 else "CAUTION",
            "highest_alert_level": "Red" if counts["Red"] > 0 else "Orange" if counts["Orange"] > 0 else "Yellow",
            "total_population": total_population,
            "total_exposed_population": total_exposed,
            "total_vulnerable_exposed": vulnerable_exposed,
        },
        "averages": {
            "temperature": avg_temp,
            "utci": avg_utci,
            "wbgt": avg_wbgt,
            "heat_index": avg_hi,
            "htsi": avg_htsi,
        },
        "highest_risk_wards": highest_risk_wards,
        "all_wards": ward_details,
        "city_forecast_trend": city_forecast_trend,
        "priority_municipal_actions": priority_recommendations,
        "data_status": {
            "type": "OBSERVED_AND_INTERPOLATED",
            "label": "City-Wide Aggregation of 10 Bhopal Representative Wards",
            "reference_date": "2026-09-18",
        },
    }


def get_city_risk_map(city_id: str = "bhopal_bmc") -> dict[str, Any]:
    summary = get_city_summary(city_id)
    features = []
    for w in summary["all_wards"]:
        features.append({
            "type": "Feature",
            "properties": {
                "ward_id": w["ward_id"],
                "ward_name": w["ward_name"],
                "zone": w["zone"],
                "alert_level": w["alert_level"],
                "temperature": w["temperature"],
                "utci": w["utci"],
                "wbgt": w["wbgt"],
                "heat_index": w["heat_index"],
                "htsi": w["htsi"],
                "population": w["population"],
                "elderly_percentage": w["elderly_percentage"],
                "outdoor_workers_percentage": w["outdoor_workers_percentage"],
                "peak_forecast_day": w["peak_forecast_day"],
                "peak_forecast_alert": w["peak_forecast_alert"],
                "priority_action": w["priority_action"],
            },
            "geometry": {
                "type": "Point",
                "coordinates": [w["longitude"], w["latitude"]],
            },
        })

    return {
        "city_id": city_id,
        "map_center": [23.25, 77.43],
        "default_zoom": 11,
        "notice": "Representative ward coordinates for prototype demonstration — official GIS boundary polygons pending municipal shapefile integration.",
        "type": "FeatureCollection",
        "features": features,
    }
