from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from positioning_engine import (
    compute_coverage_ratio,
    greedy_positioning,
    simulated_annealing_positioning,
    run_positioning_engine,
    compute_baseline_wait_time,
    compute_system_wait_time,
    REPOSITION_LIMIT,
    ZONES,
)

@pytest.fixture
def small_matrix() -> pd.DataFrame:
    data = {
        "Z1": [0.0, 2.9, 5.5, 5.7, 5.8, 10.8,  8.3, 13.9, 3.6,  3.1],
        "Z2": [2.9, 0.0, 3.3, 3.6, 3.6,  8.7,  6.2, 16.4, 2.2,  3.9],
        "Z3": [5.5, 3.3, 0.0, 2.1, 5.6,  7.2,  4.8, 14.0, 3.4,  4.2],
        "Z4": [5.7, 3.6, 2.1, 0.0, 5.0,  7.5,  5.2, 14.3, 3.7,  4.0],
        "Z5": [5.8, 3.6, 5.6, 5.0, 0.0,  5.4,  6.1, 17.0, 4.0,  5.5],
        "Z6": [10.8, 8.7, 7.2, 7.5, 5.4, 0.0,  5.7, 18.5, 8.3, 10.1],
        "Z7": [8.3, 6.2, 4.8, 5.2, 6.1,  5.7,  0.0, 11.2, 6.0,  7.4],
        "Z8": [13.9,16.4,14.0,14.3,17.0,18.5, 11.2,  0.0,14.5, 13.1],
        "Z9": [3.6, 2.2, 3.4, 3.7, 4.0,  8.3,  6.0, 14.5, 0.0,  3.8],
        "Z10":[3.1, 3.9, 4.2, 4.0, 5.5, 10.1,  7.4, 13.1, 3.8,  0.0],
    }
    df = pd.DataFrame(data, index=ZONES)
    return df

@pytest.fixture
def uniform_fleet() -> pd.DataFrame:
    rows = []
    for i in range(200):
        zone = ZONES[i % 10]
        rows.append({"driver_id": f"DRV_{i:03d}", "current_zone": zone, "status": "idle"})
    return pd.DataFrame(rows)

@pytest.fixture
def clustered_fleet() -> pd.DataFrame:
    rows = [{"driver_id": f"DRV_{i:03d}", "current_zone": "Z1", "status": "idle"}
            for i in range(200)]
    return pd.DataFrame(rows)

@pytest.fixture
def cricket_demand() -> dict:
    d = {z: 0.05 for z in ZONES}
    d["Z10"] = 1.20
    d["Z3"]  = 0.40
    d["Z4"]  = 0.40
    return d

@pytest.fixture
def poya_demand() -> dict:
    d = {z: 0.05 for z in ZONES}
    d["Z8"] = 0.90
    d["Z9"] = 0.70
    return d

class TestCoverageRatio:
    def test_uniform_fleet_reasonable_coverage(self, uniform_fleet, cricket_demand):
        cov = compute_coverage_ratio(uniform_fleet, cricket_demand)

        assert cov["Z10"] <= 1.0, "Coverage cannot exceed 1.0"
        assert all(0.0 <= v <= 1.0 for v in cov.values()), "All coverage values in [0,1]"

    def test_empty_zone_coverage_zero(self, clustered_fleet, cricket_demand):
        cov = compute_coverage_ratio(clustered_fleet, cricket_demand)

        assert cov["Z10"] == 0.0
        assert cov["Z9"]  == 0.0

    def test_full_surplus_capped_at_one(self, uniform_fleet):
        low_demand = {z: 0.0 for z in ZONES}
        cov = compute_coverage_ratio(uniform_fleet, low_demand)
        assert all(c == 1.0 for c in cov.values()), "Oversupplied zones capped at 1.0"

class TestGreedyPositioning:
    def test_assignments_produced_for_cricket(self, clustered_fleet, cricket_demand, small_matrix):
        assignments = greedy_positioning(clustered_fleet, cricket_demand, small_matrix)

        targets = {a["to_zone"] for a in assignments}
        assert "Z10" in targets, "Greedy should reposition to high-demand Z10"

    def test_hard_constraint_never_violated(self, uniform_fleet, cricket_demand, small_matrix):
        assignments = greedy_positioning(uniform_fleet, cricket_demand, small_matrix)
        for a in assignments:
            assert a["travel_time_min"] <= REPOSITION_LIMIT, (
                f"Constraint violated: {a['from_zone']}→{a['to_zone']} "
                f"= {a['travel_time_min']} min > {REPOSITION_LIMIT}"
            )

    def test_no_driver_repositioned_twice(self, clustered_fleet, cricket_demand, small_matrix):
        assignments = greedy_positioning(clustered_fleet, cricket_demand, small_matrix)
        driver_ids = [a["driver_id"] for a in assignments]
        assert len(driver_ids) == len(set(driver_ids)), "Each driver repositioned at most once"

    def test_no_self_assignment(self, uniform_fleet, cricket_demand, small_matrix):
        assignments = greedy_positioning(uniform_fleet, cricket_demand, small_matrix)
        for a in assignments:
            assert a["from_zone"] != a["to_zone"], "Driver should not be assigned to own zone"

    def test_empty_demand_produces_no_assignments(self, uniform_fleet, small_matrix):
        zero_demand = {z: 0.0 for z in ZONES}
        assignments = greedy_positioning(uniform_fleet, zero_demand, small_matrix)
        assert len(assignments) == 0, "No demand → no repositioning needed"

    def test_unreachable_zone_skipped(self, uniform_fleet, small_matrix):

        far_demand = {z: 0.0 for z in ZONES}
        far_demand["Z8"] = 1.50

        assignments = greedy_positioning(uniform_fleet, far_demand, small_matrix)
        assert all(a["to_zone"] != "Z8" for a in assignments), (
            "Z8 is >10 min from all zones — should not receive assignments"
        )

class TestSimulatedAnnealing:
    def test_sa_constraint_never_violated(self, uniform_fleet, cricket_demand, small_matrix):
        assignments = simulated_annealing_positioning(
            uniform_fleet, cricket_demand, small_matrix, max_iterations=200
        )
        for a in assignments:
            assert a["travel_time_min"] <= REPOSITION_LIMIT

    def test_sa_returns_list(self, uniform_fleet, poya_demand, small_matrix):
        result = simulated_annealing_positioning(
            uniform_fleet, poya_demand, small_matrix, max_iterations=100
        )
        assert isinstance(result, list)

    def test_sa_no_driver_twice(self, uniform_fleet, cricket_demand, small_matrix):
        assignments = simulated_annealing_positioning(
            uniform_fleet, cricket_demand, small_matrix, max_iterations=200
        )
        ids = [a["driver_id"] for a in assignments]
        assert len(ids) == len(set(ids))

class TestRunPositioningEngine:
    def test_output_keys(self, uniform_fleet, cricket_demand, small_matrix):
        result = run_positioning_engine(uniform_fleet, cricket_demand, small_matrix)
        required = {"assignments", "coverage_gap", "pre_coverage", "post_coverage",
                    "algorithm", "computation_time_sec", "constraint_violations"}
        assert required.issubset(result.keys())

    def test_selects_greedy_by_default(self, uniform_fleet, cricket_demand, small_matrix):
        result = run_positioning_engine(uniform_fleet, cricket_demand, small_matrix,
                                        fleet_size=200, use_sa=False)
        assert result["algorithm"] == "Greedy"

    def test_selects_sa_when_forced(self, uniform_fleet, cricket_demand, small_matrix):
        result = run_positioning_engine(uniform_fleet, cricket_demand, small_matrix,
                                        use_sa=True)
        assert result["algorithm"] == "SA"

    def test_coverage_improves_after_repositioning(self, clustered_fleet, cricket_demand, small_matrix):
        result = run_positioning_engine(clustered_fleet, cricket_demand, small_matrix)

        pre  = result["pre_coverage"].get("Z10", 0.0)
        post = result["post_coverage"].get("Z10", 0.0)
        assert post >= pre, "Repositioning should not make coverage worse"

    def test_computation_within_time_budget(self, uniform_fleet, cricket_demand, small_matrix):
        result = run_positioning_engine(uniform_fleet, cricket_demand, small_matrix)
        assert result["computation_time_sec"] < 5.0, "Must run in under 5 seconds"

    def test_zero_constraint_violations_greedy(self, uniform_fleet, cricket_demand, small_matrix):
        result = run_positioning_engine(uniform_fleet, cricket_demand, small_matrix,
                                        use_sa=False)
        assert result["constraint_violations"] == 0

class TestWaitTime:
    def test_baseline_wait_uniform_is_low(self, uniform_fleet, small_matrix):
        wt = compute_baseline_wait_time(uniform_fleet, small_matrix)
        assert wt == 0.0, "Uniform fleet has drivers in every zone — wait = 0"

    def test_baseline_wait_clustered_is_high(self, clustered_fleet, small_matrix):
        wt = compute_baseline_wait_time(clustered_fleet, small_matrix)
        assert wt > 0.0, "Clustered fleet (all Z1) means other zones wait"

    def test_system_wait_le_baseline(self, clustered_fleet, cricket_demand, small_matrix):
        result = run_positioning_engine(clustered_fleet, cricket_demand, small_matrix)
        baseline = compute_baseline_wait_time(clustered_fleet, small_matrix)
        system   = compute_system_wait_time(clustered_fleet, result["assignments"], small_matrix)
        assert system <= baseline + 0.01, "Repositioning should not increase wait time"
