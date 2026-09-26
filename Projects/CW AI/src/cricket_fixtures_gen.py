
from __future__ import annotations

import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from config import PATHS
from logger import get_logger

log = get_logger(__name__)

FIXTURES_RAW = [

    {
        "match_id":                "SL_IND_T20_1_2024",
        "date":                    "2024-07-27",
        "start_time":              "19:30",
        "expected_end_time":       "23:00",
        "format":                  "T20I",
        "teams":                   "Sri Lanka vs India",
        "venue_name":              "R. Premadasa Stadium, Colombo",
        "venue_zone":              "Z10",
        "capacity":                35000,
        "crowd_estimate":          32000,
        "demand_zone_primary":     "Z10",
        "demand_zones_secondary":  "Z3,Z4,Z1",
        "post_match_duration_min": 60,
    },
    {
        "match_id":                "SL_IND_T20_2_2024",
        "date":                    "2024-07-28",
        "start_time":              "19:30",
        "expected_end_time":       "23:00",
        "format":                  "T20I",
        "teams":                   "Sri Lanka vs India",
        "venue_name":              "R. Premadasa Stadium, Colombo",
        "venue_zone":              "Z10",
        "capacity":                35000,
        "crowd_estimate":          33000,
        "demand_zone_primary":     "Z10",
        "demand_zones_secondary":  "Z3,Z4,Z1",
        "post_match_duration_min": 60,
    },
    {
        "match_id":                "SL_IND_T20_3_2024",
        "date":                    "2024-07-30",
        "start_time":              "19:30",
        "expected_end_time":       "23:00",
        "format":                  "T20I",
        "teams":                   "Sri Lanka vs India",
        "venue_name":              "R. Premadasa Stadium, Colombo",
        "venue_zone":              "Z10",
        "capacity":                35000,
        "crowd_estimate":          35000,
        "demand_zone_primary":     "Z10",
        "demand_zones_secondary":  "Z3,Z4,Z1",
        "post_match_duration_min": 60,
    },

    {
        "match_id":                "SL_IND_ODI_1_2024",
        "date":                    "2024-08-02",
        "start_time":              "14:30",
        "expected_end_time":       "22:00",
        "format":                  "ODI",
        "teams":                   "Sri Lanka vs India",
        "venue_name":              "R. Premadasa Stadium, Colombo",
        "venue_zone":              "Z10",
        "capacity":                35000,
        "crowd_estimate":          30000,
        "demand_zone_primary":     "Z10",
        "demand_zones_secondary":  "Z3,Z4,Z1",
        "post_match_duration_min": 90,
    },
    {
        "match_id":                "SL_IND_ODI_2_2024",
        "date":                    "2024-08-04",
        "start_time":              "14:30",
        "expected_end_time":       "22:00",
        "format":                  "ODI",
        "teams":                   "Sri Lanka vs India",
        "venue_name":              "R. Premadasa Stadium, Colombo",
        "venue_zone":              "Z10",
        "capacity":                35000,
        "crowd_estimate":          28000,
        "demand_zone_primary":     "Z10",
        "demand_zones_secondary":  "Z3,Z4,Z1",
        "post_match_duration_min": 90,
    },

    {
        "match_id":                "SL_AFG_T20_1_2024",
        "date":                    "2024-09-06",
        "start_time":              "19:30",
        "expected_end_time":       "23:00",
        "format":                  "T20I",
        "teams":                   "Sri Lanka vs Afghanistan",
        "venue_name":              "R. Premadasa Stadium, Colombo",
        "venue_zone":              "Z10",
        "capacity":                35000,
        "crowd_estimate":          22000,
        "demand_zone_primary":     "Z10",
        "demand_zones_secondary":  "Z3,Z4",
        "post_match_duration_min": 60,
    },

    {
        "match_id":                "SL_ENG_TEST_2_2025",
        "date":                    "2025-01-14",
        "start_time":              "10:00",
        "expected_end_time":       "16:30",
        "format":                  "Test",
        "teams":                   "Sri Lanka vs England (Day 1)",
        "venue_name":              "Sinhalese Sports Club, Colombo",
        "venue_zone":              "Z4",
        "capacity":                10000,
        "crowd_estimate":          8500,
        "demand_zone_primary":     "Z4",
        "demand_zones_secondary":  "Z3,Z1",
        "post_match_duration_min": 45,
    },

    {
        "match_id":                "SL_NZ_T20_1_2025",
        "date":                    "2025-04-06",
        "start_time":              "19:30",
        "expected_end_time":       "23:00",
        "format":                  "T20I",
        "teams":                   "Sri Lanka vs New Zealand",
        "venue_name":              "R. Premadasa Stadium, Colombo",
        "venue_zone":              "Z10",
        "capacity":                35000,
        "crowd_estimate":          25000,
        "demand_zone_primary":     "Z10",
        "demand_zones_secondary":  "Z3,Z4,Z1",
        "post_match_duration_min": 60,
    },
    {
        "match_id":                "SL_NZ_T20_2_2025",
        "date":                    "2025-04-09",
        "start_time":              "19:30",
        "expected_end_time":       "23:00",
        "format":                  "T20I",
        "teams":                   "Sri Lanka vs New Zealand",
        "venue_name":              "R. Premadasa Stadium, Colombo",
        "venue_zone":              "Z10",
        "capacity":                35000,
        "crowd_estimate":          27000,
        "demand_zone_primary":     "Z10",
        "demand_zones_secondary":  "Z3,Z4,Z1",
        "post_match_duration_min": 60,
    },

    {
        "match_id":                "SL_BAN_T20_1_2025",
        "date":                    "2025-07-06",
        "start_time":              "19:30",
        "expected_end_time":       "23:00",
        "format":                  "T20I",
        "teams":                   "Sri Lanka vs Bangladesh",
        "venue_name":              "R. Premadasa Stadium, Colombo",
        "venue_zone":              "Z10",
        "capacity":                35000,
        "crowd_estimate":          20000,
        "demand_zone_primary":     "Z10",
        "demand_zones_secondary":  "Z3,Z4",
        "post_match_duration_min": 60,
    },
    {
        "match_id":                "SL_BAN_ODI_1_2025",
        "date":                    "2025-07-12",
        "start_time":              "14:30",
        "expected_end_time":       "22:00",
        "format":                  "ODI",
        "teams":                   "Sri Lanka vs Bangladesh",
        "venue_name":              "R. Premadasa Stadium, Colombo",
        "venue_zone":              "Z10",
        "capacity":                35000,
        "crowd_estimate":          22000,
        "demand_zone_primary":     "Z10",
        "demand_zones_secondary":  "Z3,Z4,Z1",
        "post_match_duration_min": 90,
    },

    {
        "match_id":                "SL_WI_T20_1_2025",
        "date":                    "2025-09-13",
        "start_time":              "19:30",
        "expected_end_time":       "23:00",
        "format":                  "T20I",
        "teams":                   "Sri Lanka vs West Indies",
        "venue_name":              "R. Premadasa Stadium, Colombo",
        "venue_zone":              "Z10",
        "capacity":                35000,
        "crowd_estimate":          24000,
        "demand_zone_primary":     "Z10",
        "demand_zones_secondary":  "Z3,Z4,Z1",
        "post_match_duration_min": 60,
    },

    {
        "match_id":                "SL_PAK_TEST_1_2025",
        "date":                    "2025-07-19",
        "start_time":              "10:00",
        "expected_end_time":       "16:30",
        "format":                  "Test",
        "teams":                   "Sri Lanka vs Pakistan (Day 1)",
        "venue_name":              "Sinhalese Sports Club, Colombo",
        "venue_zone":              "Z4",
        "capacity":                10000,
        "crowd_estimate":          9000,
        "demand_zone_primary":     "Z4",
        "demand_zones_secondary":  "Z3,Z1",
        "post_match_duration_min": 45,
    },

    {
        "match_id":                "SL_DOMESTIC_2025",
        "date":                    "2025-08-23",
        "start_time":              "10:00",
        "expected_end_time":       "16:30",
        "format":                  "ODI",
        "teams":                   "Colombo Cricket Club vs Nondescripts CC",
        "venue_name":              "P. Sara Oval, Borella",
        "venue_zone":              "Z3",
        "capacity":                10000,
        "crowd_estimate":          5000,
        "demand_zone_primary":     "Z3",
        "demand_zones_secondary":  "Z4,Z1",
        "post_match_duration_min": 45,
    },
]

def build_cricket_fixtures() -> pd.DataFrame:
    df = pd.DataFrame(FIXTURES_RAW)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["year"] = pd.to_datetime(df["date"].astype(str)).dt.year
    df["is_evening_match"] = df["start_time"].apply(
        lambda t: int(t.split(":")[0]) >= 17
    )
    log.info(
        f"Cricket fixtures: {len(df)} matches | "
        f"Venues: Premadasa={len(df[df['venue_zone']=='Z10'])}, "
        f"SSC={len(df[df['venue_zone']=='Z4'])}, "
        f"P.Sara={len(df[df['venue_zone']=='Z3'])}"
    )
    return df

def prepare_cricket_fixtures() -> pd.DataFrame:
    df = build_cricket_fixtures()
    out_path = PATHS["cricket_fixtures"]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    log.info(f"Cricket fixtures saved: {out_path.name}")
    return df

def get_match_context(match_date: str, current_time_str: str) -> dict | None:
    import datetime
    fixtures_path = PATHS["cricket_fixtures"]
    if not fixtures_path.exists():
        prepare_cricket_fixtures()

    df = pd.read_csv(fixtures_path)
    df["date"] = pd.to_datetime(df["date"]).dt.date

    check_date = datetime.date.fromisoformat(match_date)
    current_h, current_m = map(int, current_time_str.split(":"))
    current_min = current_h * 60 + current_m

    matches_today = df[df["date"] == check_date]
    if matches_today.empty:
        return None

    for _, match in matches_today.iterrows():
        end_h, end_m = map(int, str(match["expected_end_time"]).split(":"))
        end_min = end_h * 60 + end_m
        start_h, start_m = map(int, str(match["start_time"]).split(":"))
        start_min = start_h * 60 + start_m

        if start_min <= current_min <= end_min + int(match["post_match_duration_min"]):
            minutes_to_end = max(0, end_min - current_min)
            return {
                "event_type":           "cricket",
                "match_id":             match["match_id"],
                "venue_zone":           match["venue_zone"],
                "crowd_estimate":       int(match["crowd_estimate"]),
                "format":               match["format"],
                "teams":                match["teams"],
                "minutes_to_event_end": minutes_to_end,
                "is_post_match":        current_min > end_min,
            }
    return None

def validate_cricket_fixtures(df: pd.DataFrame) -> bool:
    checks = {
        "Required columns present": all(
            c in df.columns for c in [
                "match_id", "date", "start_time", "expected_end_time",
                "format", "venue_zone", "crowd_estimate"
            ]
        ),
        "All venue zones are valid":    df["venue_zone"].isin(["Z3", "Z4", "Z10"]).all(),
        "Crowd estimates are positive": (df["crowd_estimate"] > 0).all(),
        "Crowd <= capacity":            (df["crowd_estimate"] <= df["capacity"]).all(),
        "Format values are valid":      df["format"].isin(["T20I", "ODI", "Test"]).all(),
        "Match IDs are unique":         df["match_id"].is_unique,
        "Premadasa fixtures present":   (df["venue_zone"] == "Z10").any(),
        "SSC fixtures present":         (df["venue_zone"] == "Z4").any(),
    }

    all_pass = True
    for check, passed in checks.items():
        status = "PASS" if passed else "FAIL"
        log.info(f"  [{status}] {check}")
        if not passed:
            all_pass = False
    return all_pass

if __name__ == "__main__":
    df = prepare_cricket_fixtures()
    print("\n--- Cricket Fixtures ---")
    print(df[["match_id", "date", "format", "venue_zone",
              "crowd_estimate", "start_time"]].to_string(index=False))
    print("\nRunning validation...")
    validate_cricket_fixtures(df)
