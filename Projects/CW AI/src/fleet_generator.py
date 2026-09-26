
from __future__ import annotations

import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from config import PATHS, SIM, ZONE_IDS, FLEET_DISTRIBUTIONS
from logger import get_logger

log = get_logger(__name__)

def generate_driver_fleet(
    seed:         int,
    scenario:     str,
    fleet_size:   int = 200,
) -> pd.DataFrame:
    if scenario not in FLEET_DISTRIBUTIONS:
        raise ValueError(f"Unknown scenario '{scenario}'. "
                         f"Valid: {list(FLEET_DISTRIBUTIONS.keys())}")

    weights = FLEET_DISTRIBUTIONS[scenario]
    if abs(sum(weights) - 1.0) > 1e-6:
        raise ValueError(f"Weights for scenario '{scenario}' sum to {sum(weights):.4f}")

    rng = np.random.default_rng(seed)
    zone_assignments = rng.choice(ZONE_IDS, size=fleet_size, p=weights)

    df = pd.DataFrame({
        "driver_id":    [f"DRV_{i:03d}" for i in range(fleet_size)],
        "current_zone": zone_assignments,
        "status":       "idle",
        "seed":         seed,
        "scenario":     scenario,
    })

    return df

def generate_all_fleets(fleet_size: int = 200) -> dict[str, pd.DataFrame]:
    out_dir = PATHS["data_processed"]
    out_dir.mkdir(parents=True, exist_ok=True)

    results: dict[str, pd.DataFrame] = {}
    total_files = 0

    for scenario in SIM["scenario_types"]:
        weights = FLEET_DISTRIBUTIONS[scenario]
        log.info(f"Generating {SIM['n_seeds']} fleets for scenario '{scenario}'")

        zone_distribution_log = {
            z: f"{w*100:.0f}%"
            for z, w in zip(ZONE_IDS, weights)
        }
        log.info(f"  Zone distribution: {zone_distribution_log}")

        for seed in range(SIM["n_seeds"]):
            df = generate_driver_fleet(seed, scenario, fleet_size)
            fname = f"driver_fleet_{scenario}_seed{seed}"
            fpath = out_dir / f"{fname}.csv"
            df.to_csv(fpath, index=False)
            results[fname] = df
            total_files += 1

        sample = results[f"driver_fleet_{scenario}_seed0"]
        zone_counts = sample["current_zone"].value_counts().sort_index()
        log.info(f"  Sample (seed=0) zone counts: {zone_counts.to_dict()}")

    log.info(f"Fleet generation complete: {total_files} CSV files saved to {out_dir}")
    return results

def validate_fleet(df: pd.DataFrame, scenario: str, seed: int) -> bool:
    fleet_size = SIM["fleet_size"]
    checks = {
        f"Row count == {fleet_size}":         len(df) == fleet_size,
        "All drivers are 'idle'":              (df["status"] == "idle").all(),
        "All zones are valid":                 df["current_zone"].isin(ZONE_IDS).all(),
        "Driver IDs are unique":               df["driver_id"].is_unique,
        "Correct seed recorded":               (df["seed"] == seed).all(),
        "Correct scenario recorded":           (df["scenario"] == scenario).all(),
        "No null values":                      df.notnull().all().all(),
    }
    all_pass = True
    for check, passed in checks.items():
        if not passed:
            log.error(f"[FAIL] {scenario}/seed{seed}: {check}")
            all_pass = False
    return all_pass

def validate_all_fleets(results: dict[str, pd.DataFrame]) -> bool:
    log.info("Validating all 30 driver fleet files...")
    all_pass = True
    for fname, df in results.items():
        parts   = fname.split("_")
        scenario = parts[2]
        seed    = int(parts[3].replace("seed", ""))
        ok = validate_fleet(df, scenario, seed)
        if not ok:
            all_pass = False

    if all_pass:
        log.info(f"All {len(results)} fleet files validated: PASS")
    else:
        log.error("Some fleet files failed validation — see errors above")
    return all_pass

def compute_fleet_statistics(results: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for scenario in SIM["scenario_types"]:
        for zone in ZONE_IDS:
            counts = []
            for seed in range(SIM["n_seeds"]):
                df = results[f"driver_fleet_{scenario}_seed{seed}"]
                counts.append((df["current_zone"] == zone).sum())
            rows.append({
                "scenario":  scenario,
                "zone":      zone,
                "mean":      float(np.mean(counts)),
                "std":       float(np.std(counts)),
                "min":       int(np.min(counts)),
                "max":       int(np.max(counts)),
                "weight_pct": FLEET_DISTRIBUTIONS[scenario][ZONE_IDS.index(zone)] * 100
            })
    return pd.DataFrame(rows)

def prepare_driver_fleets() -> dict[str, pd.DataFrame]:
    results = generate_all_fleets(fleet_size=SIM["fleet_size"])
    validate_all_fleets(results)
    stats = compute_fleet_statistics(results)

    stats_path = PATHS["data_processed"] / "fleet_statistics.csv"
    stats.to_csv(stats_path, index=False)
    log.info(f"Fleet statistics saved: {stats_path.name}")

    return results

if __name__ == "__main__":
    results = prepare_driver_fleets()
    print(f"\nGenerated {len(results)} fleet files")

    print("\n--- Zone Distribution by Scenario Type (Seed 0) ---")
    for scenario in SIM["scenario_types"]:
        df = results[f"driver_fleet_{scenario}_seed0"]
        print(f"\n{scenario.upper()} (seed=0):")
        counts = df["current_zone"].value_counts().sort_index()
        for zone, count in counts.items():
            bar = "#" * count
            print(f"  {zone}: {count:3d} {bar[:40]}")
