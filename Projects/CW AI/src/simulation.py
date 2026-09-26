from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

try:
    from .config import ZONE_IDS, PATHS, SIM
    from .demand_rule_base import evaluate_demand
    from .positioning_engine import (
        run_positioning_engine,
        compute_baseline_wait_time,
        compute_system_wait_time,
    )
    from .pricing_engine import compute_price_multipliers
except ImportError:
    from config import ZONE_IDS, PATHS, SIM
    from demand_rule_base import evaluate_demand
    from positioning_engine import (
        run_positioning_engine,
        compute_baseline_wait_time,
        compute_system_wait_time,
    )
    from pricing_engine import compute_price_multipliers

log = logging.getLogger(__name__)
ZONES: List[str] = ZONE_IDS

def compute_gini(values: List[float]) -> float:
    arr = np.array(values, dtype=float)
    if arr.sum() == 0:
        return 0.0
    arr   = np.sort(arr)
    n     = len(arr)
    index = np.arange(1, n + 1)
    return float(
        (2.0 * np.dot(index, arr) - (n + 1) * arr.sum()) / (n * arr.sum())
    )

def compute_metrics(
    drivers_df:         pd.DataFrame,
    positioning_result: dict,
    pricing_result:     dict,
    travel_matrix:      pd.DataFrame,
    baseline_wait:      float,
    demand_scores:      dict | None = None,
) -> dict:
    assignments  = positioning_result["assignments"]
    gaps         = positioning_result["coverage_gap"]
    multipliers  = list(pricing_result["multipliers"].values())

    updated = drivers_df.copy()
    for a in assignments:
        updated.loc[updated["driver_id"] == a["driver_id"], "current_zone"] = a["to_zone"]

    idle_counts = (
        updated[updated["status"] == "idle"]["current_zone"]
        .value_counts()
        .reindex(ZONES, fill_value=0)
    )

    n_high_demand = sum(1 for g in gaps.values() if g > 0 or g == 0)
    n_resolved    = sum(1 for g in gaps.values() if g == 0.0)
    surge_prev    = n_resolved / max(1, len(gaps))

    surge_mults = [m for m in multipliers if m > 1.0]
    avg_surge   = float(np.mean(surge_mults)) if surge_mults else 1.0

    gini = compute_gini(idle_counts.tolist())

    n_assignments = max(1, len(assignments))
    violations    = positioning_result["constraint_violations"]
    csr           = 1.0 - (violations / n_assignments)

    comp_time = positioning_result["computation_time_sec"]

    system_wait = compute_system_wait_time(drivers_df, assignments, travel_matrix, demand_scores)
    if baseline_wait > 0:
        wait_reduction = (baseline_wait - system_wait) / baseline_wait
    else:
        wait_reduction = 0.0

    return {
        "surge_prevention_rate":        round(surge_prev,    4),
        "avg_surge_multiplier":         round(avg_surge,     4),
        "gini_coefficient":             round(gini,          4),
        "constraint_satisfaction_rate": round(csr,           4),
        "computation_time_sec":         round(comp_time,     4),
        "wait_time_reduction_pct":      round(wait_reduction, 4),
        "baseline_wait_time_min":       round(baseline_wait, 4),
        "system_wait_time_min":         round(system_wait,   4),
        "n_assignments":                len(assignments),
        "n_constraint_violations":      violations,
    }

def run_scenario(scenario_config: dict, travel_matrix: pd.DataFrame) -> dict:

    ctx: dict = {
        **scenario_config.get("weather", {}),
        **scenario_config.get("time", {}),
        "is_poya_day": scenario_config.get("poya_day", False),
        "timestamp":   scenario_config.get("description", ""),
    }
    if scenario_config.get("event"):
        ctx.update(scenario_config["event"])

    fleet_file = Path(str(PATHS["data_processed"])) / scenario_config["driver_fleet_file"]
    drivers_df = pd.read_csv(fleet_file)

    demand_result = evaluate_demand(ctx)
    log.debug("[SIM] Fired rules: %s", demand_result["fired_rules"])

    positioning_result = run_positioning_engine(
        drivers_df,
        demand_result["demand_uplifts"],
        travel_matrix,
        fleet_size=len(drivers_df),
        use_sa=scenario_config.get("use_sa", False),
    )

    pricing_result = compute_price_multipliers(
        demand_result,
        positioning_result["coverage_gap"],
        ctx,
    )

    baseline_wait = compute_baseline_wait_time(
        drivers_df, travel_matrix, demand_result["demand_uplifts"]
    )
    metrics = compute_metrics(
        drivers_df, positioning_result, pricing_result, travel_matrix, baseline_wait,
        demand_scores=demand_result["demand_uplifts"]
    )

    log.info(
        "[SIM] %s seed=%s | fired=%s | assignments=%d | wait_red=%.1f%%",
        scenario_config["scenario_type"],
        scenario_config["seed"],
        demand_result["fired_rules"],
        len(positioning_result["assignments"]),
        metrics["wait_time_reduction_pct"] * 100,
    )

    return {
        "scenario_type": scenario_config["scenario_type"],
        "seed":          scenario_config["seed"],
        "context":       ctx,
        "demand":        demand_result,
        "positioning":   positioning_result,
        "pricing":       pricing_result,
        "metrics":       metrics,
    }

def run_scenario_baseline(scenario_config: dict, travel_matrix: pd.DataFrame) -> dict:
    ctx: dict = {
        **scenario_config.get("weather", {}),
        **scenario_config.get("time", {}),
        "is_poya_day": scenario_config.get("poya_day", False),
    }
    if scenario_config.get("event"):
        ctx.update(scenario_config["event"])

    fleet_file = Path(str(PATHS["data_processed"])) / scenario_config["driver_fleet_file"]
    drivers_df = pd.read_csv(fleet_file)
    demand_result = evaluate_demand(ctx)

    zero_gap    = {z: 1.0 for z in ZONES}
    no_pricing  = {"multipliers": {z: 1.0 for z in ZONES},
                   "applied_rules": {z: None for z in ZONES}}

    baseline_wait = compute_baseline_wait_time(drivers_df, travel_matrix)

    fake_pos = {
        "assignments":           [],
        "coverage_gap":          zero_gap,
        "pre_coverage":          {},
        "post_coverage":         {},
        "algorithm":             "Baseline",
        "computation_time_sec":  0.0,
        "constraint_violations": 0,
    }

    metrics = compute_metrics(drivers_df, fake_pos, no_pricing, travel_matrix, baseline_wait)

    return {
        "scenario_type": scenario_config["scenario_type"],
        "seed":          scenario_config["seed"],
        "variant":       "baseline",
        "demand":        demand_result,
        "positioning":   fake_pos,
        "pricing":       no_pricing,
        "metrics":       metrics,
    }

if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO)

    matrix = pd.read_csv(PATHS["travel_matrix"], index_col=0)

    scenario_dir = Path(str(PATHS["data_scenarios"])) / "monsoon"
    first = sorted(scenario_dir.glob("*.json"))[0]
    with first.open() as fh:
        cfg = json.load(fh)

    result = run_scenario(cfg, matrix)
    m = result["metrics"]
    print(f"Scenario  : {result['scenario_type']} seed={result['seed']}")
    print(f"Assignments: {m['n_assignments']}")
    print(f"Wait red  : {m['wait_time_reduction_pct']*100:.1f}%")
    print(f"Gini      : {m['gini_coefficient']:.3f}")
    print(f"Surge prev: {m['surge_prevention_rate']*100:.0f}%")
