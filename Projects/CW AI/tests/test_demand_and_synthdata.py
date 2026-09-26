import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from config import ZONE_IDS, PATHS
from demand_rule_base import evaluate_demand
import ground_truth_generator as gt

class TestSchoolRunPrecedence:
    def test_R07_does_not_fire_on_weekend(self):

        ctx = {"day_of_week": 5, "hour": 8, "minute": 15}
        assert "R07" not in evaluate_demand(ctx)["fired_rules"]

    def test_R07_fires_on_weekday(self):
        ctx = {"day_of_week": 1, "hour": 7, "minute": 0}
        assert "R07" in evaluate_demand(ctx)["fired_rules"]

    def test_R08_does_not_fire_on_weekend(self):

        ctx = {"day_of_week": 6, "hour": 15, "minute": 0}
        assert "R08" not in evaluate_demand(ctx)["fired_rules"]

    def test_R08_fires_on_weekday(self):
        ctx = {"day_of_week": 2, "hour": 15, "minute": 0}
        assert "R08" in evaluate_demand(ctx)["fired_rules"]

@pytest.fixture(scope="module")
def dgp():
    T = pd.read_csv(Path(PATHS["travel_matrix"]), index_col=0)
    return gt.GroundTruthDGP(T)

def _ctx(**kw):
    base = dict(hour=12, day_of_week=1, current_rainfall_mm=0.0,
                is_poya_day=False, poya_type="none",
                poya_primary_zone=None, poya_secondary_zone=None,
                poya_uplift_primary=0.0, poya_uplift_secondary=0.0,
                event_type=None, venue_zone=None,
                crowd_estimate=0, minutes_to_event_end=999)
    base.update(kw)
    return base

class TestGroundTruthStructure:
    def test_rain_peak_interaction_is_superadditive(self, dgp):
        z = "Z1"
        d = lambda **kw: dgp.demand(_ctx(**kw), noise=False)[z]
        base = d(hour=3, current_rainfall_mm=0.0)
        peak_only = d(hour=8, current_rainfall_mm=0.0)
        rain_only = d(hour=3, current_rainfall_mm=8.0)
        both = d(hour=8, current_rainfall_mm=8.0)
        additive = peak_only + (rain_only - base)
        assert both > additive + 0.05

    def test_poya_spillover_beyond_temple_zones(self, dgp):
        ctx = _ctx(is_poya_day=True, poya_type="vesak",
                   poya_primary_zone="Z8", poya_secondary_zone="Z9",
                   poya_uplift_primary=0.9, poya_uplift_secondary=0.7)
        d = dgp.demand(ctx, noise=False)

        assert d["Z10"] > dgp.demand(_ctx(), noise=False)["Z10"]

    def test_event_decays_with_travel_time(self, dgp):
        ctx = _ctx(event_type="cricket", venue_zone="Z10",
                   crowd_estimate=35000, minutes_to_event_end=0, hour=22)
        d = dgp.demand(ctx, noise=False)
        assert d["Z10"] > d["Z8"]

    def test_reproducible_same_seed(self):
        a = gt.generate_dataset(n_contexts=50, seed=7)
        b = gt.generate_dataset(n_contexts=50, seed=7)
        pd.testing.assert_frame_equal(a, b)

    def test_demand_within_bounds(self, dgp):
        for h in range(0, 24):
            for z in ZONE_IDS:
                v = dgp.demand(_ctx(hour=h, current_rainfall_mm=20.0),
                               noise=False)[z]
                assert gt.FLOOR <= v <= gt.CAP

class TestDataset:
    @pytest.fixture(scope="class")
    def df(self):
        p = Path(PATHS["data_processed"]) / "demand_dataset.csv"
        if not p.exists():
            gt.main()
        return pd.read_csv(p)

    def test_ten_rows_per_context(self, df):
        assert (df.groupby("context_id").size() == 10).all()

    def test_no_nans_and_nonneg_bounds(self, df):
        assert df["true_demand"].notna().all()
        assert (df["true_demand"] >= gt.FLOOR - 1e-9).all()

    def test_split_is_leakage_safe(self, df):
        per_date_splits = df.groupby("date")["split"].nunique()
        assert (per_date_splits == 1).all()

    def test_all_splits_present(self, df):
        assert set(df["split"].unique()) == {"train", "val", "test"}
