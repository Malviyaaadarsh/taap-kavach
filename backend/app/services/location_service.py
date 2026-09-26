from __future__ import annotations

from typing import Any
from .data_store import load_wards


STATES = [
    {
        "id": "MP",
        "name": "Madhya Pradesh",
        "code": "MP",
        "status": "ACTIVE",
        "description": "Central state with high summer heatwave exposure in Malwa and Vindhya plateaus.",
    }
]

DISTRICTS = {
    "MP": [
        {
            "id": "bhopal",
            "name": "Bhopal",
            "state_id": "MP",
            "status": "DEMONSTRATED",
            "is_primary": True,
            "description": "Fully demonstrated district prototype with 10 representative wards.",
        },
        {
            "id": "indore",
            "name": "Indore",
            "state_id": "MP",
            "status": "PLACEHOLDER",
            "is_primary": False,
            "description": "Demonstration region — detailed ward data integration pending.",
        },
        {
            "id": "jabalpur",
            "name": "Jabalpur",
            "state_id": "MP",
            "status": "PLACEHOLDER",
            "is_primary": False,
            "description": "Demonstration region — detailed ward data integration pending.",
        },
        {
            "id": "gwalior",
            "name": "Gwalior",
            "state_id": "MP",
            "status": "PLACEHOLDER",
            "is_primary": False,
            "description": "Demonstration region — detailed ward data integration pending.",
        },
        {
            "id": "ujjain",
            "name": "Ujjain",
            "state_id": "MP",
            "status": "PLACEHOLDER",
            "is_primary": False,
            "description": "Demonstration region — detailed ward data integration pending.",
        },
    ]
}

CITIES = {
    "bhopal": [
        {
            "id": "bhopal_bmc",
            "name": "Bhopal Municipal Corporation",
            "short_name": "Bhopal (BMC)",
            "district_id": "bhopal",
            "status": "DEMONSTRATED",
            "is_primary": True,
            "ward_count": 10,
            "latitude": 23.2599,
            "longitude": 77.4126,
            "description": "Administrative authority for Bhopal urban zone. Monitored in prototype.",
        },
        {
            "id": "berasia_mc",
            "name": "Berasia Municipal Council",
            "short_name": "Berasia (MC)",
            "district_id": "bhopal",
            "status": "PLACEHOLDER",
            "is_primary": False,
            "ward_count": 4,
            "latitude": 23.6333,
            "longitude": 77.4333,
            "description": "Northern peri-urban council. Demonstration placeholder.",
        },
    ],
    "indore": [
        {
            "id": "indore_imc",
            "name": "Indore Municipal Corporation",
            "short_name": "Indore (IMC)",
            "district_id": "indore",
            "status": "PLACEHOLDER",
            "is_primary": False,
            "ward_count": 5,
            "latitude": 22.7196,
            "longitude": 75.8577,
            "description": "Demonstration region — detailed ward data integration pending.",
        }
    ],
    "jabalpur": [
        {
            "id": "jabalpur_jmc",
            "name": "Jabalpur Municipal Corporation",
            "short_name": "Jabalpur (JMC)",
            "district_id": "jabalpur",
            "status": "PLACEHOLDER",
            "is_primary": False,
            "ward_count": 4,
            "latitude": 23.1815,
            "longitude": 79.9864,
            "description": "Demonstration region — detailed ward data integration pending.",
        }
    ],
    "gwalior": [
        {
            "id": "gwalior_gmc",
            "name": "Gwalior Municipal Corporation",
            "short_name": "Gwalior (GMC)",
            "district_id": "gwalior",
            "status": "PLACEHOLDER",
            "is_primary": False,
            "ward_count": 4,
            "latitude": 26.2183,
            "longitude": 78.1828,
            "description": "Demonstration region — detailed ward data integration pending.",
        }
    ],
    "ujjain": [
        {
            "id": "ujjain_umc",
            "name": "Ujjain Municipal Corporation",
            "short_name": "Ujjain (UMC)",
            "district_id": "ujjain",
            "status": "PLACEHOLDER",
            "is_primary": False,
            "ward_count": 4,
            "latitude": 23.1765,
            "longitude": 75.7885,
            "description": "Demonstration region — detailed ward data integration pending.",
        }
    ],
}


def get_states() -> list[dict[str, Any]]:
    return STATES


def get_districts(state_id: str = "MP") -> list[dict[str, Any]]:
    return DISTRICTS.get(state_id.upper(), DISTRICTS["MP"])


def get_cities(district_id: str = "bhopal") -> list[dict[str, Any]]:
    norm = district_id.lower().strip()
    return CITIES.get(norm, CITIES["bhopal"])


def get_city_or_default(city_id: str) -> dict[str, Any]:
    norm = city_id.lower().strip()
    for cities_list in CITIES.values():
        for city in cities_list:
            if city["id"].lower() == norm or city["name"].lower() == norm:
                return city
    return CITIES["bhopal"][0]


def get_wards_for_city(city_id: str = "bhopal_bmc") -> list[dict[str, Any]]:
    norm = city_id.lower().strip()
    if norm in ("bhopal_bmc", "bhopal", "bmc", ""):
        return load_wards()
    
    # Return structured demonstration wards for placeholder cities
    city = get_city_or_default(city_id)
    count = city.get("ward_count", 4)
    base_lat = city.get("latitude", 23.25)
    base_lon = city.get("longitude", 77.41)
    
    demo_wards = []
    zones = ["North", "South", "Central", "East", "West"]
    for i in range(1, count + 1):
        ward_code = f"{city['id'].split('_')[0].upper()}_W{str(i).padStart(3, '0') if hasattr(str(i), 'padStart') else str(i).zfill(3)}"
        demo_wards.append({
            "ward_id": ward_code,
            "ward_name": f"{city['short_name']} Sector {i}",
            "zone": zones[(i - 1) % len(zones)],
            "population": 90000 + i * 15000,
            "elderly_percentage": 11 + (i % 5),
            "outdoor_workers_percentage": 20 + (i % 12),
            "latitude": round(base_lat + (i - 2) * 0.02, 4),
            "longitude": round(base_lon + (i - 2) * 0.025, 4),
            "healthcare_facilities": 2 + (i % 3),
            "elevation_m": 500 + i * 5,
            "vegetation_coverage": "Medium",
            "urban_density": "Medium",
            "temp_offset": 0.0,
            "humidity_offset": 0.0,
            "wind_offset": 0.0,
            "is_demonstration": True,
            "note": "Demonstration region — detailed ward data integration pending."
        })
    return demo_wards
