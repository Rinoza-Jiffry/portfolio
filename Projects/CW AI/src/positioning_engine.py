from __future__ import annotations

import math
import random
import time
from typing import Dict, List

import numpy as np
import pandas as pd

try:
    from .config import ZONE_IDS, POSITIONING, DEMAND
except ImportError:
    from config import ZONE_IDS, DEMAND, POSITIONING

ZONES: List[str] = ZONE_IDS
REPOSITION_LIMIT: float = POSITIONING["reposition_limit_min"]
LAMBDA: float           = POSITIONING["lambda_time_penalty"]
BASE_DRIVERS: int       = DEMAND["base_drivers_per_zone"]
SA_TEMP: float          = POSITIONING["sa_initial_temp"]
SA_COOL: float          = POSITIONING["sa_cooling_rate"]
SA_ITERS: int           = POSITIONING["sa_max_iterations"]

def compute_coverage_ratio(
    drivers_df: pd.DataFrame,
    demand_scores: Dict[str, float],
) -> Dict[str, float]:
    idle_counts = (
        drivers_df[drivers_df["status"] == "idle"]["current_zone"]
        .value_counts()
        .to_dict()
    )
    coverage: Dict[str, float] = {}
    for z in ZONES:
        count    = idle_counts.get(z, 0)
        expected = max(1, (1.0 + demand_scores.get(z, 0.0)) * BASE_DRIVERS)
        coverage[z] = min(1.0, count / expected)
    return coverage

def _objective(assignments: List[dict], drivers_df: pd.DataFrame,
               demand_scores: Dict[str, float]) -> float:
    updated = drivers_df.copy()
    for a in assignments:
        updated.loc[updated["driver_id"] == a["driver_id"], "current_zone"] = a["to_zone"]
    cov = compute_coverage_ratio(updated, demand_scores)
    supply_cost = sum(demand_scores.get(z, 0.0) * (1.0 - cov[z]) for z in ZONES)
    time_cost   = LAMBDA * sum(a["travel_time_min"] for a in assignments)
    return supply_cost + time_cost

def greedy_positioning(
    drivers_df: pd.DataFrame,
    demand_scores: Dict[str, float],
    travel_matrix: pd.DataFrame,
) -> List[dict]:
    idle_df       = drivers_df[drivers_df["status"] == "idle"].copy()
    coverage      = compute_coverage_ratio(idle_df, demand_scores)
    assignments:  List[dict] = []
    repositioned: set        = set()

    while True:

        deficit_zones = sorted(
            [(z, demand_scores.get(z, 0.0), coverage.get(z, 0.0))
             for z in ZONES if coverage.get(z, 0.0) < 1.0],
            key=lambda t: t[1] * (1.0 - t[2]),
            reverse=True,
        )
        if not deficit_zones:
            break

        made_assignment = False
        for target_z, _demand, _cov in deficit_zones:
            candidates = []
            for _, drv in idle_df.iterrows():
                did = drv["driver_id"]
                if did in repositioned:
                    continue
                from_z = drv["current_zone"]
                if from_z == target_z:
                    continue
                try:
                    tt = float(travel_matrix.loc[from_z, target_z])
                except KeyError:
                    continue
                if tt <= REPOSITION_LIMIT:
                    candidates.append((did, from_z, tt))

            if not candidates:
                continue

            candidates.sort(key=lambda x: x[2])
            did, from_z, tt = candidates[0]

            assignments.append({
                "driver_id":       did,
                "from_zone":       from_z,
                "to_zone":         target_z,
                "travel_time_min": tt,
            })

            idle_df.loc[idle_df["driver_id"] == did, "current_zone"] = target_z
            repositioned.add(did)

            coverage = compute_coverage_ratio(idle_df, demand_scores)
            made_assignment = True
            break

        if not made_assignment:
            break

    return assignments

def simulated_annealing_positioning(
    drivers_df: pd.DataFrame,
    demand_scores: Dict[str, float],
    travel_matrix: pd.DataFrame,
    max_iterations: int = SA_ITERS,
    initial_temp: float = SA_TEMP,
    cooling_rate: float = SA_COOL,
) -> List[dict]:
    rng = random.Random(42)

    current = greedy_positioning(drivers_df, demand_scores, travel_matrix)
    current_cost = _objective(current, drivers_df, demand_scores)
    best, best_cost = current[:], current_cost

    reachable: Dict[str, List[str]] = {}
    for fz in ZONES:
        reachable[fz] = [
            tz for tz in ZONES
            if tz != fz and float(travel_matrix.loc[fz, tz]) <= REPOSITION_LIMIT
        ]

    temp = initial_temp
    for _ in range(max_iterations):
        if not current:
            break

        neighbour = [dict(a) for a in current]
        idx = rng.randint(0, len(neighbour) - 1)
        a   = neighbour[idx]

        options = reachable.get(a["from_zone"], [])
        if options:
            new_target          = rng.choice(options)
            a["to_zone"]        = new_target
            a["travel_time_min"] = float(travel_matrix.loc[a["from_zone"], new_target])

        nc    = _objective(neighbour, drivers_df, demand_scores)
        delta = nc - current_cost

        if delta < 0 or rng.random() < math.exp(-delta / max(temp, 1e-10)):
            current, current_cost = neighbour, nc
            if current_cost < best_cost:
                best, best_cost = current[:], current_cost

        temp *= cooling_rate

    return best

def run_positioning_engine(
    drivers_df: pd.DataFrame,
    demand_scores: Dict[str, float],
    travel_matrix: pd.DataFrame,
    fleet_size: int | None = None,
    use_sa: bool = False,
) -> dict:
    if fleet_size is None:
        fleet_size = len(drivers_df)

    t0 = time.perf_counter()

    sa_threshold = POSITIONING.get("sa_fleet_threshold", 200)
    if use_sa or fleet_size > sa_threshold:
        assignments = simulated_annealing_positioning(drivers_df, demand_scores, travel_matrix)
        algorithm   = "SA"
    else:
        assignments = greedy_positioning(drivers_df, demand_scores, travel_matrix)
        algorithm   = "Greedy"

    elapsed = time.perf_counter() - t0

    pre_cov = compute_coverage_ratio(
        drivers_df[drivers_df["status"] == "idle"], demand_scores
    )

    updated = drivers_df.copy()
    for a in assignments:
        updated.loc[updated["driver_id"] == a["driver_id"], "current_zone"] = a["to_zone"]

    post_cov = compute_coverage_ratio(updated[updated["status"] == "idle"], demand_scores)
    gap      = {z: max(0.0, 1.0 - post_cov.get(z, 0.0)) for z in ZONES}

    violations = sum(
        1 for a in assignments
        if a["travel_time_min"] > REPOSITION_LIMIT
    )

    return {
        "assignments":           assignments,
        "coverage_gap":          gap,
        "pre_coverage":          pre_cov,
        "post_coverage":         post_cov,
        "algorithm":             algorithm,
        "computation_time_sec":  elapsed,
        "constraint_violations": violations,
    }

def _demand_weighted_wait(
    drivers_df: pd.DataFrame,
    demand_scores: Dict[str, float],
    travel_matrix: pd.DataFrame,
) -> float:
    cov       = compute_coverage_ratio(drivers_df[drivers_df["status"] == "idle"], demand_scores)
    wait_list = []

    idle_counts = (
        drivers_df[drivers_df["status"] == "idle"]["current_zone"]
        .value_counts()
        .to_dict()
    )

    for zone in ZONES:
        deficit = max(0.0, 1.0 - cov.get(zone, 0.0))
        if deficit == 0.0:
            wait_list.append(0.0)
            continue

        row    = travel_matrix[zone].sort_values()
        tt_min = REPOSITION_LIMIT
        for src_zone, tt in row.items():
            if src_zone == zone:
                continue
            src_cov = cov.get(src_zone, 0.0)
            if src_cov >= 1.0 or idle_counts.get(src_zone, 0) > 0:
                tt_min = float(tt)
                break
        wait_list.append(tt_min * deficit)

    return float(np.mean(wait_list)) if wait_list else 0.0

def compute_baseline_wait_time(
    drivers_df: pd.DataFrame,
    travel_matrix: pd.DataFrame,
    demand_scores: Dict[str, float] | None = None,
) -> float:
    if demand_scores is not None:
        return _demand_weighted_wait(drivers_df, demand_scores, travel_matrix)

    idle_zones = set(
        drivers_df[drivers_df["status"] == "idle"]["current_zone"].unique()
    )
    wait_times = []
    for zone in ZONES:
        if zone in idle_zones:
            wait_times.append(0.0)
            continue
        row = travel_matrix[zone].sort_values()
        found = False
        for z_src, tt in row.items():
            if z_src in idle_zones:
                wait_times.append(float(tt))
                found = True
                break
        if not found:
            wait_times.append(float(REPOSITION_LIMIT))
    return float(np.mean(wait_times)) if wait_times else 0.0

def compute_system_wait_time(
    drivers_df: pd.DataFrame,
    assignments: List[dict],
    travel_matrix: pd.DataFrame,
    demand_scores: Dict[str, float] | None = None,
) -> float:
    updated = drivers_df.copy()
    for a in assignments:
        updated.loc[updated["driver_id"] == a["driver_id"], "current_zone"] = a["to_zone"]
    return compute_baseline_wait_time(updated, travel_matrix, demand_scores)

if __name__ == "__main__":

    import pandas as _pd
    _drivers = _pd.DataFrame([
        {"driver_id": f"DRV_{i:03d}", "current_zone": f"Z{(i % 10) + 1}", "status": "idle"}
        for i in range(50)
    ])
    import os as _os
    _matrix = _pd.read_csv(
        _os.path.join(_os.path.dirname(__file__), "..", "data", "processed", "travel_time_matrix.csv"),
        index_col=0
    )
    _demand = {f"Z{i}": 0.8 if i in [10, 4] else 0.1 for i in range(1, 11)}
    result = run_positioning_engine(_drivers, _demand, _matrix)
    print(f"Algorithm : {result['algorithm']}")
    print(f"Assignments: {len(result['assignments'])}")
    print(f"Violations : {result['constraint_violations']}")
    print(f"Time (s)   : {result['computation_time_sec']:.4f}")
