from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from pricing_engine import compute_price_multipliers, ZONES, HARD_CAP, FAIR_CAP

def _demand(uplifts: dict) -> dict:
    d = {z: 0.0 for z in ZONES}
    d.update(uplifts)
    return {"demand_uplifts": d, "fired_rules": []}

def _gap(gaps: dict) -> dict:
    g = {z: 0.0 for z in ZONES}
    g.update(gaps)
    return g

def _ctx(**kwargs) -> dict:
    base = {"is_poya_day": False, "current_rainfall_mm": 0.0,
            "crowd_estimate": 0, "minutes_to_event_end": 999}
    base.update(kwargs)
    return base

class TestPricingRules:

    def test_P01_fires_small_gap(self):
        result = compute_price_multipliers(
            _demand({"Z10": 0.8}),
            _gap({"Z10": 0.20}),
            _ctx()
        )
        assert result["multipliers"]["Z10"] == 1.15
        assert result["applied_rules"]["Z10"] == "P01"

    def test_P02_fires_medium_gap(self):
        result = compute_price_multipliers(
            _demand({"Z10": 0.8}),
            _gap({"Z10": 0.45}),
            _ctx()
        )
        assert result["multipliers"]["Z10"] == 1.30
        assert result["applied_rules"]["Z10"] == "P02"

    def test_P03_fires_large_gap(self):
        result = compute_price_multipliers(
            _demand({"Z10": 0.8}),
            _gap({"Z10": 0.80}),
            _ctx()
        )
        assert result["multipliers"]["Z10"] == 1.50
        assert result["applied_rules"]["Z10"] == "P03"

    def test_P04_preemptive_large_event(self):
        result = compute_price_multipliers(
            _demand({"Z10": 0.0}),
            _gap({"Z10": 0.10}),
            _ctx(crowd_estimate=35000, minutes_to_event_end=10)
        )
        assert result["multipliers"]["Z10"] == 1.30
        assert result["applied_rules"]["Z10"] == "P04"

    def test_P04_does_not_fire_small_crowd(self):
        result = compute_price_multipliers(
            _demand({"Z10": 0.0}),
            _gap({"Z10": 0.0}),
            _ctx(crowd_estimate=1000, minutes_to_event_end=10)
        )

        assert result["applied_rules"]["Z10"] != "P04"

    def test_P04_does_not_fire_event_far_away(self):
        result = compute_price_multipliers(
            _demand({"Z10": 0.0}),
            _gap({"Z10": 0.0}),
            _ctx(crowd_estimate=40000, minutes_to_event_end=45)
        )
        assert result["applied_rules"]["Z10"] != "P04"

    def test_P05_discount_excess_supply(self):
        result = compute_price_multipliers(
            _demand({"Z1": -0.30}),
            _gap({"Z1": 0.0}),
            _ctx()
        )
        assert result["multipliers"]["Z1"] == 0.85
        assert result["applied_rules"]["Z1"] == "P05"

    def test_P06_no_surge_repositioning_resolved(self):
        result = compute_price_multipliers(
            _demand({"Z10": 0.8}),
            _gap({"Z10": 0.0}),
            _ctx()
        )
        assert result["multipliers"]["Z10"] == 1.0
        assert result["applied_rules"]["Z10"] == "P06"

    def test_base_multiplier_when_no_rule_matches(self):
        result = compute_price_multipliers(
            _demand({"Z6": 0.10}),
            _gap({"Z6": 0.05}),
            _ctx()
        )
        assert result["multipliers"]["Z6"] == 1.0

class TestPricingCaps:
    def test_hard_cap_never_exceeded(self):
        result = compute_price_multipliers(
            _demand({z: 1.50 for z in ZONES}),
            _gap({z: 1.0  for z in ZONES}),
            _ctx(crowd_estimate=50000, minutes_to_event_end=1)
        )
        for z, m in result["multipliers"].items():
            assert m <= HARD_CAP, f"Zone {z} multiplier {m} exceeds hard cap {HARD_CAP}"

    def test_fair_cap_poya_heavy_rain(self):
        result = compute_price_multipliers(
            _demand({"Z8": 0.90, "Z9": 0.70}),
            _gap({"Z8": 0.80, "Z9": 0.80}),
            _ctx(is_poya_day=True, current_rainfall_mm=7.0)
        )

        assert result["multipliers"]["Z8"] <= FAIR_CAP
        assert result["multipliers"]["Z9"] <= FAIR_CAP

    def test_fair_cap_scenario_seed6(self):

        ctx = _ctx(is_poya_day=True, current_rainfall_mm=5.5)
        result = compute_price_multipliers(
            _demand({"Z8": 1.2, "Z9": 0.90}),
            _gap({"Z8": 0.9, "Z9": 0.9}),
            ctx
        )
        for z in ["Z8", "Z9"]:
            assert result["multipliers"][z] <= FAIR_CAP, (
                f"{z}: {result['multipliers'][z]} > fair cap {FAIR_CAP}"
            )

    def test_fair_cap_not_applied_without_both_conditions(self):

        r1 = compute_price_multipliers(
            _demand({"Z8": 0.8}),
            _gap({"Z8": 0.8}),
            _ctx(is_poya_day=False, current_rainfall_mm=7.0)
        )

        assert r1["multipliers"]["Z8"] == 1.50

        r2 = compute_price_multipliers(
            _demand({"Z8": 0.8}),
            _gap({"Z8": 0.8}),
            _ctx(is_poya_day=True, current_rainfall_mm=1.0)
        )
        assert r2["multipliers"]["Z8"] == 1.50

class TestPricingIntegration:
    def test_all_zones_have_multiplier(self):
        result = compute_price_multipliers(
            _demand({}), _gap({}), _ctx()
        )
        assert set(result["multipliers"].keys()) == set(ZONES)
        assert set(result["applied_rules"].keys()) == set(ZONES)

    def test_cricket_post_match_context(self):
        result = compute_price_multipliers(
            _demand({"Z10": 1.2, "Z3": 0.4, "Z4": 0.4}),
            _gap({"Z10": 0.70, "Z3": 0.30, "Z4": 0.30}),
            _ctx(crowd_estimate=35000, minutes_to_event_end=15)
        )

        for z in ["Z10", "Z3", "Z4"]:
            assert result["multipliers"][z] == 1.30
            assert result["applied_rules"][z] == "P04"

    def test_monsoon_heavy_rain_no_event(self):
        result = compute_price_multipliers(
            _demand({z: 0.40 for z in ZONES}),
            _gap({z: 0.70 for z in ZONES}),
            _ctx(current_rainfall_mm=8.0)
        )
        for z in ZONES:
            assert result["multipliers"][z] == 1.50

    def test_off_peak_discount_applies(self):
        result = compute_price_multipliers(
            _demand({z: -0.30 for z in ZONES}),
            _gap({z: 0.0 for z in ZONES}),
            _ctx()
        )
        for z in ZONES:
            assert result["multipliers"][z] == 0.85
            assert result["applied_rules"][z] == "P05"

    def test_multipliers_are_rounded_to_2dp(self):
        result = compute_price_multipliers(
            _demand({"Z1": 0.5}), _gap({"Z1": 0.3}), _ctx()
        )
        for m in result["multipliers"].values():
            assert m == round(m, 2)
