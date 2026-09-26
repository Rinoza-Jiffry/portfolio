
from __future__ import annotations

import sys
import json
import datetime
from pathlib import Path

import pytest
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import ZONE_IDS, SIM, FLEET_DISTRIBUTIONS, DEMAND, PATHS

class TestRainfallClassification:

    def test_zero_rain_is_none(self):
        from weather_prep import classify_rainfall
        assert classify_rainfall(0.0) == "none"

    def test_light_rain_below_moderate_threshold(self):
        from weather_prep import classify_rainfall
        assert classify_rainfall(1.0) == "light"
        assert classify_rainfall(2.49) == "light"

    def test_moderate_rain_at_boundary(self):
        from weather_prep import classify_rainfall

        assert classify_rainfall(2.5) == "moderate"
        assert classify_rainfall(4.9) == "moderate"

    def test_heavy_rain_at_and_above_threshold(self):
        from weather_prep import classify_rainfall

        assert classify_rainfall(5.0) == "heavy"
        assert classify_rainfall(50.0) == "heavy"

    def test_negative_rain_classified_as_none(self):
        from weather_prep import classify_rainfall

        result = classify_rainfall(0.0)
        assert result == "none"

    def test_thresholds_match_config(self):
        from weather_prep import classify_rainfall
        heavy    = DEMAND["rainfall_heavy_threshold"]
        moderate = DEMAND["rainfall_moderate_threshold"]
        assert classify_rainfall(heavy)    == "heavy"
        assert classify_rainfall(heavy - 0.1) == "moderate"
        assert classify_rainfall(moderate) == "moderate"
        assert classify_rainfall(moderate - 0.1) == "light"

class TestMonsoonFlag:

    def test_sw_monsoon_months_are_true(self):
        from weather_prep import is_monsoon_month
        for m in [5, 6, 7, 8, 9]:
            assert is_monsoon_month(m) is True, f"Month {m} should be monsoon"

    def test_non_monsoon_months_are_false(self):
        from weather_prep import is_monsoon_month
        for m in [1, 2, 3, 4, 10, 11, 12]:
            assert is_monsoon_month(m) is False, f"Month {m} should not be monsoon"

class TestSchoolRunFlag:

    def test_morning_school_run_on_weekday(self):
        from weather_prep import is_school_run_hour
        assert is_school_run_hour(0, 7, 30) is True
        assert is_school_run_hour(4, 8, 0)  is True

    def test_afternoon_school_run_on_weekday(self):
        from weather_prep import is_school_run_hour
        assert is_school_run_hour(1, 15, 0) is True
        assert is_school_run_hour(2, 14, 30) is True

    def test_school_run_is_false_on_weekend(self):
        from weather_prep import is_school_run_hour
        assert is_school_run_hour(5, 7, 30) is False
        assert is_school_run_hour(6, 15, 0) is False

    def test_school_run_is_false_outside_windows(self):
        from weather_prep import is_school_run_hour
        assert is_school_run_hour(0, 12, 0) is False
        assert is_school_run_hour(0, 20, 0) is False

class TestSyntheticWeatherGeneration:

    @pytest.fixture(scope="class")
    def small_dataset(self):
        from weather_prep import generate_synthetic_weather
        return generate_synthetic_weather(start_year=2020, end_year=2021, seed=0)

    def test_output_schema(self, small_dataset):
        required = ["date", "hour", "day_of_week", "rainfall_mm",
                    "rainfall_class", "is_monsoon_season", "is_school_run"]
        for col in required:
            assert col in small_dataset.columns, f"Missing column: {col}"

    def test_no_negative_rainfall(self, small_dataset):
        assert (small_dataset["rainfall_mm"] >= 0).all()

    def test_valid_rainfall_classes(self, small_dataset):
        valid = {"none", "light", "moderate", "heavy"}
        assert set(small_dataset["rainfall_class"].unique()).issubset(valid)

    def test_hours_are_complete(self, small_dataset):
        counts = small_dataset.groupby("date").size()
        assert (counts == 24).all(), "Some days have != 24 hourly rows"

    def test_reproducibility(self):
        from weather_prep import generate_synthetic_weather
        df1 = generate_synthetic_weather(2020, 2020, seed=99)
        df2 = generate_synthetic_weather(2020, 2020, seed=99)
        pd.testing.assert_frame_equal(df1, df2)

    def test_monsoon_wetter_than_dry(self, small_dataset):
        monsoon = small_dataset[small_dataset["is_monsoon_season"]]["rainfall_mm"].mean()
        dry     = small_dataset[~small_dataset["is_monsoon_season"]]["rainfall_mm"].mean()
        assert monsoon > dry, "Monsoon season should be wetter than dry season"

    def test_hourly_weights_normalised(self):
        from weather_prep import HOURLY_RAIN_WEIGHTS
        assert abs(HOURLY_RAIN_WEIGHTS.sum() - 1.0) < 1e-9

    def test_afternoon_peak_is_highest(self):
        from weather_prep import HOURLY_RAIN_WEIGHTS
        afternoon_mean = HOURLY_RAIN_WEIGHTS[14:18].mean()
        morning_mean   = HOURLY_RAIN_WEIGHTS[6:9].mean()
        assert afternoon_mean > morning_mean

class TestPoyaCalendar:

    @pytest.fixture(scope="class")
    def poya_df(self):
        from poya_calendar_gen import build_poya_calendar
        return build_poya_calendar()

    def test_required_columns(self, poya_df):
        required = ["date", "poya_name", "poya_type", "primary_zone",
                    "secondary_zone", "demand_uplift_primary", "demand_uplift_secondary",
                    "is_major_poya"]
        for col in required:
            assert col in poya_df.columns

    def test_vesak_has_highest_uplift(self, poya_df):
        vesak = poya_df[poya_df["poya_type"] == "vesak"]["demand_uplift_primary"].min()
        standard = poya_df[poya_df["poya_type"] == "standard"]["demand_uplift_primary"].max()
        assert vesak > standard, "Vesak should have higher uplift than any standard Poya"

    def test_primary_uplift_gte_secondary(self, poya_df):
        assert (poya_df["demand_uplift_primary"] >= poya_df["demand_uplift_secondary"]).all()

    def test_all_zones_valid(self, poya_df):
        valid = set(ZONE_IDS)
        assert poya_df["primary_zone"].isin(valid).all()
        assert poya_df["secondary_zone"].isin(valid).all()

    def test_uplifts_in_range(self, poya_df):
        assert poya_df["demand_uplift_primary"].between(0.0, 1.0).all()
        assert poya_df["demand_uplift_secondary"].between(0.0, 1.0).all()

    def test_twelve_months_per_year(self, poya_df):
        for year in [2023, 2024, 2025]:
            year_df = poya_df[poya_df["year"] == year]
            assert len(year_df) >= 12, f"Year {year} has only {len(year_df)} Poya days"

    def test_is_poya_date_lookup(self):
        from poya_calendar_gen import build_poya_calendar, is_poya_date
        df = build_poya_calendar()
        df.to_csv(PATHS["poya_calendar"], index=False)
        result = is_poya_date("2025-05-12")
        assert result is not None
        assert result["poya_type"] == "vesak"
        assert result["is_poya_day"] is True

    def test_non_poya_date_returns_none(self):
        from poya_calendar_gen import build_poya_calendar, is_poya_date
        df = build_poya_calendar()
        df.to_csv(PATHS["poya_calendar"], index=False)
        result = is_poya_date("2025-06-15")
        assert result is None

class TestCricketFixtures:

    @pytest.fixture(scope="class")
    def fixtures_df(self):
        from cricket_fixtures_gen import build_cricket_fixtures
        return build_cricket_fixtures()

    def test_required_columns(self, fixtures_df):
        required = ["match_id", "date", "start_time", "expected_end_time",
                    "format", "venue_zone", "crowd_estimate", "capacity"]
        for col in required:
            assert col in fixtures_df.columns

    def test_unique_match_ids(self, fixtures_df):
        assert fixtures_df["match_id"].is_unique

    def test_valid_venue_zones(self, fixtures_df):
        assert fixtures_df["venue_zone"].isin(["Z3", "Z4", "Z10"]).all()

    def test_crowd_within_capacity(self, fixtures_df):
        assert (fixtures_df["crowd_estimate"] <= fixtures_df["capacity"]).all()

    def test_valid_formats(self, fixtures_df):
        assert fixtures_df["format"].isin(["T20I", "ODI", "Test"]).all()

    def test_premadasa_has_most_matches(self, fixtures_df):
        zone_counts = fixtures_df["venue_zone"].value_counts()
        assert zone_counts.idxmax() == "Z10"

    def test_crowd_positive(self, fixtures_df):
        assert (fixtures_df["crowd_estimate"] > 0).all()

    def test_get_match_context_active_match(self):
        from cricket_fixtures_gen import build_cricket_fixtures, get_match_context
        df = build_cricket_fixtures()
        df.to_csv(PATHS["cricket_fixtures"], index=False)

        ctx = get_match_context("2025-07-06", "20:00")
        assert ctx is not None
        assert ctx["event_type"] == "cricket"

    def test_get_match_context_no_match(self):
        from cricket_fixtures_gen import build_cricket_fixtures, get_match_context
        df = build_cricket_fixtures()
        df.to_csv(PATHS["cricket_fixtures"], index=False)
        ctx = get_match_context("2025-04-01", "15:00")
        assert ctx is None

class TestDriverFleet:

    def test_fleet_size_is_correct(self):
        from fleet_generator import generate_driver_fleet
        df = generate_driver_fleet(seed=0, scenario="monsoon")
        assert len(df) == SIM["fleet_size"]

    def test_all_drivers_are_idle(self):
        from fleet_generator import generate_driver_fleet
        df = generate_driver_fleet(seed=0, scenario="cricket")
        assert (df["status"] == "idle").all()

    def test_all_zones_are_valid(self):
        from fleet_generator import generate_driver_fleet
        df = generate_driver_fleet(seed=0, scenario="poya")
        assert df["current_zone"].isin(ZONE_IDS).all()

    def test_driver_ids_are_unique(self):
        from fleet_generator import generate_driver_fleet
        df = generate_driver_fleet(seed=0, scenario="monsoon")
        assert df["driver_id"].is_unique

    def test_reproducibility_same_seed(self):
        from fleet_generator import generate_driver_fleet
        df1 = generate_driver_fleet(seed=7, scenario="cricket")
        df2 = generate_driver_fleet(seed=7, scenario="cricket")
        pd.testing.assert_frame_equal(df1, df2)

    def test_different_seeds_differ(self):
        from fleet_generator import generate_driver_fleet
        df0 = generate_driver_fleet(seed=0, scenario="monsoon")
        df1 = generate_driver_fleet(seed=1, scenario="monsoon")

        assert not (df0["current_zone"] == df1["current_zone"]).all()

    def test_monsoon_concentrates_in_centre(self):
        from fleet_generator import generate_driver_fleet

        z1_counts, z8_counts = [], []
        for seed in range(10):
            df = generate_driver_fleet(seed=seed, scenario="monsoon")
            z1_counts.append((df["current_zone"] == "Z1").sum())
            z8_counts.append((df["current_zone"] == "Z8").sum())
        assert np.mean(z1_counts) > np.mean(z8_counts)

    def test_poya_avoids_temple_zones(self):
        from fleet_generator import generate_driver_fleet
        temple_counts, centre_counts = [], []
        for seed in range(10):
            df = generate_driver_fleet(seed=seed, scenario="poya")
            temple_counts.append(
                (df["current_zone"].isin(["Z8", "Z9"])).sum()
            )
            centre_counts.append(
                (df["current_zone"].isin(["Z1", "Z2"])).sum()
            )
        assert np.mean(temple_counts) < np.mean(centre_counts)

    def test_invalid_scenario_raises(self):
        from fleet_generator import generate_driver_fleet
        with pytest.raises(ValueError, match="Unknown scenario"):
            generate_driver_fleet(seed=0, scenario="invalid_type")

    def test_weight_sum_is_one_for_all_scenarios(self):
        for scenario, weights in FLEET_DISTRIBUTIONS.items():
            total = sum(weights)
            assert abs(total - 1.0) < 1e-9, \
                f"Scenario '{scenario}' weights sum to {total}"

    def test_weight_count_matches_zone_count(self):
        for scenario, weights in FLEET_DISTRIBUTIONS.items():
            assert len(weights) == len(ZONE_IDS), \
                f"Scenario '{scenario}': {len(weights)} weights vs {len(ZONE_IDS)} zones"

class TestFallbackEvents:

    @pytest.fixture(scope="class")
    def events(self):
        fp = PATHS["fallback_events"]
        with open(fp, encoding="utf-8") as f:
            return json.load(f)

    def test_at_least_30_events(self, events):
        assert len(events) >= 30

    def test_required_keys_present(self, events):
        required = {"name", "venue", "zone", "date", "event_type", "crowd_estimate"}
        for i, evt in enumerate(events):
            missing = required - evt.keys()
            assert not missing, f"Event {i} missing keys: {missing}"

    def test_all_zones_valid(self, events):
        valid = set(ZONE_IDS)
        for evt in events:
            assert evt["zone"] in valid, f"Invalid zone '{evt['zone']}' in event '{evt['name']}'"

    def test_crowd_estimates_positive(self, events):
        for evt in events:
            assert isinstance(evt["crowd_estimate"], int) and evt["crowd_estimate"] > 0

    def test_covers_multiple_event_types(self, events):
        types = {evt["event_type"] for evt in events}
        assert "cricket"   in types
        assert "religious" in types
        assert "concert"   in types
        assert "exhibition" in types

    def test_all_zones_covered(self, events):
        covered_zones = {evt["zone"] for evt in events}
        assert len(covered_zones) >= 8, \
            f"Only {len(covered_zones)} zones covered by fallback events"

    def test_dates_are_parseable(self, events):
        for evt in events:
            datetime.date.fromisoformat(evt["date"])
