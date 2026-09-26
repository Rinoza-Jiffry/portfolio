from __future__ import annotations
from typing import Dict, List

try:
    from .config import ZONE_IDS, PRICING, DEMAND
except ImportError:
    from config import ZONE_IDS, PRICING, DEMAND

ZONES: List[str] = ZONE_IDS

HARD_CAP:       float = PRICING["hard_cap"]
FAIR_CAP:       float = PRICING["fair_cap_combined"]
BASE:           float = PRICING["base_multiplier"]
DISCOUNT:       float = PRICING["discount_multiplier"]
MIN_DEMAND:     float = PRICING["min_demand_for_surge"]
PRE_EMP_MULT:   float = PRICING["preemptive_multiplier"]
PRE_EMP_CROWD:  int   = DEMAND["large_event_crowd_threshold"]
PRE_EMP_WINDOW: int   = DEMAND["event_pre_surge_window_min"]

_GRAD = PRICING["graduated_thresholds"]
LOW_GAP:  float = _GRAD["low"]["gap_max"];   LOW_MULT:  float = _GRAD["low"]["multiplier"]
MED_GAP:  float = _GRAD["medium"]["gap_max"]; MED_MULT: float = _GRAD["medium"]["multiplier"]
HIGH_MULT: float = _GRAD["high"]["multiplier"]

def _high_demand(demand_uplifts: Dict[str, float], zone: str) -> bool:
    return demand_uplifts.get(zone, 0.0) >= MIN_DEMAND

PRICING_RULES = [

    {
        "id": "P04",
        "description": "Pre-emptive surge: large event ending ≤20 min, crowd >5 000",
        "condition": lambda ctx, gap, du, z: (
            ctx.get("crowd_estimate", 0) > PRE_EMP_CROWD
            and ctx.get("minutes_to_event_end", 999) <= PRE_EMP_WINDOW
        ),
        "multiplier": PRE_EMP_MULT,
    },

    {
        "id": "P03",
        "description": "High demand, coverage gap >60 % → 1.50×",
        "condition": lambda ctx, gap, du, z: _high_demand(du, z) and gap > MED_GAP,
        "multiplier": HIGH_MULT,
    },

    {
        "id": "P02",
        "description": "High demand, coverage gap 31–60 % → 1.30×",
        "condition": lambda ctx, gap, du, z: _high_demand(du, z) and LOW_GAP < gap <= MED_GAP,
        "multiplier": MED_MULT,
    },

    {
        "id": "P01",
        "description": "High demand, coverage gap 1–30 % → 1.15×",
        "condition": lambda ctx, gap, du, z: _high_demand(du, z) and 0 < gap <= LOW_GAP,
        "multiplier": LOW_MULT,
    },

    {
        "id": "P06",
        "description": "High demand, gap = 0 — repositioning sufficient → 1.00×",
        "condition": lambda ctx, gap, du, z: _high_demand(du, z) and gap == 0.0,
        "multiplier": BASE,
    },

    {
        "id": "P05",
        "description": "Excess supply, low demand → 0.85× discount",
        "condition": lambda ctx, gap, du, z: (
            du.get(z, 0.0) < 0.0 and gap == 0.0
        ),
        "multiplier": DISCOUNT,
    },
]

def _apply_caps(multiplier: float, context: dict) -> float:
    is_poya       = bool(context.get("is_poya_day", False))
    is_heavy_rain = float(context.get("current_rainfall_mm", 0.0)) > 5.0
    if is_poya and is_heavy_rain:
        multiplier = min(multiplier, FAIR_CAP)
    return min(multiplier, HARD_CAP)

def compute_price_multipliers(
    demand_result: dict,
    coverage_gap: Dict[str, float],
    context: dict,
) -> dict:
    demand_uplifts: Dict[str, float] = demand_result.get("demand_uplifts", {})
    multipliers:    Dict[str, float] = {}
    applied_rules:  Dict[str, str | None] = {}

    for zone in ZONES:
        gap  = float(coverage_gap.get(zone, 0.0))
        mult = BASE
        rule_hit = None

        for rule in PRICING_RULES:
            try:
                if rule["condition"](context, gap, demand_uplifts, zone):
                    mult     = rule["multiplier"]
                    rule_hit = rule["id"]
                    break
            except Exception as exc:
                print(f"[PRICING] Rule {rule['id']} error zone {zone}: {exc}")

        mult = _apply_caps(mult, context)
        multipliers[zone]   = round(mult, 2)
        applied_rules[zone] = rule_hit

    return {"multipliers": multipliers, "applied_rules": applied_rules}

if __name__ == "__main__":

    _demand = {
        "demand_uplifts": {f"Z{i}": 0.8 if i in [10, 4] else -0.1 for i in range(1, 11)},
        "fired_rules": ["R01"],
    }
    _gap = {f"Z{i}": 0.5 if i in [10, 4] else 0.0 for i in range(1, 11)}
    _ctx = {"is_poya_day": False, "current_rainfall_mm": 2.0,
            "crowd_estimate": 35000, "minutes_to_event_end": 15}
    result = compute_price_multipliers(_demand, _gap, _ctx)
    for z, m in result["multipliers"].items():
        print(f"  {z}: {m:.2f}×  (rule={result['applied_rules'][z]})")
