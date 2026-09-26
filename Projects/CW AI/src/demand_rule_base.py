from __future__ import annotations
from typing import Dict, List

try:
    from .config import ZONE_IDS, DEMAND
except ImportError:
    from config import ZONE_IDS, DEMAND

ZONES: List[str] = ZONE_IDS
DEMAND_CEILING: float = DEMAND["demand_ceiling"]
DEMAND_FLOOR: float = DEMAND["demand_floor"]
WEEKDAYS = DEMAND["weekdays"]
HEAVY = DEMAND["rainfall_heavy_threshold"]
MODERATE = DEMAND["rainfall_moderate_threshold"]

RULES = [

    {
        "id": "R01",
        "description": "Cricket at R. Premadasa (Z10) — post-match dispersal",
        "condition": lambda c: (
            c.get("event_type") == "cricket"
            and c.get("venue_zone") == "Z10"
            and c.get("minutes_to_event_end", 999) <= 20
        ),
        "uplifts": {"Z10": 0.80, "Z3": 0.40, "Z4": 0.40, "Z1": 0.20},
    },
    {
        "id": "R02",
        "description": "Cricket at SSC Ground (Z4) — post-match dispersal",
        "condition": lambda c: (
            c.get("event_type") == "cricket"
            and c.get("venue_zone") == "Z4"
            and c.get("minutes_to_event_end", 999) <= 20
        ),
        "uplifts": {"Z4": 0.80, "Z3": 0.40, "Z1": 0.30},
    },

    {
        "id": "R03",
        "description": "Heavy rainfall (>5mm/hr) — city-wide surge",
        "condition": lambda c: c.get("current_rainfall_mm", 0.0) > HEAVY,
        "uplifts": {z: 0.40 for z in ZONES},
    },
    {
        "id": "R04",
        "description": "Moderate rainfall (2.5-5mm/hr) — moderate uplift",
        "condition": lambda c: MODERATE <= c.get("current_rainfall_mm", 0.0) <= HEAVY,
        "uplifts": {z: 0.20 for z in ZONES},
    },

    {
        "id": "R05",
        "description": "Poya day — Kelaniya Temple (Z8) pilgrimage demand",
        "condition": lambda c: c.get("is_poya_day", False),
        "uplifts": {"Z8": 0.90, "Z1": 0.30},
    },
    {
        "id": "R06",
        "description": "Poya day — Gangaramaya Temple (Z9) pilgrimage demand",
        "condition": lambda c: c.get("is_poya_day", False),
        "uplifts": {"Z9": 0.70, "Z2": 0.30},
    },

    {
        "id": "R07",
        "description": "Morning school run (weekday 07:00-08:30)",
        "condition": lambda c: (
            c.get("day_of_week") in WEEKDAYS
            and (
                c.get("hour") == 7
                or (c.get("hour") == 8 and c.get("minute", 0) <= 30)
            )
        ),
        "uplifts": {"Z6": 0.50, "Z7": 0.45},
    },
    {
        "id": "R08",
        "description": "Afternoon school run (weekday 14:30-16:00)",
        "condition": lambda c: (
            c.get("day_of_week") in WEEKDAYS
            and (
                (c.get("hour") == 14 and c.get("minute", 0) >= 30)
                or c.get("hour") == 15
            )
        ),
        "uplifts": {"Z6": 0.50, "Z7": 0.45},
    },

    {
        "id": "R09",
        "description": "Concert at BMICH (Z3), crowd >1000 — Borella demand",
        "condition": lambda c: (
            c.get("event_type") == "concert"
            and c.get("venue_zone") == "Z3"
            and c.get("crowd_estimate", 0) > 1000
            and c.get("minutes_to_event_end", 999) <= 30
        ),
        "uplifts": {"Z3": 0.70, "Z9": 0.30},
    },

    {
        "id": "R10",
        "description": "Early-morning low-demand period (01:00-05:00) — discount",
        "condition": lambda c: 1 <= c.get("hour", 12) <= 5,
        "uplifts": {z: -0.30 for z in ZONES},
    },
]

def evaluate_demand(context: dict) -> dict:
    scores: Dict[str, float] = {z: 0.0 for z in ZONES}
    fired: List[str] = []

    for rule in RULES:
        try:
            if rule["condition"](context):
                fired.append(rule["id"])
                for zone, uplift in rule["uplifts"].items():
                    scores[zone] += uplift
        except Exception as exc:
            print(f"[RULE ENGINE] {rule['id']} error: {exc}")

    for z in ZONES:
        scores[z] = max(DEMAND_FLOOR, min(scores[z], DEMAND_CEILING))

    return {"demand_uplifts": scores, "fired_rules": fired}

def demand_vector(context: dict) -> List[float]:
    out = evaluate_demand(context)["demand_uplifts"]
    return [out[z] for z in ZONES]

if __name__ == "__main__":
    demo = {
        "current_rainfall_mm": 6.0, "is_poya_day": True,
        "hour": 8, "minute": 15, "day_of_week": 1,
        "event_type": None, "venue_zone": None,
    }
    r = evaluate_demand(demo)
    print("Fired:", r["fired_rules"])
    for z in ZONES:
        print(f"  {z}: {r['demand_uplifts'][z]:+.2f}")
