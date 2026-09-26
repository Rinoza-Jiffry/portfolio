
from __future__ import annotations

import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from config import PATHS
from logger import get_logger

log = get_logger(__name__)

POYA_DAYS_RAW = [

    ("2023-01-06", "Duruthu",   "standard", "Z8",  "Z9",  0.60, 0.30, False, 15000),
    ("2023-02-05", "Navam",     "standard", "Z9",  "Z8",  0.55, 0.25, False, 12000),
    ("2023-03-07", "Medin",     "standard", "Z8",  "Z9",  0.55, 0.25, False, 10000),
    ("2023-04-06", "Bak",       "standard", "Z8",  "Z9",  0.60, 0.30, False, 14000),
    ("2023-05-05", "Vesak",     "vesak",    "Z9",  "Z8",  0.90, 0.70, True,  50000),
    ("2023-06-04", "Poson",     "poson",    "Z8",  "Z9",  0.85, 0.65, True,  45000),
    ("2023-07-03", "Esala",     "standard", "Z8",  "Z9",  0.65, 0.35, False, 18000),
    ("2023-08-01", "Nikini",    "standard", "Z8",  "Z9",  0.60, 0.30, False, 14000),
    ("2023-08-30", "Binara",    "standard", "Z8",  "Z9",  0.60, 0.30, False, 12000),
    ("2023-09-29", "Vap",       "standard", "Z8",  "Z9",  0.60, 0.30, False, 13000),
    ("2023-10-28", "Il",        "standard", "Z9",  "Z8",  0.65, 0.35, False, 16000),
    ("2023-11-27", "Unduvap",   "standard", "Z8",  "Z9",  0.60, 0.30, False, 15000),
    ("2023-12-26", "Duruthu",   "standard", "Z8",  "Z9",  0.60, 0.30, False, 14000),

    ("2024-01-25", "Duruthu",   "standard", "Z8",  "Z9",  0.60, 0.30, False, 16000),
    ("2024-02-24", "Navam",     "standard", "Z9",  "Z8",  0.55, 0.25, False, 13000),
    ("2024-03-25", "Medin",     "standard", "Z8",  "Z9",  0.55, 0.25, False, 11000),
    ("2024-04-23", "Bak",       "standard", "Z8",  "Z9",  0.60, 0.30, False, 15000),
    ("2024-05-23", "Vesak",     "vesak",    "Z9",  "Z8",  0.90, 0.70, True,  55000),
    ("2024-06-21", "Poson",     "poson",    "Z8",  "Z9",  0.85, 0.65, True,  48000),
    ("2024-07-21", "Esala",     "standard", "Z8",  "Z9",  0.65, 0.35, False, 20000),
    ("2024-08-19", "Nikini",    "standard", "Z8",  "Z9",  0.60, 0.30, False, 14000),
    ("2024-09-17", "Binara",    "standard", "Z8",  "Z9",  0.60, 0.30, False, 13000),
    ("2024-10-17", "Vap",       "standard", "Z8",  "Z9",  0.60, 0.30, False, 14000),
    ("2024-11-15", "Il",        "standard", "Z9",  "Z8",  0.65, 0.35, False, 17000),
    ("2024-12-15", "Unduvap",   "standard", "Z8",  "Z9",  0.60, 0.30, False, 15000),

    ("2025-01-13", "Duruthu",   "standard", "Z8",  "Z9",  0.60, 0.30, False, 16000),
    ("2025-02-12", "Navam",     "standard", "Z9",  "Z8",  0.55, 0.25, False, 13000),
    ("2025-03-13", "Medin",     "standard", "Z8",  "Z9",  0.55, 0.25, False, 11000),
    ("2025-04-12", "Bak",       "standard", "Z8",  "Z9",  0.60, 0.30, False, 15000),
    ("2025-05-12", "Vesak",     "vesak",    "Z9",  "Z8",  0.90, 0.70, True,  55000),
    ("2025-06-11", "Poson",     "poson",    "Z8",  "Z9",  0.85, 0.65, True,  50000),
    ("2025-07-10", "Esala",     "standard", "Z8",  "Z9",  0.65, 0.35, False, 20000),
    ("2025-08-09", "Nikini",    "standard", "Z8",  "Z9",  0.60, 0.30, False, 14000),
    ("2025-09-07", "Binara",    "standard", "Z8",  "Z9",  0.60, 0.30, False, 13000),
    ("2025-10-07", "Vap",       "standard", "Z8",  "Z9",  0.60, 0.30, False, 14000),
    ("2025-11-05", "Il",        "standard", "Z9",  "Z8",  0.65, 0.35, False, 17000),
    ("2025-12-04", "Unduvap",   "standard", "Z8",  "Z9",  0.60, 0.30, False, 15000),

    ("2026-01-03", "Duruthu",   "standard", "Z8",  "Z9",  0.60, 0.30, False, 16000),
    ("2026-02-01", "Navam",     "standard", "Z9",  "Z8",  0.55, 0.25, False, 13000),
    ("2026-03-03", "Medin",     "standard", "Z8",  "Z9",  0.55, 0.25, False, 11000),
    ("2026-04-01", "Bak",       "standard", "Z8",  "Z9",  0.60, 0.30, False, 15000),
    ("2026-05-01", "Vesak",     "vesak",    "Z9",  "Z8",  0.90, 0.70, True,  55000),
    ("2026-05-31", "Poson",     "poson",    "Z8",  "Z9",  0.85, 0.65, True,  50000),
    ("2026-06-29", "Esala",     "standard", "Z8",  "Z9",  0.65, 0.35, False, 20000),
    ("2026-07-29", "Nikini",    "standard", "Z8",  "Z9",  0.60, 0.30, False, 14000),
    ("2026-08-27", "Binara",    "standard", "Z8",  "Z9",  0.60, 0.30, False, 13000),
    ("2026-09-26", "Vap",       "standard", "Z8",  "Z9",  0.60, 0.30, False, 14000),
    ("2026-10-25", "Il",        "standard", "Z9",  "Z8",  0.65, 0.35, False, 17000),
    ("2026-11-24", "Unduvap",   "standard", "Z8",  "Z9",  0.60, 0.30, False, 15000),
]

def build_poya_calendar() -> pd.DataFrame:
    columns = [
        "date", "poya_name", "poya_type",
        "primary_zone", "secondary_zone",
        "demand_uplift_primary", "demand_uplift_secondary",
        "is_major_poya", "expected_crowd_estimate",
    ]
    df = pd.DataFrame(POYA_DAYS_RAW, columns=columns)
    df["date"]       = pd.to_datetime(df["date"])
    df["year"]       = df["date"].dt.year
    df["month"]      = df["date"].dt.month
    df["month_name"] = df["date"].dt.strftime("%B")
    df["day_of_week"] = df["date"].dt.weekday
    df["date"]       = df["date"].dt.date

    log.info(
        f"Poya calendar built: {len(df)} entries | "
        f"Years: {df['year'].min()}-{df['year'].max()} | "
        f"Vesak days: {(df['poya_type']=='vesak').sum()} | "
        f"Poson days: {(df['poya_type']=='poson').sum()}"
    )
    return df

def prepare_poya_calendar() -> pd.DataFrame:
    df = build_poya_calendar()

    out_path = PATHS["poya_calendar"]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    log.info(f"Poya calendar saved: {out_path.name}")
    return df

def is_poya_date(check_date: object) -> dict | None:
    poya_path = PATHS["poya_calendar"]
    if not poya_path.exists():
        prepare_poya_calendar()

    df = pd.read_csv(poya_path)
    df["date"] = pd.to_datetime(df["date"]).dt.date

    import datetime
    if isinstance(check_date, str):
        check_date = datetime.date.fromisoformat(check_date)

    match = df[df["date"] == check_date]
    if match.empty:
        return None

    row = match.iloc[0]
    return {
        "is_poya_day":               True,
        "poya_name":                 row["poya_name"],
        "poya_type":                 row["poya_type"],
        "primary_zone":              row["primary_zone"],
        "secondary_zone":            row["secondary_zone"],
        "demand_uplift_primary":     float(row["demand_uplift_primary"]),
        "demand_uplift_secondary":   float(row["demand_uplift_secondary"]),
        "is_major_poya":             bool(row["is_major_poya"]),
        "expected_crowd_estimate":   int(row["expected_crowd_estimate"]),
    }

def validate_poya_calendar(df: pd.DataFrame) -> bool:
    checks = {
        "Required columns present": all(
            c in df.columns for c in [
                "date", "poya_name", "poya_type",
                "primary_zone", "secondary_zone",
                "demand_uplift_primary", "demand_uplift_secondary",
                "is_major_poya"
            ]
        ),
        "At least one Vesak entry":         (df["poya_type"] == "vesak").any(),
        "At least one Poson entry":         (df["poya_type"] == "poson").any(),
        "Primary zone is valid zone ID":    df["primary_zone"].str.match(r"^Z\d+$").all(),
        "Uplifts between 0 and 1":          (
            df["demand_uplift_primary"].between(0, 1).all() and
            df["demand_uplift_secondary"].between(0, 1).all()
        ),
        "Primary uplift >= secondary":      (
            df["demand_uplift_primary"] >= df["demand_uplift_secondary"]
        ).all(),
        "Vesak has highest uplift":         (
            df[df["poya_type"] == "vesak"]["demand_uplift_primary"].min() >= 0.85
        ),
        "Coverage: 2024 entries":           (df["year"] == 2024).sum() >= 12,
        "Coverage: 2025 entries":           (df["year"] == 2025).sum() >= 12,
    }

    all_pass = True
    for check, passed in checks.items():
        status = "PASS" if passed else "FAIL"
        log.info(f"  [{status}] {check}")
        if not passed:
            all_pass = False
    return all_pass

if __name__ == "__main__":
    df = prepare_poya_calendar()
    print("\n--- Poya Calendar Sample ---")
    print(df[["date", "poya_name", "poya_type", "primary_zone",
              "demand_uplift_primary", "is_major_poya"]].to_string(index=False))
    print("\nRunning validation...")
    validate_poya_calendar(df)
