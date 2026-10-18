"""Ranking metrics and evaluation plots.

PR-AUC (average precision) is the headline metric: about 1 account in 100 is positive, so a model
that flags nobody is 99% accurate. Accuracy is never reported.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from sklearn.calibration import CalibrationDisplay
from sklearn.metrics import average_precision_score, precision_recall_curve, roc_auc_score

from aml.alert_budget import threshold_curve

PRECISION_TARGETS = (0.5, 0.8)
PALETTE = {
    "hist_gradient_boosting": "#1f77b4",
    "random_forest": "#2ca02c",
    "logistic_regression": "#ff7f0e",
    "statsmodels_logit": "#9467bd",
    "isolation_forest": "#d62728",
    "rule_total_volume": "#7f7f7f",
}


def recall_at_precision(labels: np.ndarray, scores: np.ndarray, target: float) -> float:
    """Highest recall among thresholds whose precision is at least `target` (0 if none)."""
    precision, recall, _ = precision_recall_curve(labels, scores)
    ok = precision >= target
    return float(recall[ok].max()) if ok.any() else 0.0


def ranking_metrics(labels: np.ndarray, scores: np.ndarray) -> dict[str, float]:
    metrics = {
        "pr_auc": float(average_precision_score(labels, scores)),
        "roc_auc": float(roc_auc_score(labels, scores)),
        "prevalence": float(np.mean(labels)),
    }
    for target in PRECISION_TARGETS:
        metrics[f"recall_at_precision_{int(target * 100)}"] = recall_at_precision(labels, scores, target)
    return metrics


def plot_pr_curves(labels: np.ndarray, scores: dict[str, np.ndarray], path: Path) -> None:
    fig, ax = plt.subplots(figsize=(7, 5))
    for name, s in scores.items():
        precision, recall, _ = precision_recall_curve(labels, s)
        ap = average_precision_score(labels, s)
        ax.plot(recall, precision, label=f"{name} (PR-AUC {ap:.3f})", color=PALETTE.get(name))
    ax.axhline(np.mean(labels), color="black", linestyle=":", label=f"random ({np.mean(labels):.3f})")
    ax.set(xlabel="recall", ylabel="precision", xlim=(0, 1), ylim=(0, 1.02),
           title="Precision-recall on the test window (Sep 6-10)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_calibration(labels: np.ndarray, probabilities: dict[str, np.ndarray], path: Path) -> None:
    fig, ax = plt.subplots(figsize=(6, 5))
    for name, p in probabilities.items():
        CalibrationDisplay.from_predictions(
            labels, p, n_bins=10, strategy="quantile", name=name, ax=ax, color=PALETTE.get(name)
        )
    ax.set(xscale="log", yscale="log", xlim=(1e-4, 1), ylim=(1e-4, 1),
           title="Calibration (quantile bins, log scale)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_alert_capacity(
    labels: np.ndarray, scores: dict[str, np.ndarray], budget: int, path: Path, max_alerts: int = 2000
) -> None:
    """Laundering accounts caught as the number of alerts grows, with the budget marked."""
    fig, ax = plt.subplots(figsize=(7, 5))
    for name, s in scores.items():
        curve = threshold_curve(s, labels)
        keep = curve["alerts"] <= max_alerts
        ax.step(curve["alerts"][keep], curve["caught"][keep], where="post", label=name,
                color=PALETTE.get(name))
    alerts = np.arange(max_alerts + 1)
    ax.plot(alerts, alerts * np.mean(labels), color="black", linestyle=":", label="random")
    ax.axvline(budget, color="black", linewidth=1)
    ax.annotate(f"budget: {budget} alerts", (budget, ax.get_ylim()[1] * 0.95),
                xytext=(5, 0), textcoords="offset points", fontsize=8, va="top")
    ax.set(xlabel="alerts reviewed", ylabel="laundering accounts caught",
           title="Laundering accounts caught per alert reviewed (test window)")
    ax.legend(fontsize=8, loc="lower right")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
