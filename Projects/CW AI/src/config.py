
from __future__ import annotations
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent

PATHS = {
    "data_raw":           PROJECT_ROOT / "data" / "raw",
    "data_processed":     PROJECT_ROOT / "data" / "processed",
    "data_scenarios":     PROJECT_ROOT / "data" / "scenarios",
    "colombo_osm":        PROJECT_ROOT / "data" / "raw" / "colombo_osm",
    "weather_kaggle":     PROJECT_ROOT / "data" / "raw" / "weather_kaggle",
    "events_scraped":     PROJECT_ROOT / "data" / "raw" / "events_scraped",
    "outputs_figures":    PROJECT_ROOT / "outputs" / "figures",
    "outputs_maps":       PROJECT_ROOT / "outputs" / "maps",
    "outputs_reports":    PROJECT_ROOT / "outputs" / "reports",
    "logs":               PROJECT_ROOT / "logs",
    "cache":              PROJECT_ROOT / ".cache",
    "travel_matrix":      PROJECT_ROOT / "data" / "processed" / "travel_time_matrix.csv",
    "zone_geojson":       PROJECT_ROOT / "data" / "processed" / "zone_definitions.geojson",
    "poya_calendar":      PROJECT_ROOT / "data" / "processed" / "poya_calendar.csv",
    "cricket_fixtures":   PROJECT_ROOT / "data" / "processed" / "cricket_fixtures.csv",
    "weather_clean":      PROJECT_ROOT / "data" / "processed" / "historical_weather_clean.csv",
    "eval_results":       PROJECT_ROOT / "data" / "processed" / "evaluation_results.csv",
    "fallback_events":    PROJECT_ROOT / "data" / "raw" / "events_scraped" / "fallback_events.json",
    "osm_graph":          PROJECT_ROOT / "data" / "raw" / "colombo_osm" / "colombo_drive.graphml",
}

@dataclass(frozen=True)
class Zone:
    id: str
    name: str
    centroid_lat: float
    centroid_lon: float
    key_venue: str
    colour: str

ZONES: List[Zone] = [
    Zone("Z1",  "Fort / Pettah",        6.9344, 79.8428, "Fort Railway Station",         "#E63946"),
    Zone("Z2",  "Kollupitiya",           6.9147, 79.8497, "Majestic City",                "#457B9D"),
    Zone("Z3",  "Borella",               6.9101, 79.8673, "National Hospital / BMICH",    "#2A9D8F"),
    Zone("Z4",  "Maitland Crescent",     6.9065, 79.8614, "SSC Cricket Ground",           "#E9C46A"),
    Zone("Z5",  "Bambalapitiya",         6.8942, 79.8545, "Regal Cinema area",            "#F4A261"),
    Zone("Z6",  "Nugegoda",              6.8683, 79.8880, "Nugegoda Junction",            "#E76F51"),
    Zone("Z7",  "Rajagiriya",            6.9097, 79.8967, "Rajagiriya Interchange",       "#264653"),
    Zone("Z8",  "Kelaniya",              6.9557, 79.9218, "Kelaniya Raja Maha Viharaya",  "#6A4C93"),
    Zone("Z9",  "Gangaramaya",           6.9153, 79.8564, "Gangaramaya Temple",           "#1982C4"),
    Zone("Z10", "Maradana / Premadasa",  6.9271, 79.8609, "R. Premadasa Stadium",         "#8AC926"),
]

ZONE_BY_ID: Dict[str, Zone]   = {z.id: z for z in ZONES}
ZONE_IDS:   List[str]         = [z.id for z in ZONES]
ZONE_NAMES: Dict[str, str]    = {z.id: z.name for z in ZONES}

ZONE_CENTROIDS: Dict[str, Tuple[float, float]] = {
    z.id: (z.centroid_lat, z.centroid_lon) for z in ZONES
}

VENUE_TO_ZONE: Dict[str, str] = {

    "r. premadasa":             "Z10",
    "premadasa":                "Z10",
    "ssc ground":               "Z4",
    "sinhalese sports club":    "Z4",
    "maitland crescent":        "Z4",
    "p. sara oval":             "Z3",
    "paikiasothy saravanamuttu":"Z3",

    "bmich":                    "Z3",
    "bandaranaike memorial":    "Z3",
    "nelum pokuna":             "Z9",
    "slecc":                    "Z2",
    "sri lanka exhibition":     "Z2",

    "kelaniya":                 "Z8",
    "gangaramaya":              "Z9",

    "fort":                     "Z1",
    "pettah":                   "Z1",
    "kollupitiya":              "Z2",
    "colpetty":                 "Z2",
    "borella":                  "Z3",
    "bambalapitiya":            "Z5",
    "nugegoda":                 "Z6",
    "rajagiriya":               "Z7",
    "maradana":                 "Z10",
}

GEO = {
    "place_query":    "Colombo, Western Province, Sri Lanka",
    "network_type":   "drive",
    "crs_metric":     "EPSG:32644",
    "crs_geographic": "EPSG:4326",
    "colombo_bbox": {
        "north": 7.000,
        "south": 6.840,
        "east":  79.970,
        "west":  79.820,
    },
}

SIM = {
    "fleet_size":               200,
    "cycle_interval_min":       15,
    "n_seeds":                  10,
    "scenario_types":           ["monsoon", "cricket", "poya"],
    "total_scenarios":          30,
}

DEMAND = {
    "demand_ceiling":           1.50,
    "demand_floor":            -0.50,
    "base_drivers_per_zone":    5,
    "monsoon_months":           [5, 6, 7, 8, 9],
    "school_run_morning": {
        "start_hour": 7, "start_min": 0,
        "end_hour":   8, "end_min":  30,
    },
    "school_run_afternoon": {
        "start_hour": 14, "start_min": 30,
        "end_hour":   16, "end_min":   0,
    },
    "weekdays":                 [0, 1, 2, 3, 4],
    "rainfall_heavy_threshold":  5.0,
    "rainfall_moderate_threshold": 2.5,
    "event_pre_surge_window_min": 20,
    "large_event_crowd_threshold": 5000,
}

POSITIONING = {
    "reposition_limit_min":     10.0,
    "lambda_time_penalty":       0.1,
    "sa_initial_temp":         100.0,
    "sa_cooling_rate":           0.95,
    "sa_max_iterations":        1000,
    "sa_fleet_threshold":        200,
    "time_budget_sec":            5.0,
}

PRICING = {
    "base_multiplier":          1.00,
    "hard_cap":                 2.00,
    "fair_cap_combined":        1.80,
    "discount_multiplier":      0.85,
    "graduated_thresholds": {
        "low":    {"gap_max": 0.30, "multiplier": 1.15},
        "medium": {"gap_max": 0.60, "multiplier": 1.30},
        "high":   {"gap_max": 1.00, "multiplier": 1.50},
    },
    "preemptive_multiplier":    1.30,
    "min_demand_for_surge":     0.40,
}

METRICS_TARGETS = {
    "wait_time_reduction_pct":  0.25,
    "surge_prevention_rate":    0.60,
    "avg_surge_multiplier_max": 1.35,
    "gini_target":              0.20,
    "constraint_satisfaction":  1.00,
    "computation_time_max_sec": 5.00,
    "geocoding_precision":      0.80,
}

APIS = {
    "openmeteo_base":       "https://api.open-meteo.com/v1/forecast",
    "nominatim_base":       "https://nominatim.openstreetmap.org/search",
    "poya_calendar":        "https://srilanka-holidays.vercel.app/api/holidays",
    "lankaevents_upcoming": "https://www.lankaevents.lk/upcoming",
    "eventbrite_colombo":   "https://www.eventbrite.com/d/lk--colombo/",
    "colombo_lat":          6.9271,
    "colombo_lon":          79.8612,
    "timezone":             "Asia/Colombo",
    "cache_ttl_sec":        900,
    "request_timeout_sec":  10,
    "max_retries":          3,
    "backoff_factor":       0.2,
}

FLEET_DISTRIBUTIONS: Dict[str, List[float]] = {
    "monsoon": [0.25, 0.20, 0.15, 0.10, 0.10, 0.05, 0.05, 0.03, 0.04, 0.03],
    "cricket": [0.10, 0.10, 0.10, 0.10, 0.10, 0.10, 0.10, 0.10, 0.10, 0.10],
    "poya":    [0.15, 0.15, 0.12, 0.12, 0.12, 0.10, 0.10, 0.02, 0.02, 0.10],
}

LOGGING = {
    "level":        "INFO",
    "format":       "%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s",
    "date_format":  "%Y-%m-%d %H:%M:%S",
    "log_file":     PROJECT_ROOT / "logs" / "system.log",
    "max_bytes":    10 * 1024 * 1024,
    "backup_count": 3,
}

def validate_config() -> bool:
    errors: List[str] = []

    if len(ZONES) != 10:
        errors.append(f"Expected 10 zones, got {len(ZONES)}")

    for scenario, weights in FLEET_DISTRIBUTIONS.items():
        total = sum(weights)
        if abs(total - 1.0) > 1e-6:
            errors.append(f"Fleet distribution '{scenario}' sums to {total:.4f}, expected 1.0")
        if len(weights) != len(ZONES):
            errors.append(f"Fleet distribution '{scenario}' has {len(weights)} weights, expected {len(ZONES)}")

    if PRICING["hard_cap"] < PRICING["fair_cap_combined"]:
        errors.append("hard_cap must be >= fair_cap_combined")

    if not (0 < METRICS_TARGETS["surge_prevention_rate"] <= 1):
        errors.append("surge_prevention_rate target must be in (0, 1]")

    if errors:
        for e in errors:
            print(f"[CONFIG ERROR] {e}")
        return False

    print(f"[CONFIG] Validated: {len(ZONES)} zones, {SIM['fleet_size']} drivers, "
          f"{SIM['total_scenarios']} scenarios")
    return True

if __name__ == "__main__":
    validate_config()
    print("\nZone Summary:")
    print(f"{'ID':<5} {'Name':<25} {'Centroid':<25} {'Key Venue'}")
    print("-" * 80)
    for z in ZONES:
        print(f"{z.id:<5} {z.name:<25} ({z.centroid_lat:.4f}, {z.centroid_lon:.4f})  {z.key_venue}")
