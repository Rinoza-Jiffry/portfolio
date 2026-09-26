
from __future__ import annotations

import sys
import os
from pathlib import Path
import numpy as np
import pandas as pd
from datetime import datetime, date, timedelta

sys.path.insert(0, str(Path(__file__).parent))
from config import PATHS, DEMAND, SIM
from logger import get_logger

log = get_logger(__name__)

COLOMBO_MONTHLY_PARAMS: dict[int, dict] = {
    1:  {"prob": 0.28, "mean_mm":  8.5,  "shape": 0.9, "label": "January   (NE Monsoon)"},
    2:  {"prob": 0.22, "mean_mm":  6.2,  "shape": 0.8, "label": "February  (NE Monsoon)"},
    3:  {"prob": 0.32, "mean_mm":  9.8,  "shape": 1.0, "label": "March     (Inter-monsoon)"},
    4:  {"prob": 0.48, "mean_mm": 14.5,  "shape": 1.1, "label": "April     (Inter-monsoon)"},
    5:  {"prob": 0.68, "mean_mm": 22.3,  "shape": 1.3, "label": "May       (SW Monsoon onset)"},
    6:  {"prob": 0.74, "mean_mm": 24.1,  "shape": 1.4, "label": "June      (SW Monsoon peak)"},
    7:  {"prob": 0.64, "mean_mm": 16.2,  "shape": 1.2, "label": "July      (SW Monsoon)"},
    8:  {"prob": 0.60, "mean_mm": 15.8,  "shape": 1.2, "label": "August    (SW Monsoon)"},
    9:  {"prob": 0.62, "mean_mm": 17.4,  "shape": 1.2, "label": "September (SW Monsoon)"},
    10: {"prob": 0.64, "mean_mm": 20.5,  "shape": 1.3, "label": "October   (Inter-monsoon)"},
    11: {"prob": 0.60, "mean_mm": 18.9,  "shape": 1.2, "label": "November  (Inter-monsoon)"},
    12: {"prob": 0.44, "mean_mm": 12.3,  "shape": 1.0, "label": "December  (NE Monsoon)"},
}

HOURLY_RAIN_WEIGHTS = np.array([
    0.01, 0.01, 0.01, 0.01, 0.01, 0.01,
    0.01, 0.02, 0.02, 0.02, 0.03, 0.03,
    0.04, 0.05, 0.09, 0.11, 0.12, 0.11,
    0.10, 0.08, 0.06, 0.04, 0.02, 0.01,
], dtype=float)
HOURLY_RAIN_WEIGHTS /= HOURLY_RAIN_WEIGHTS.sum()

def classify_rainfall(mm_per_hour: float) -> str:
    heavy    = DEMAND["rainfall_heavy_threshold"]
    moderate = DEMAND["rainfall_moderate_threshold"]

    if mm_per_hour == 0.0:
        return "none"
    elif mm_per_hour < moderate:
        return "light"
    elif mm_per_hour < heavy:
        return "moderate"
    else:
        return "heavy"

def is_monsoon_month(month: int) -> bool:
    return month in DEMAND["monsoon_months"]

def is_school_run_hour(day_of_week: int, hour: int, minute: int = 0) -> bool:
    if day_of_week not in DEMAND["weekdays"]:
        return False

    mr = DEMAND["school_run_morning"]
    ar = DEMAND["school_run_afternoon"]

    morning_start   = mr["start_hour"] * 60 + mr["start_min"]
    morning_end     = mr["end_hour"]   * 60 + mr["end_min"]
    afternoon_start = ar["start_hour"] * 60 + ar["start_min"]
    afternoon_end   = ar["end_hour"]   * 60 + ar["end_min"]

    current_min = hour * 60 + minute
    return (morning_start <= current_min <= morning_end or
            afternoon_start <= current_min <= afternoon_end)

def generate_synthetic_weather(
    start_year: int = 2010,
    end_year:   int = 2023,
    seed:       int = 42
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    log.info(f"Generating synthetic Colombo weather: {start_year}–{end_year}")

    rows: list[dict] = []
    current = date(start_year, 1, 1)
    end     = date(end_year, 12, 31)

    while current <= end:
        m      = current.month
        params = COLOMBO_MONTHLY_PARAMS[m]
        dow    = current.weekday()

        rains_today = rng.random() < params["prob"]

        if rains_today:
            scale      = params["mean_mm"] / params["shape"]
            daily_total = rng.gamma(params["shape"], scale)
            daily_total = min(daily_total, 200.0)
        else:
            daily_total = 0.0

        if daily_total > 0:
            hourly_amounts = HOURLY_RAIN_WEIGHTS * daily_total

            noise = rng.normal(0, 0.05 * hourly_amounts.mean(), size=24)
            hourly_amounts = np.clip(hourly_amounts + noise, 0, None)
        else:
            hourly_amounts = np.zeros(24)

        for hour in range(24):
            mm_hr = float(hourly_amounts[hour])
            rows.append({
                "date":               current.isoformat(),
                "year":               current.year,
                "month":              current.month,
                "hour":               hour,
                "day_of_week":        dow,
                "rainfall_mm":        round(mm_hr, 3),
                "rainfall_class":     classify_rainfall(mm_hr),
                "is_monsoon_season":  is_monsoon_month(m),
                "is_school_run":      is_school_run_hour(dow, hour),
            })

        current += timedelta(days=1)

    df = pd.DataFrame(rows)
    log.info(
        f"Synthetic dataset: {len(df):,} hourly rows | "
        f"Rain hours: {(df['rainfall_mm'] > 0).sum():,} | "
        f"Heavy rain hours: {(df['rainfall_class'] == 'heavy').sum():,}"
    )
    return df

def process_kaggle_weather(csv_path: Path) -> pd.DataFrame:
    log.info(f"Loading Kaggle weather data from: {csv_path}")
    raw = pd.read_csv(csv_path)

    raw.columns = [c.lower().strip() for c in raw.columns]

    date_col = next((c for c in raw.columns if "date" in c), None)
    if date_col is None:
        raise ValueError("No date column found in Kaggle CSV")

    rain_col = next(
        (c for c in raw.columns if any(k in c for k in ["rain", "precip", "rainfall"])),
        None
    )
    if rain_col is None:
        raise ValueError("No rainfall/precipitation column found in Kaggle CSV")

    city_col = next((c for c in raw.columns if "city" in c or "location" in c), None)
    if city_col:
        raw = raw[raw[city_col].str.lower().str.contains("colombo", na=False)].copy()
        log.info(f"Filtered to Colombo: {len(raw):,} daily rows")

    raw[date_col] = pd.to_datetime(raw[date_col])
    raw[rain_col] = pd.to_numeric(raw[rain_col], errors="coerce").fillna(0.0)

    rows: list[dict] = []
    for _, row in raw.iterrows():
        d   = row[date_col].date()
        dow = d.weekday()
        m   = d.month
        daily_total = float(row[rain_col])

        hourly_amounts = HOURLY_RAIN_WEIGHTS * daily_total if daily_total > 0 else np.zeros(24)

        for hour in range(24):
            mm_hr = float(hourly_amounts[hour])
            rows.append({
                "date":               d.isoformat(),
                "year":               d.year,
                "month":              m,
                "hour":               hour,
                "day_of_week":        dow,
                "rainfall_mm":        round(mm_hr, 3),
                "rainfall_class":     classify_rainfall(mm_hr),
                "is_monsoon_season":  is_monsoon_month(m),
                "is_school_run":      is_school_run_hour(dow, hour),
            })

    df = pd.DataFrame(rows)
    log.info(f"Processed Kaggle data: {len(df):,} hourly rows")
    return df

def prepare_weather_dataset() -> pd.DataFrame:
    out_path = PATHS["weather_clean"]

    kaggle_dir  = PATHS["weather_kaggle"]
    kaggle_csvs = list(kaggle_dir.glob("*.csv"))

    if kaggle_csvs:
        log.info(f"Found Kaggle CSV: {kaggle_csvs[0].name} — using real data mode")
        df = process_kaggle_weather(kaggle_csvs[0])
        source = "kaggle"
    else:
        log.warning(
            "No Kaggle CSV found in data/raw/weather_kaggle/ — "
            "switching to synthetic data mode (2010-2023)"
        )
        log.info(
            "To use real data: download 'Sri Lanka Weather Dataset' from Kaggle "
            "and place CSV in data/raw/weather_kaggle/"
        )
        df = generate_synthetic_weather(start_year=2010, end_year=2023, seed=42)
        source = "synthetic"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)

    log.info(
        f"Weather dataset saved ({source}): {out_path.name} | "
        f"Rows: {len(df):,} | "
        f"Years: {df['year'].min()}-{df['year'].max()} | "
        f"Heavy rain hours: {(df['rainfall_class']=='heavy').sum():,}"
    )

    monsoon = df[df["is_monsoon_season"]]
    dry     = df[~df["is_monsoon_season"]]
    log.info(
        f"Monsoon avg rainfall: {monsoon['rainfall_mm'].mean():.3f} mm/hr | "
        f"Dry season avg: {dry['rainfall_mm'].mean():.3f} mm/hr"
    )

    return df

def get_scenario_weather(scenario_type: str) -> dict:
    scenario_weather = {
        "monsoon": {
            "current_rainfall_mm": 7.5,
            "forecast_1h_mm":      6.0,
            "description":         "Southwest monsoon heavy rain (>5mm/hr)"
        },
        "cricket": {
            "current_rainfall_mm": 0.0,
            "forecast_1h_mm":      0.0,
            "description":         "Clear day, no rain — typical match day"
        },
        "poya": {
            "current_rainfall_mm": 1.2,
            "forecast_1h_mm":      0.8,
            "description":         "Light rain on Poya day (common in Oct/Nov)"
        },
    }
    return scenario_weather.get(scenario_type, scenario_weather["monsoon"])

def validate_weather_dataset(df: pd.DataFrame) -> bool:
    checks = {
        "Required columns present": all(
            c in df.columns for c in [
                "date", "hour", "day_of_week", "rainfall_mm",
                "rainfall_class", "is_monsoon_season", "is_school_run"
            ]
        ),
        "No negative rainfall":        (df["rainfall_mm"] >= 0).all(),
        "Rainfall class valid values":  df["rainfall_class"].isin(
            ["none", "light", "moderate", "heavy"]
        ).all(),
        "Hours in [0,23]":             df["hour"].between(0, 23).all(),
        "Day of week in [0,6]":        df["day_of_week"].between(0, 6).all(),
        "Monsoon rows exist":           df["is_monsoon_season"].any(),
        "School run rows exist":        df["is_school_run"].any(),
        "Heavy rain rows exist":        (df["rainfall_class"] == "heavy").any(),
        "Rainfall cap not exceeded":    (df["rainfall_mm"] <= 200.0).all(),
    }

    all_pass = True
    for check, passed in checks.items():
        status = "PASS" if passed else "FAIL"
        log.info(f"  [{status}] {check}")
        if not passed:
            all_pass = False

    return all_pass

if __name__ == "__main__":
    df = prepare_weather_dataset()
    print("\nDataset sample (5 rows):")
    print(df.head().to_string(index=False))
    print("\nRainfall class distribution:")
    print(df["rainfall_class"].value_counts().to_string())
    print("\nRunning validation...")
    ok = validate_weather_dataset(df)
    print(f"\nValidation: {'PASS' if ok else 'FAIL'}")
