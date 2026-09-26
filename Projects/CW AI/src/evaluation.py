from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List

import pandas as pd

try:
    from .config import PATHS, SIM, METRICS_TARGETS, ZONE_IDS
    from .simulation import run_scenario, run_scenario_baseline
except ImportError:
    from config import PATHS, SIM, METRICS_TARGETS, ZONE_IDS
    from simulation import run_scenario, run_scenario_baseline

log = logging.getLogger(__name__)
ZONES: List[str] = ZONE_IDS

def discover_scenarios() -> List[Path]:
    base = Path(str(PATHS["data_scenarios"]))
    files = []
    for stype in SIM["scenario_types"]:
        files.extend(sorted((base / stype).glob("*.json")))
    return files

def run_all_scenarios(
    travel_matrix: pd.DataFrame,
    include_sa:  bool = True,
    verbose:     bool = True,
) -> pd.DataFrame:
    scenario_files = discover_scenarios()
    if not scenario_files:
        raise FileNotFoundError(
            "No scenario JSON files found in data/scenarios/. "
            "Run: python -c \"from src.evaluation import generate_scenario_configs; "
            "generate_scenario_configs()\" first."
        )

    rows = []
    total = len(scenario_files) * (3 if include_sa else 2)
    done  = 0

    for sf in scenario_files:
        with sf.open() as fh:
            cfg = json.load(fh)

        try:
            r = run_scenario_baseline(cfg, travel_matrix)
            rows.append({"variant": "baseline", **_flatten(r)})
        except Exception as exc:
            log.error("[EVAL] Baseline failed for %s: %s", sf.name, exc)

        try:
            cfg_greedy = {**cfg, "use_sa": False}
            r = run_scenario(cfg_greedy, travel_matrix)
            rows.append({"variant": "greedy", **_flatten(r)})
        except Exception as exc:
            log.error("[EVAL] Greedy failed for %s: %s", sf.name, exc)

        if include_sa:
            try:
                cfg_sa = {**cfg, "use_sa": True}
                r = run_scenario(cfg_sa, travel_matrix)
                rows.append({"variant": "sa", **_flatten(r)})
            except Exception as exc:
                log.error("[EVAL] SA failed for %s: %s", sf.name, exc)

        done += (3 if include_sa else 2)
        if verbose:
            print(f"  [{done:>3}/{total}] {sf.parent.name}/{sf.name}")

    return pd.DataFrame(rows)

def _flatten(result: dict) -> dict:
    return {
        "scenario_type":  result["scenario_type"],
        "seed":           result["seed"],
        **result["metrics"],
        "fired_rules":    "|".join(result["demand"]["fired_rules"]),
        "n_zones_surged": sum(
            1 for m in result["pricing"]["multipliers"].values() if m > 1.0
        ),
        "avg_multiplier": round(
            pd.Series(list(result["pricing"]["multipliers"].values())).mean(), 3
        ),
    }

def validate_success_criteria(results_df: pd.DataFrame) -> dict:
    greedy = results_df[results_df["variant"] == "greedy"]

    checks = {
        "wait_time_reduction_pct": {
            "target":   METRICS_TARGETS["wait_time_reduction_pct"],
            "achieved": greedy["wait_time_reduction_pct"].mean(),
            "op":       ">=",
        },
        "surge_prevention_rate": {
            "target":   METRICS_TARGETS["surge_prevention_rate"],
            "achieved": greedy["surge_prevention_rate"].mean(),
            "op":       ">=",
        },
        "avg_surge_multiplier": {
            "target":   METRICS_TARGETS["avg_surge_multiplier_max"],
            "achieved": greedy["avg_surge_multiplier"].mean(),
            "op":       "<=",
        },
        "gini_coefficient": {
            "target":   METRICS_TARGETS["gini_target"],
            "achieved": greedy["gini_coefficient"].mean(),
            "op":       "<",
        },
        "constraint_satisfaction_rate": {
            "target":   METRICS_TARGETS["constraint_satisfaction"],
            "achieved": greedy["constraint_satisfaction_rate"].min(),
            "op":       ">=",
        },
        "computation_time_sec": {
            "target":   METRICS_TARGETS["computation_time_max_sec"],
            "achieved": greedy["computation_time_sec"].max(),
            "op":       "<",
        },
    }

    for k, v in checks.items():
        op = v["op"]
        if op == ">=":
            v["pass"] = v["achieved"] >= v["target"]
        elif op == "<=":
            v["pass"] = v["achieved"] <= v["target"]
        elif op == "<":
            v["pass"] = v["achieved"] < v["target"]

    return checks

def build_comparison_table(results_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for stype in SIM["scenario_types"]:
        for variant in ["baseline", "greedy", "sa"]:
            sub = results_df[
                (results_df["scenario_type"] == stype) &
                (results_df["variant"] == variant)
            ]
            if sub.empty:
                continue
            rows.append({
                "Scenario":            stype.capitalize(),
                "Variant":             variant.capitalize(),
                "Surge Prev. Rate":    f"{sub['surge_prevention_rate'].mean():.1%}",
                "Avg Surge Mult.":     f"{sub['avg_surge_multiplier'].mean():.2f}×",
                "Gini Coeff.":         f"{sub['gini_coefficient'].mean():.3f}",
                "Wait Reduction":      f"{sub['wait_time_reduction_pct'].mean():.1%}",
                "Computation (s)":     f"{sub['computation_time_sec'].mean():.3f}",
                "Constraint Sat.":     f"{sub['constraint_satisfaction_rate'].mean():.1%}",
            })
    return pd.DataFrame(rows)

def write_evaluation_summary(checks: dict, comp_df: pd.DataFrame) -> Path:
    rep_dir = Path(str(PATHS["outputs_reports"]))
    rep_dir.mkdir(parents=True, exist_ok=True)
    out = rep_dir / "evaluation_summary.txt"

    lines = [
        "=" * 70,
        "EVALUATION SUMMARY — Colombo Ride-Hailing AI",
        "7COSC013W.1 Foundations of AI, University of Westminster",
        "=" * 70,
        "",
        "SUCCESS CRITERIA (Greedy variant, mean across 10 seeds per type)",
        "-" * 70,
    ]
    for metric, v in checks.items():
        status = "PASS" if v["pass"] else "FAIL"
        lines.append(
            f"  [{status}] {metric:<35}  "
            f"target {v['op']} {v['target']:.2f}  |  "
            f"achieved = {v['achieved']:.4f}"
        )

    n_pass = sum(1 for v in checks.values() if v["pass"])
    lines += [
        "",
        f"  {n_pass}/{len(checks)} criteria met.",
        "",
        "COMPARATIVE ANALYSIS (mean across seeds)",
        "-" * 70,
        comp_df.to_string(index=False),
        "",
    ]

    with out.open("w") as fh:
        fh.write("\n".join(lines))

    log.info("[EVAL] Summary written to %s", out)
    return out

def run_full_evaluation(verbose: bool = True) -> pd.DataFrame:
    matrix_path = Path(str(PATHS["travel_matrix"]))
    travel_matrix = pd.read_csv(matrix_path, index_col=0)

    print("\n" + "=" * 60)
    print("RUNNING 30-SCENARIO EVALUATION SUITE")
    print("=" * 60)

    results_df = run_all_scenarios(travel_matrix, include_sa=True, verbose=verbose)

    proc = Path(str(PATHS["data_processed"]))
    raw_path = proc / "evaluation_results.csv"
    results_df.to_csv(raw_path, index=False)
    print(f"\n[SAVED] {raw_path}")

    comp_df = build_comparison_table(results_df)
    comp_path = proc / "comparison_table.csv"
    comp_df.to_csv(comp_path, index=False)
    print(f"[SAVED] {comp_path}")

    checks   = validate_success_criteria(results_df)
    n_pass   = sum(1 for v in checks.values() if v["pass"])
    print(f"\nSUCCESS CRITERIA: {n_pass}/{len(checks)} passed")
    for metric, v in checks.items():
        icon = "PASS" if v["pass"] else "FAIL"
        print(f"  [{icon}] {metric}: {v['achieved']:.4f} (target {v['op']} {v['target']})")

    summary_path = write_evaluation_summary(checks, comp_df)
    print(f"\n[SAVED] {summary_path}")
    print("\nEvaluation complete.")
    return results_df

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_full_evaluation()
