from __future__ import annotations
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.dummy import DummyRegressor
from sklearn.linear_model import Ridge
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import GroupKFold, cross_val_score
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

try:
    from .config import ZONE_IDS, PATHS
    from .demand_rule_base import evaluate_demand
except ImportError:
    from config import ZONE_IDS, PATHS
    from demand_rule_base import evaluate_demand

CAT_COLS = ["zone_id", "rainfall_class", "poya_type", "event_type", "venue_zone"]
NUM_COLS = ["hour", "day_of_week", "is_weekend", "rainfall_mm",
            "is_monsoon_season", "is_school_run", "is_poya_day",
            "minutes_to_event_end", "crowd_estimate",
            "is_venue_zone", "travel_time_to_venue"]
TARGET = "true_demand"
RNG = np.random.default_rng(42)

def _rmse(y, p):
    return float(np.sqrt(mean_squared_error(y, p)))

def _metrics(y, p) -> Dict[str, float]:
    return {"MAE": float(mean_absolute_error(y, p)),
            "RMSE": _rmse(y, p),
            "R2": float(r2_score(y, p))}

def _bootstrap_rmse_ci(df_test: pd.DataFrame, pred_col: str, n: int = 300):
    ctx_ids = df_test["context_id"].unique()
    vals = []
    for _ in range(n):
        sample_ctx = RNG.choice(ctx_ids, size=len(ctx_ids), replace=True)
        sub = df_test[df_test["context_id"].isin(sample_ctx)]
        vals.append(_rmse(sub[TARGET], sub[pred_col]))
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))

def rule_base_predict(df: pd.DataFrame) -> np.ndarray:
    cache: Dict[int, Dict[str, float]] = {}
    preds = np.empty(len(df))
    for i, row in enumerate(df.itertuples(index=False)):
        cid = row.context_id
        if cid not in cache:
            ctx = {
                "hour": int(row.hour), "minute": 0,
                "day_of_week": int(row.day_of_week),
                "current_rainfall_mm": float(row.rainfall_mm),
                "is_poya_day": bool(row.is_poya_day),
                "event_type": None if row.event_type == "none" else row.event_type,
                "venue_zone": None if row.venue_zone == "none" else row.venue_zone,
                "minutes_to_event_end": int(row.minutes_to_event_end),
                "crowd_estimate": int(row.crowd_estimate),
            }
            cache[cid] = evaluate_demand(ctx)["demand_uplifts"]
        preds[i] = cache[cid][row.zone_id]
    return preds

def encode(df: pd.DataFrame, template_cols: List[str] | None = None):
    X = pd.get_dummies(df[CAT_COLS + NUM_COLS], columns=CAT_COLS)
    if template_cols is not None:
        X = X.reindex(columns=template_cols, fill_value=0)
    return X

def main():
    proc = Path(PATHS["data_processed"])
    df = pd.read_csv(proc / "demand_dataset.csv")
    tr = df[df.split == "train"].copy()
    va = df[df.split == "val"].copy()
    te = df[df.split == "test"].copy()

    X_tr = encode(tr)
    cols = list(X_tr.columns)
    X_va = encode(va, cols)
    X_te = encode(te, cols)
    y_tr, y_va, y_te = tr[TARGET].values, va[TARGET].values, te[TARGET].values

    models = {
        "Naive (mean)": DummyRegressor(strategy="mean"),
        "Ridge (linear)": make_pipeline(StandardScaler(with_mean=False), Ridge(alpha=1.0)),
        "Gradient Boosted Trees": GradientBoostingRegressor(
            n_estimators=300, max_depth=3, learning_rate=0.05, random_state=42),
    }

    results = []

    te = te.assign(pred_rule=rule_base_predict(te))
    m = _metrics(y_te, te["pred_rule"].values)
    lo, hi = _bootstrap_rmse_ci(te, "pred_rule")
    results.append({"Model": "Rule base (symbolic)", **m,
                    "RMSE 95% CI": f"[{lo:.3f}, {hi:.3f}]", "CV RMSE": "n/a (no training)"})

    gbm_fitted = None
    for name, model in models.items():
        model.fit(X_tr, y_tr)
        p_te = model.predict(X_te)
        te = te.assign(**{f"pred_{name}": p_te})
        m = _metrics(y_te, p_te)
        lo, hi = _bootstrap_rmse_ci(te, f"pred_{name}")

        cv_str = "n/a"
        if name != "Naive (mean)":
            trva = pd.concat([tr, va])
            Xcv = encode(trva, cols)
            groups = trva["context_id"].values
            gkf = GroupKFold(n_splits=5)
            neg = cross_val_score(model, Xcv, trva[TARGET].values,
                                  groups=groups, cv=gkf,
                                  scoring="neg_root_mean_squared_error")
            cv_str = f"{-neg.mean():.3f} ± {neg.std():.3f}"
        results.append({"Model": name, **m,
                        "RMSE 95% CI": f"[{lo:.3f}, {hi:.3f}]", "CV RMSE": cv_str})
        if name == "Gradient Boosted Trees":
            gbm_fitted = model

    res_df = pd.DataFrame(results)[
        ["Model", "MAE", "RMSE", "R2", "RMSE 95% CI", "CV RMSE"]]
    rep = Path(PATHS["outputs_reports"]); rep.mkdir(parents=True, exist_ok=True)
    res_df.to_csv(rep / "demand_model_comparison.csv", index=False)

    print("\n================ RULE-BASE vs LEARNED — test set ================")
    print(res_df.to_string(index=False,
          formatters={"MAE": "{:.3f}".format, "RMSE": "{:.3f}".format, "R2": "{:.3f}".format}))

    print("\n--- Nonlinear rain x peak interaction (GBM predictions) ---")
    base = dict(zone_id="Z1", rainfall_class="none", poya_type="none",
                event_type="none", venue_zone="none", day_of_week=1, is_weekend=0,
                is_monsoon_season=0, is_school_run=0, is_poya_day=0,
                minutes_to_event_end=999, crowd_estimate=0, is_venue_zone=0,
                travel_time_to_venue=99.0)

    def gbm_pred(hour, rain, rain_class):
        row = {**base, "hour": hour, "rainfall_mm": rain, "rainfall_class": rain_class}
        Xq = encode(pd.DataFrame([row]), cols)
        return float(gbm_fitted.predict(Xq)[0])

    dry_off = gbm_pred(3, 0.0, "none")
    dry_peak = gbm_pred(8, 0.0, "none")
    rain_off = gbm_pred(3, 8.0, "heavy")
    rain_peak = gbm_pred(8, 8.0, "heavy")
    add_pred = dry_peak + (rain_off - dry_off)
    print(f"  dry/off-peak      : {dry_off:+.3f}")
    print(f"  dry/peak          : {dry_peak:+.3f}")
    print(f"  rain/off-peak     : {rain_off:+.3f}")
    print(f"  rain/peak (actual): {rain_peak:+.3f}")
    print(f"  additive expect.  : {add_pred:+.3f}")
    print(f"  super-additivity  : {rain_peak - add_pred:+.3f} "
          f"(>0 means GBM captured the interaction the rules cannot)")

    imp = pd.Series(gbm_fitted.feature_importances_, index=cols).sort_values(ascending=False).head(12)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(imp.index[::-1], imp.values[::-1], color="#2A9D8F")
    ax.set_title("GBM feature importance — learned demand model", fontsize=12, fontweight="bold")
    ax.set_xlabel("Importance")
    fig.tight_layout()
    figs = Path(PATHS["outputs_figures"]); figs.mkdir(parents=True, exist_ok=True)
    fig.savefig(figs / "demand_model_feature_importance.png", dpi=130)
    print(f"\n[FIG] {figs / 'demand_model_feature_importance.png'}")
    print(f"[CSV] {rep / 'demand_model_comparison.csv'}")
    return res_df

if __name__ == "__main__":
    main()
