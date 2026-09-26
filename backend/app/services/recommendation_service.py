from __future__ import annotations

from typing import Any

from .data_store import alert_details, get_ward_facilities, ward_or_404
from .forecast_service import forecast_service


def get_ward_recommendations(ward_id: str) -> dict[str, Any]:
    ward = ward_or_404(ward_id)
    alert = alert_details(ward_id)
    facilities = get_ward_facilities(ward_id)
    forecast = forecast_service.get_4day_forecast(ward_id, days_ahead=4)

    level = alert["current_alert_level"]
    peak = forecast["peak_forecast"]

    # Municipal action recommendations
    municipal_actions = {
        "Green": [
            {"action": "Routine Monitoring", "priority": "Low", "description": "Maintain standard water delivery schedules and verify cooling point readiness."},
            {"action": "Advisory Circulation", "priority": "Low", "description": "Display general summer hydration tips on civic digital signboards."},
        ],
        "Yellow": [
            {"action": "Inspect Water Points", "priority": "Medium", "description": "Inspect all public drinking water fountains (Pyaaus) and refill municipal storage tanks."},
            {"action": "Outdoor Labor Advisory", "priority": "Medium", "description": "Issue advisory recommending shade breaks for construction workers between 12:30-15:00."},
            {"action": "Cooling Centre Standby", "priority": "Medium", "description": f"Place {ward['ward_name']} community halls on standby for daytime cooling access."},
        ],
        "Orange": [
            {"action": "Deploy Mobile Water Tankers", "priority": "High", "description": f"Position 3 dedicated water tankers near {ward['ward_name']} transit stops and market corridors."},
            {"action": "Activate Public Cooling Shelters", "priority": "High", "description": f"Open {facilities['cooling_centres'][0]['name']} from 10:00 to 18:00 with free chilled drinking water."},
            {"action": "Adjust Outdoor Work Schedules", "priority": "High", "description": "Shift municipal sanitation and road work to 05:30-10:30 and post 17:00."},
            {"action": "Power Grid Load Pre-cooling", "priority": "Medium", "description": "Coordinate with MPPKVVCL power utility to prioritize uninterrupted feeder supply to cooling shelters and hospitals."},
            {"action": "Direct Targeted SMS Alert", "priority": "High", "description": f"Simulate automated alert to registered {ward['ward_name']} residential contacts and labor contractors."},
        ],
        "Red": [
            {"action": "Enforce Outdoor Work Moratorium", "priority": "Critical", "description": "Strictly suspend heavy outdoor construction and manual labor between 11:00 and 16:30."},
            {"action": "Maximized Cooling Center Operations", "priority": "Critical", "description": f"Open all {len(facilities['cooling_centres'])} cooling facilities in {ward['ward_name']} 24/7 with emergency first aid, ORS, and ice packs."},
            {"action": "Continuous Water Distribution", "priority": "Critical", "description": "Deploy emergency continuous water tankers across vulnerable settlements and bus stations."},
            {"action": "Mobile Rapid Response Teams", "priority": "Critical", "description": "Deploy municipal mobile ambulances and trained civil volunteers for street heat-exhaustion patrol."},
            {"action": "Power Grid Emergency Protocol", "priority": "High", "description": "Prevent scheduled load-shedding across all healthcare lines and cooling center circuits."},
        ],
    }[level]

    # Healthcare facility recommendations
    healthcare_actions = {
        "Green": [
            "Maintain baseline inventory of oral rehydration salts and IV saline.",
            "Normal triage operations with routine vigilance.",
        ],
        "Yellow": [
            "Inspect and service emergency room air-conditioning and cooling units.",
            "Verify adequate stock of ORS packets, Ringer Lactate, and normal saline.",
            "Alert duty doctors to watch for early heat cramps and exhaustion in elderly patients.",
        ],
        "Orange": [
            "Designate 10-15 dedicated heat-stroke beds with fans, cold packs, and ice water immersion tubs.",
            "Circulate the National Heat Illness Treatment Protocol to all casualty doctors and nursing staff.",
            "Conduct pre-shift briefing on rapid recognition of classical vs exertional heat stroke.",
            "Ensure emergency ambulances have working air conditioning and cold saline packs.",
        ],
        "Red": [
            "Activate Code Heat / Surge Emergency Response plan across the facility.",
            "Mobilize off-duty nursing staff and reserve beds for impending heatstroke admissions.",
            "Establish rapid cold-water immersion cooling station at the emergency casualty entrance.",
            "Report daily heat illness admissions to the Chief Medical and Health Officer (CMHO) Bhopal.",
        ],
    }[level]

    # Citizen guidance
    citizen_guidance = {
        "Green": {
            "headline": "Normal Conditions — Stay Well Hydrated",
            "summary": "Weather conditions are comfortable. Normal daily work and outdoor exercise can proceed.",
            "key_steps": [
                "Drink 2-3 litres of clean water throughout the day.",
                "Wear light, comfortable cotton clothing.",
                "Ventilate your home during cooler morning and evening hours.",
            ],
            "vulnerable_guidance": "Check that elderly family members are drinking adequate fluids.",
        },
        "Yellow": {
            "headline": "Precautionary Heat — Avoid Midday Sun",
            "summary": "Thermal stress is rising. Take precautions if you are working or traveling outdoors.",
            "key_steps": [
                "Carry a water bottle and umbrella or cap when stepping outside.",
                "Take frequent breaks in shaded or ventilated areas.",
                "Avoid strenuous outdoor activities between 12:00 PM and 3:00 PM.",
                "Consume natural electrolytes like coconut water, nimbu pani, and buttermilk (chaas).",
            ],
            "vulnerable_guidance": "Ensure young children and elders do not stay in poorly ventilated or unshaded rooms.",
        },
        "Orange": {
            "headline": "High Heat Alert — Protect Yourself and Elders",
            "summary": "High thermal stress detected. Sustained exposure can rapidly cause heat exhaustion or cramps.",
            "key_steps": [
                "Stay indoors during the peak heat window (11:30 AM to 4:30 PM).",
                "Drink fluids every 20-30 minutes even if you do not feel thirsty.",
                "If feeling faint, dizzy, or nauseous, immediately move to a cool place and sip cool water.",
                f"Use the nearest free cooling centre: {facilities['cooling_centres'][0]['name']}.",
                "Never leave infants, children, or pets in a closed vehicle.",
            ],
            "vulnerable_guidance": "Monitor elderly relatives twice daily for disorientation, weakness, or dry skin.",
        },
        "Red": {
            "headline": "Severe Heat Emergency — Avoid Outdoor Activity",
            "summary": "Critical thermal conditions. Severe threat of life-threatening heat stroke.",
            "key_steps": [
                "Halt all non-essential outdoor travel and physical labor.",
                "Seek air-conditioned or shaded municipal cooling shelters if home is excessively hot.",
                "Apply cool damp cloths to neck, armpits, and groin if body temperature rises.",
                "Recognize HEAT STROKE signs: high fever, confusion, lack of sweating, unconsciousness.",
                "Call 108 Emergency Ambulance immediately if severe symptoms appear.",
            ],
            "vulnerable_guidance": "High mortality risk for senior citizens and bedridden patients. Move them to coolest available room with active fan/cooler.",
        },
    }[level]

    readiness_checklist = [
        {"id": "chk_cooling", "item": "Facility cooling equipment, air conditioning, and fans serviced", "status": "VERIFIED"},
        {"id": "chk_beds", "item": f"Dedicated heat-stroke observation beds prepared ({facilities['healthcare_facilities'][0]['heat_stroke_beds']} beds)", "status": "READY"},
        {"id": "chk_fluids", "item": "Sufficient ORS packets and IV saline (0.9% NaCl) in casualty store", "status": "STOCKED"},
        {"id": "chk_protocol", "item": "Standard Heat Illness Clinical Protocol circulated to duty doctors", "status": "CIRCULATED"},
        {"id": "chk_staff", "item": "Emergency shift medical staff briefed on rapid triage and cooling", "status": "BRIEFED"},
        {"id": "chk_ambulance", "item": "Ambulance fleet equipped with functional cooling and ice packs", "status": "OPERATIONAL"},
    ]

    return {
        "ward_id": ward_id,
        "ward_name": ward["ward_name"],
        "current_alert_level": level,
        "peak_forecast_summary": peak["summary"],
        "municipal_actions": municipal_actions,
        "healthcare_actions": healthcare_actions,
        "readiness_checklist": readiness_checklist,
        "citizen_guidance": citizen_guidance,
        "cooling_centres": facilities["cooling_centres"],
        "healthcare_facilities": facilities["healthcare_facilities"],
        "emergency_contacts": [
            {"service": "Ambulance / Medical Emergency", "number": "108"},
            {"service": "Bhopal Heat Action Command Helpline", "number": "0755-2740111"},
            {"service": "National Emergency Support System", "number": "112"},
            {"service": "Bhopal Municipal Water Tanker Desk", "number": "1800-233-0101"},
        ],
        "disclaimer": "Taap Kavach recommendations are municipal and public health decision-support guidelines. The system does not directly control physical infrastructure.",
    }
