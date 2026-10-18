"""Alert budget: how many laundering accounts a model catches with a fixed number of alerts.

An investigations team can review a fixed number of alerts per period. Every score threshold
produces some number of alerts and catches some number of true positives; the best cutoff is the
lowest threshold whose alert count still fits the budget, since catches only grow as the
threshold drops.
"""

from dataclasses import asdict, dataclass

import numpy as np


@dataclass(frozen=True)
class BudgetResult:
    budget: int
    threshold: float
    alerts: int
    caught: int
    positives: int
    precision: float
    recall: float

    def to_dict(self) -> dict:
        return asdict(self)


def threshold_curve(scores: np.ndarray, labels: np.ndarray) -> dict[str, np.ndarray]:
    """Alerts, catches, precision and recall at every distinct score threshold.

    A threshold t flags every score >= t. Thresholds are returned from highest to lowest, so
    alerts and caught are non-decreasing. Tied scores are flagged together.
    """
    scores = np.asarray(scores, dtype=float)
    labels = np.asarray(labels).astype(bool)
    if scores.shape != labels.shape:
        raise ValueError("scores and labels must have the same shape")

    order = np.argsort(-scores, kind="stable")
    sorted_scores, sorted_labels = scores[order], labels[order]
    cum_caught = np.cumsum(sorted_labels)

    # Last index of each run of tied scores: flagging t flags the whole run.
    last_of_run = np.flatnonzero(np.r_[sorted_scores[1:] != sorted_scores[:-1], True])
    alerts = last_of_run + 1
    caught = cum_caught[last_of_run]
    positives = int(labels.sum())
    return {
        "threshold": sorted_scores[last_of_run],
        "alerts": alerts,
        "caught": caught,
        "precision": caught / alerts,
        "recall": caught / positives if positives else np.zeros_like(caught, dtype=float),
    }


def best_cutoff(scores: np.ndarray, labels: np.ndarray, budget: int) -> BudgetResult:
    """The threshold that catches the most positives without exceeding `budget` alerts."""
    if budget < 1:
        raise ValueError("budget must be at least 1")
    curve = threshold_curve(scores, labels)
    feasible = np.flatnonzero(curve["alerts"] <= budget)
    positives = int(np.asarray(labels).astype(bool).sum())
    if feasible.size == 0:
        # Even the top score is tied across more rows than the budget allows.
        return BudgetResult(budget, float("inf"), 0, 0, positives, 0.0, 0.0)
    i = feasible[-1]
    return BudgetResult(
        budget=budget,
        threshold=float(curve["threshold"][i]),
        alerts=int(curve["alerts"][i]),
        caught=int(curve["caught"][i]),
        positives=positives,
        precision=float(curve["precision"][i]),
        recall=float(curve["recall"][i]),
    )
