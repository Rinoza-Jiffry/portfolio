from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

try:
    from .config import ZONE_IDS, PATHS, DEMAND
except ImportError:
    from config import ZONE_IDS, PATHS, DEMAND

ZONES: List[str] = ZONE_IDS
FLOOR, CAP = -0.60, 2.50
POYA_TYPE_STRENGTH = {"vesak": 1.15, "poson": 1.00, "standard": 0.80}

ZONE_BUSYNESS = {
    "Z1": 1.20, "Z2": 1.10, "Z3": 1.05, "Z4": 0.90, "Z5": 1.00,
    "Z6": 0.85, "Z7": 0.80, "Z8": 0.70, "Z9": 0.95, "Z10": 1.00,
}

def _diurnal_raw(hour: float) -> float:
    morning = 0.30 * math.exp(-((hour - 8.0) / 2.5) ** 2)
    evening = 0.35 * math.exp(-((hour - 18.0) / 2.5) ** 2)
    night = 0.30 * math.exp(-((hour - 3.0) / 3.0) ** 2)
    return morning + evening - night

def _peak_intensity(hour: float) -> float:
    return max(0.0, _diurnal_raw(hour)) / 0.35

def _rain_norm(rain_mm: float) -> float:
    return 1.0 - math.exp(-max(0.0, rain_mm) / 4.0)

class GroundTruthDGP:

    def __init__(self, travel_matrix: pd.DataFrame):
        self.T = travel_matrix

    def diurnal(self, zone: str, hour: float, is_weekend: bool) -> float:
        base = _diurnal_raw(hour) * ZONE_BUSYNESS[zone]
        if is_weekend:
            base *= 0.6
        return base

    def rain_terms(self, zone: str, rain_mm: float, hour: float):
        rn = _rain_norm(rain_mm)
        additive = 0.55 * rn

        interaction = 0.60 * rn * _peak_intensity(hour)
        return additive, interaction

    def event(self, zone: str, ctx: dict) -> float:
        if not ctx.get("event_type") or ctx.get("venue_zone") not in ZONES:
            return 0.0
        crowd_norm = min(1.2, ctx.get("crowd_estimate", 0) / 35000.0)
        mte = max(0.0, ctx.get("minutes_to_event_end", 999))

        ramp = math.exp(-((mte) / 45.0) ** 2)
        tt = float(self.T.loc[ctx["venue_zone"], zone])
        spill = math.exp(-tt / 6.0)
        return 1.10 * crowd_norm * ramp * spill

    def poya(self, zone: str, ctx: dict) -> float:
        if not ctx.get("is_poya_day", False):
            return 0.0
        strength = POYA_TYPE_STRENGTH.get(ctx.get("poya_type", "standard"), 0.80)
        total = 0.0
        for temple_zone, base in (
            (ctx.get("poya_primary_zone"), ctx.get("poya_uplift_primary", 0.0)),
            (ctx.get("poya_secondary_zone"), ctx.get("poya_uplift_secondary", 0.0)),
        ):
            if temple_zone in ZONES:
                tt = float(self.T.loc[temple_zone, zone])
                total += strength * base * math.exp(-tt / 7.0)
        return total

    def demand(self, ctx: dict, rng: Optional[np.random.Generator] = None,
               noise: bool = True) -> Dict[str, float]:
        is_weekend = ctx.get("day_of_week", 0) not in DEMAND["weekdays"]
        hour = ctx.get("hour", 12)
        rain = ctx.get("current_rainfall_mm", 0.0)

        signal = {}
        for z in ZONES:
            add_rain, inter = self.rain_terms(z, rain, hour)
            signal[z] = (
                self.diurnal(z, hour, is_weekend)
                + add_rain + inter
                + self.event(z, ctx)
                + self.poya(z, ctx)
            )

        diffused = {}
        for z in ZONES:
            w_sum, acc = 0.0, 0.0
            for z2 in ZONES:
                if z2 == z:
                    continue
                w = math.exp(-float(self.T.loc[z2, z]) / 8.0)
                acc += w * signal[z2]
                w_sum += w
            diffused[z] = signal[z] + 0.10 * (acc / w_sum if w_sum else 0.0)

        out = {}
        for z in ZONES:
            val = diffused[z]
            if noise and rng is not None:

                sigma = 0.05 + 0.10 * abs(val)
                val += rng.normal(0.0, sigma)
            out[z] = float(max(FLOOR, min(CAP, val)))
        return out

def _load_sources():
    proc = Path(PATHS["data_processed"])
    weather = pd.read_csv(proc / "historical_weather_clean.csv")
    poya = pd.read_csv(proc / "poya_calendar.csv")
    cricket = pd.read_csv(proc / "cricket_fixtures.csv")
    fb_path = Path(PATHS["fallback_events"])
    events = json.loads(fb_path.read_text()) if fb_path.exists() else []
    return weather, poya, cricket, events

def _rainfall_class(mm: float) -> str:
    if mm == 0:
        return "none"
    if mm < 2.5:
        return "light"
    if mm < 5.0:
        return "moderate"
    return "heavy"

def build_context(kind: str, rng, weather, poya, cricket, events) -> dict:
    wrow = weather.iloc[int(rng.integers(len(weather)))]
    ctx = {
        "date": str(wrow["date"]),
        "hour": int(wrow["hour"]),
        "day_of_week": int(wrow["day_of_week"]),
        "current_rainfall_mm": float(wrow["rainfall_mm"]),
        "is_monsoon_season": bool(wrow["is_monsoon_season"]),
        "is_school_run": bool(wrow["is_school_run"]),
        "is_poya_day": False, "poya_type": "none",
        "poya_primary_zone": None, "poya_secondary_zone": None,
        "poya_uplift_primary": 0.0, "poya_uplift_secondary": 0.0,
        "event_type": None, "venue_zone": None,
        "crowd_estimate": 0, "minutes_to_event_end": 999,
    }

    if kind == "poya":
        prow = poya.iloc[int(rng.integers(len(poya)))]
        ctx.update({
            "date": str(prow["date"]),
            "hour": int(rng.integers(6, 20)),
            "is_poya_day": True,
            "poya_type": str(prow["poya_type"]),
            "poya_primary_zone": str(prow["primary_zone"]),
            "poya_secondary_zone": str(prow["secondary_zone"]),
            "poya_uplift_primary": float(prow["demand_uplift_primary"]),
            "poya_uplift_secondary": float(prow["demand_uplift_secondary"]),
        })
    elif kind == "event":
        if rng.random() < 0.6 and len(cricket):
            crow = cricket.iloc[int(rng.integers(len(cricket)))]
            ctx.update({
                "date": str(crow["date"]),
                "event_type": "cricket",
                "venue_zone": str(crow["venue_zone"]),
                "crowd_estimate": int(crow["crowd_estimate"]),
                "minutes_to_event_end": int(rng.integers(0, 120)),
                "hour": int(rng.integers(18, 24)),
            })
        elif len(events):
            ev = events[int(rng.integers(len(events)))]
            etype = ev.get("event_type", "concert")
            etype = "concert" if etype in ("concert", "exhibition", "national") else etype
            ctx.update({
                "date": str(ev.get("date", ctx["date"])),
                "event_type": etype,
                "venue_zone": str(ev.get("zone", "Z3")),
                "crowd_estimate": int(ev.get("crowd_estimate", 2000)),
                "minutes_to_event_end": int(rng.integers(0, 90)),
                "hour": int(rng.integers(17, 23)),
            })

    return ctx

def _split_of(date_str: str) -> str:
    h = int(hashlib.md5(date_str.encode()).hexdigest(), 16) % 100
    if h < 70:
        return "train"
    return "val" if h < 85 else "test"

def generate_dataset(n_contexts: int = 3000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    weather, poya, cricket, events = _load_sources()
    T = pd.read_csv(Path(PATHS["travel_matrix"]), index_col=0)
    dgp = GroundTruthDGP(T)

    kinds = (["weather"] * 55 + ["poya"] * 20 + ["event"] * 25)
    rows = []
    for i in range(n_contexts):
        kind = kinds[int(rng.integers(len(kinds)))]
        ctx = build_context(kind, rng, weather, poya, cricket, events)
        truth = dgp.demand(ctx, rng=rng, noise=True)
        split = _split_of(ctx["date"])
        for z in ZONES:
            tt_v = float(T.loc[ctx["venue_zone"], z]) if ctx["venue_zone"] in ZONES else 99.0
            rows.append({
                "context_id": i, "kind": kind, "split": split,
                "date": ctx["date"], "zone_id": z,
                "hour": ctx["hour"], "day_of_week": ctx["day_of_week"],
                "is_weekend": int(ctx["day_of_week"] not in DEMAND["weekdays"]),
                "rainfall_mm": round(ctx["current_rainfall_mm"], 3),
                "rainfall_class": _rainfall_class(ctx["current_rainfall_mm"]),
                "is_monsoon_season": int(bool(ctx["is_monsoon_season"])),
                "is_school_run": int(bool(ctx["is_school_run"])),
                "is_poya_day": int(ctx["is_poya_day"]),
                "poya_type": ctx["poya_type"],
                "event_type": ctx["event_type"] or "none",
                "minutes_to_event_end": ctx["minutes_to_event_end"],
                "crowd_estimate": ctx["crowd_estimate"],
                "venue_zone": ctx["venue_zone"] or "none",
                "is_venue_zone": int(ctx["venue_zone"] == z),
                "travel_time_to_venue": round(tt_v, 2),
                "true_demand": round(truth[z], 4),
            })
    return pd.DataFrame(rows)

def main():
    df = generate_dataset()
    out = Path(PATHS["data_processed"]) / "demand_dataset.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    counts = df.groupby("split")["context_id"].nunique()
    print(f"[GT] Wrote {out}  ({len(df):,} rows, {df.context_id.nunique():,} contexts)")
    print(f"[GT] Split (contexts): {counts.to_dict()}")
    print(f"[GT] true_demand: min={df.true_demand.min():.3f} "
          f"mean={df.true_demand.mean():.3f} max={df.true_demand.max():.3f}")
    return df

if __name__ == "__main__":
    main()
