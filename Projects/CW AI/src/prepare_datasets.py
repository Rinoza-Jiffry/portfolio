
from __future__ import annotations

import sys
import time
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import PATHS, SIM
from logger import get_logger

log = get_logger(__name__)

def run_step_1_weather() -> bool:
    log.info("=" * 55)
    log.info("STEP 1: Historical Weather Dataset")
    log.info("=" * 55)
    from weather_prep import prepare_weather_dataset, validate_weather_dataset
    df = prepare_weather_dataset()
    ok = validate_weather_dataset(df)
    log.info(f"Step 1 complete | rows={len(df):,} | validation={'PASS' if ok else 'FAIL'}")
    return ok

def run_step_2_poya() -> bool:
    log.info("=" * 55)
    log.info("STEP 2: Poya Day Calendar")
    log.info("=" * 55)
    from poya_calendar_gen import prepare_poya_calendar, validate_poya_calendar
    df = prepare_poya_calendar()
    ok = validate_poya_calendar(df)
    log.info(f"Step 2 complete | entries={len(df)} | validation={'PASS' if ok else 'FAIL'}")
    return ok

def run_step_3_cricket() -> bool:
    log.info("=" * 55)
    log.info("STEP 3: Cricket Fixtures")
    log.info("=" * 55)
    from cricket_fixtures_gen import prepare_cricket_fixtures, validate_cricket_fixtures
    df = prepare_cricket_fixtures()
    ok = validate_cricket_fixtures(df)
    log.info(f"Step 3 complete | fixtures={len(df)} | validation={'PASS' if ok else 'FAIL'}")
    return ok

def run_step_4_fleets() -> bool:
    log.info("=" * 55)
    log.info("STEP 4: Simulated Driver Fleets")
    log.info("=" * 55)
    from fleet_generator import prepare_driver_fleets, validate_all_fleets
    results = prepare_driver_fleets()
    ok = validate_all_fleets(results)
    log.info(f"Step 4 complete | files={len(results)} | validation={'PASS' if ok else 'FAIL'}")
    return ok

def run_step_5_events() -> bool:
    log.info("=" * 55)
    log.info("STEP 5: Fallback Events JSON Validation")
    log.info("=" * 55)
    import json
    fallback_path = PATHS["fallback_events"]

    if not fallback_path.exists():
        log.error(f"Fallback events file missing: {fallback_path}")
        return False

    with open(fallback_path, encoding="utf-8") as f:
        events = json.load(f)

    required_keys = {"name", "venue", "zone", "date", "event_type", "crowd_estimate"}
    valid_zones   = {f"Z{i}" for i in range(1, 11)}

    issues = []
    for i, evt in enumerate(events):
        missing = required_keys - evt.keys()
        if missing:
            issues.append(f"Event {i}: missing keys {missing}")
        if evt.get("zone") not in valid_zones:
            issues.append(f"Event {i} ('{evt.get('name', '?')}): invalid zone '{evt.get('zone')}'")
        if not isinstance(evt.get("crowd_estimate"), int) or evt["crowd_estimate"] <= 0:
            issues.append(f"Event {i}: crowd_estimate must be positive int")

    if issues:
        for issue in issues:
            log.error(f"  [FAIL] {issue}")
        return False

    log.info(f"Step 5 complete | events={len(events)} | validation=PASS")
    return True

def print_dataset_summary() -> None:
    processed_dir = PATHS["data_processed"]
    print("\n" + "=" * 60)
    print("  PHASE 2 DATASET SUMMARY")
    print("=" * 60)

    datasets = [
        ("Weather",          PATHS["weather_clean"]),
        ("Poya Calendar",    PATHS["poya_calendar"]),
        ("Cricket Fixtures", PATHS["cricket_fixtures"]),
        ("Fleet Statistics", processed_dir / "fleet_statistics.csv"),
    ]

    import pandas as pd
    for name, path in datasets:
        if path.exists():
            df = pd.read_csv(path)
            size_kb = path.stat().st_size / 1024
            print(f"  {name:<20} {len(df):>8,} rows  {size_kb:>8.1f} KB  {path.name}")
        else:
            print(f"  {name:<20} {'MISSING':>8}")

    fleet_files = list(processed_dir.glob("driver_fleet_*.csv"))
    total_fleet_kb = sum(f.stat().st_size for f in fleet_files) / 1024
    print(f"  {'Driver Fleets':<20} {len(fleet_files):>8} files {total_fleet_kb:>7.1f} KB  "
          f"({SIM['n_seeds']} seeds x {len(SIM['scenario_types'])} scenarios)")

    fe_path = PATHS["fallback_events"]
    if fe_path.exists():
        import json
        events = json.load(open(fe_path, encoding="utf-8"))
        print(f"  {'Fallback Events':<20} {len(events):>8} events {fe_path.stat().st_size/1024:.1f} KB  {fe_path.name}")

    print("=" * 60)
    print(f"  Output directory: {processed_dir}")
    print("=" * 60)

STEPS = {
    1: ("Weather Dataset",    run_step_1_weather),
    2: ("Poya Calendar",      run_step_2_poya),
    3: ("Cricket Fixtures",   run_step_3_cricket),
    4: ("Driver Fleets",      run_step_4_fleets),
    5: ("Fallback Events",    run_step_5_events),
}

def main(step: int | None = None) -> None:
    start_total = time.perf_counter()
    results: dict[int, bool] = {}

    steps_to_run = [step] if step else list(STEPS.keys())

    log.info("=" * 55)
    log.info("  PHASE 2: DATASET PREPARATION")
    log.info("  7COSC013W.1 Foundations of AI")
    log.info("=" * 55)

    for s in steps_to_run:
        name, fn = STEPS[s]
        t0 = time.perf_counter()
        try:
            ok = fn()
        except Exception as e:
            log.error(f"Step {s} ({name}) raised exception: {e}", exc_info=True)
            ok = False
        elapsed = time.perf_counter() - t0
        results[s] = ok
        status = "PASS" if ok else "FAIL"
        log.info(f"Step {s} ({name}): {status} ({elapsed:.1f}s)")

    total_elapsed = time.perf_counter() - start_total
    passed = sum(results.values())
    total  = len(results)

    print("\n" + "=" * 55)
    print(f"  PHASE 2 RESULTS: {passed}/{total} steps passed ({total_elapsed:.1f}s)")
    for s, ok in results.items():
        print(f"    Step {s} {STEPS[s][0]}: {'PASS' if ok else 'FAIL'}")

    if passed == total:
        print("  STATUS: Phase 2 complete. Ready for Phase 3.")
    else:
        print("  STATUS: Fix FAIL steps above, then re-run.")
    print("=" * 55)

    if passed == total:
        print_dataset_summary()

    sys.exit(0 if passed == total else 1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 2 Dataset Preparation")
    parser.add_argument("--step", type=int, choices=[1, 2, 3, 4, 5],
                        help="Run only one step (1-5). Omit to run all.")
    args = parser.parse_args()
    main(step=args.step)
