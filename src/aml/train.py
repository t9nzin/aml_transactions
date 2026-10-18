"""Train, evaluate and score every model in one run.

    uv run python -m aml.train            # with graph features (default)
    uv run python -m aml.train --no-graph

Steps: load the feature mart -> add graph features -> split by time window -> tune gradient
boosting on a held-out slice of train accounts -> fit all models on the train window -> score the
test window -> metrics, alert budget, plots -> write results to the warehouse (schema ml) and to
reports/.
"""

import argparse
import itertools
import json
import time

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score
from sklearn.model_selection import train_test_split

from aml import config, io
from aml.alert_budget import best_cutoff
from aml.evaluate import plot_alert_capacity, plot_calibration, plot_pr_curves, ranking_metrics
from aml.features import ID_COLUMNS, LABEL, feature_columns, load_features
from aml.graph import add_graph_features
from aml.interpret import StandardizedLogit
from aml.models import build_models, score
from aml.splits import time_split

REPORTS = config.ROOT / "reports"
HGB_GRID = {
    "learning_rate": [0.05, 0.1],
    "max_leaf_nodes": [15, 31, 63],
    "class_weight": [None, "balanced"],
}


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def tune_hgb(train: pd.DataFrame, cols) -> dict:
    """Pick gradient boosting settings by PR-AUC on 20% of train accounts (same window).

    With only two windows there is no earlier window to validate on, so tuning holds out
    accounts instead. The test window is never touched here.
    """
    fit_part, val_part = train_test_split(
        train, test_size=0.2, stratify=train[LABEL], random_state=config.RANDOM_STATE
    )
    X_cols = sum(cols, [])
    results = []
    for values in itertools.product(*HGB_GRID.values()):
        params = dict(zip(HGB_GRID, values))
        model = build_models(cols, params)["hist_gradient_boosting"]
        model.fit(fit_part[X_cols], fit_part[LABEL])
        ap = average_precision_score(val_part[LABEL], score(model, val_part[X_cols]))
        results.append((ap, params))
        log(f"  hgb {params} -> validation PR-AUC {ap:.4f}")
    best_ap, best = max(results, key=lambda r: r[0])
    log(f"best hgb params {best} (validation PR-AUC {best_ap:.4f})")
    return best


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--no-graph", action="store_true", help="skip networkx graph features")
    parser.add_argument("--no-tune", action="store_true", help="use default gradient boosting settings")
    args = parser.parse_args()
    use_graph = not args.no_graph
    config.FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    log("loading features")
    df = load_features()
    if use_graph:
        log("adding graph features")
        df = add_graph_features(df)
    train, test = time_split(df, config.TRAIN_WINDOW_START, config.TEST_WINDOW_START)
    log(f"train {len(train):,} rows ({train[LABEL].sum():,} positive), "
        f"test {len(test):,} rows ({test[LABEL].sum():,} positive)")

    cols = feature_columns(use_graph)
    X_cols = sum(cols, [])
    hgb_params = {} if args.no_tune else tune_hgb(train, cols)

    y_test = test[LABEL].to_numpy()
    scores: dict[str, np.ndarray] = {}
    for name, model in build_models(cols, hgb_params).items():
        log(f"fitting {name}")
        if name == "isolation_forest":
            model.fit(train[X_cols])  # no labels
        else:
            model.fit(train[X_cols], train[LABEL])
        scores[name] = score(model, test[X_cols])

    log("fitting statsmodels logit")
    logit = StandardizedLogit(use_graph).fit(train, train[LABEL])
    scores["statsmodels_logit"] = logit.predict_proba(test)
    coefficients = logit.coefficient_table()

    # A simple rule a bank might start with: review the accounts moving the most money.
    scores["rule_total_volume"] = (test["usd_out_total"] + test["usd_in_total"]).to_numpy()

    log("evaluating")
    budget = config.ALERT_BUDGET
    metrics, budget_rows = [], []
    for name, s in scores.items():
        m = ranking_metrics(y_test, s)
        b = best_cutoff(s, y_test, budget)
        metrics.append({"model": name, **m})
        budget_rows.append({"model": name, **b.to_dict()})
    metrics = pd.DataFrame(metrics).sort_values("pr_auc", ascending=False)
    budget_results = pd.DataFrame(budget_rows).sort_values("caught", ascending=False)
    random_caught = budget * y_test.mean()
    budget_results["lift_over_random"] = budget_results["caught"] / random_caught

    plot_pr_curves(y_test, scores, config.FIGURES_DIR / "pr_curves.png")
    plot_calibration(
        y_test,
        {k: v for k, v in scores.items() if k not in ("isolation_forest", "rule_total_volume")},
        config.FIGURES_DIR / "calibration.png",
    )
    plot_alert_capacity(y_test, scores, budget, config.FIGURES_DIR / "alert_capacity.png")

    log("writing results")
    model_scores = pd.concat(
        [
            test[ID_COLUMNS].assign(
                model=name,
                score=s,
                score_rank=pd.Series(s).rank(ascending=False, method="first").astype(int).to_numpy(),
                is_suspicious=y_test,
            )
            for name, s in scores.items()
        ],
        ignore_index=True,
    )
    model_scores["flagged"] = model_scores["model"].map(
        budget_results.set_index("model")["threshold"]
    ).le(model_scores["score"]).astype(int)
    io.write_table(model_scores, "model_scores")
    io.write_table(metrics, "model_metrics")
    io.write_table(budget_results, "alert_budget_results")
    io.write_table(coefficients.reset_index(), "logit_coefficients")

    REPORTS.mkdir(exist_ok=True)
    coefficients.round(4).to_csv(REPORTS / "logit_coefficients.csv")
    summary = {
        "train_window": str(config.TRAIN_WINDOW_START),
        "test_window": str(config.TEST_WINDOW_START),
        "window_days": config.WINDOW_DAYS,
        "graph_features": use_graph,
        "hgb_params": hgb_params,
        "alert_budget": budget,
        "train_rows": len(train),
        "train_positives": int(train[LABEL].sum()),
        "test_rows": len(test),
        "test_positives": int(y_test.sum()),
        "random_caught_at_budget": round(random_caught, 1),
        "metrics": metrics.round(4).to_dict(orient="records"),
        "alert_budget_results": budget_results.round(4).to_dict(orient="records"),
    }
    (REPORTS / "metrics.json").write_text(json.dumps(summary, indent=2, default=str))

    pd.set_option("display.width", 160)
    print(metrics.round(4).to_string(index=False))
    print(budget_results.round(3).to_string(index=False))
    print(coefficients.round(3).to_string())


if __name__ == "__main__":
    main()
