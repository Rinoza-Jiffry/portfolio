"""
plot_positioning_cost.py
========================
Regenerates Figure 1 of the technical report — "Positioning engine cost:
Greedy vs Simulated Annealing" — directly from the real evaluation results in
data/processed/comparison_table.csv (the 'Computation (s)' column).

Run:  python src/plot_positioning_cost.py
Output: outputs/figures/greedy_vs_sa_cost.png

Course: 7COSC013W.1 Foundations of AI, University of Westminster.
"""
from __future__ import annotations
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

try:
    from .config import PATHS, POSITIONING
except ImportError:
    from config import PATHS, POSITIONING

GREEDY_COLOR = "#2A9D8F"
SA_COLOR = "#E76F51"


def main():
    proc = Path(PATHS["data_processed"])
    df = pd.read_csv(proc / "comparison_table.csv")

    # 'Computation (s)' is numeric; Variant is Baseline / Greedy / Sa
    df["Computation (s)"] = pd.to_numeric(df["Computation (s)"], errors="coerce")
    scenarios = ["Monsoon", "Cricket", "Poya"]
    greedy = [float(df[(df.Scenario == s) & (df.Variant == "Greedy")]["Computation (s)"].iloc[0]) for s in scenarios]
    sa = [float(df[(df.Scenario == s) & (df.Variant == "Sa")]["Computation (s)"].iloc[0]) for s in scenarios]

    x = np.arange(len(scenarios))
    w = 0.36
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    b1 = ax.bar(x - w / 2, greedy, w, label="Greedy", color=GREEDY_COLOR)
    b2 = ax.bar(x + w / 2, sa, w, label="Simulated Annealing", color=SA_COLOR)

    ax.set_yscale("log")
    ax.set_ylabel("Mean computation time per cycle (s, log scale)")
    ax.set_title("Positioning engine cost: Greedy vs Simulated Annealing", fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(scenarios)

    budget = POSITIONING.get("time_budget_sec", 5.0)
    ax.axhline(budget, color="#666666", ls="--", lw=1)
    ax.text(len(scenarios) - 0.65, budget * 1.1, f"{budget:g} s budget", color="#666666", fontsize=8, ha="right")

    for b in list(b1) + list(b2):
        ax.annotate(f"{b.get_height():.3f}", (b.get_x() + b.get_width() / 2, b.get_height()),
                    ha="center", va="bottom", fontsize=8)

    ax.legend(frameon=False)
    fig.tight_layout()

    out = Path(PATHS["outputs_figures"])
    out.mkdir(parents=True, exist_ok=True)
    path = out / "greedy_vs_sa_cost.png"
    fig.savefig(path, dpi=140)
    print(f"[FIG] wrote {path}")
    print(f"[FIG] Greedy  : {dict(zip(scenarios, greedy))}")
    print(f"[FIG] SA      : {dict(zip(scenarios, sa))}")


if __name__ == "__main__":
    main()
