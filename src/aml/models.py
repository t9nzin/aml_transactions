"""Model pipelines. Every model shares the same preprocessing so comparisons are like for like."""

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import (
    HistGradientBoostingClassifier,
    IsolationForest,
    RandomForestClassifier,
)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler

from aml.config import RANDOM_STATE


def preprocessor(log_cols: list[str], linear_cols: list[str], cat_cols: list[str]) -> ColumnTransformer:
    """log1p + scale heavy-tailed columns, scale bounded ones, one-hot categoricals.

    pass_through_ratio is null when an account received nothing; the imputer fills 0 and adds a
    missing-indicator column so "no inflow" stays visible to the model.
    """
    log_pipe = make_pipeline(
        SimpleImputer(strategy="constant", fill_value=0, add_indicator=True),
        FunctionTransformer(np.log1p, feature_names_out="one-to-one"),
        StandardScaler(),
    )
    return ColumnTransformer(
        [
            ("log", log_pipe, log_cols),
            ("linear", StandardScaler(), linear_cols),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat_cols),
        ],
        verbose_feature_names_out=False,
    )


def build_models(cols: tuple[list[str], list[str], list[str]], hgb_params: dict | None = None) -> dict[str, Pipeline]:
    hgb_params = hgb_params or {}
    supervised = {
        "logistic_regression": LogisticRegression(
            class_weight="balanced", max_iter=2000, random_state=RANDOM_STATE
        ),
        "hist_gradient_boosting": HistGradientBoostingClassifier(
            random_state=RANDOM_STATE, early_stopping=False, **hgb_params
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=300,
            min_samples_leaf=5,
            max_samples=0.3,
            class_weight="balanced_subsample",
            n_jobs=-1,
            random_state=RANDOM_STATE,
        ),
        # Unsupervised: fit without labels, higher score = more anomalous (see anomaly_scores).
        "isolation_forest": IsolationForest(
            n_estimators=300, max_samples=0.3, n_jobs=-1, random_state=RANDOM_STATE
        ),
    }
    return {name: Pipeline([("prep", preprocessor(*cols)), ("model", est)]) for name, est in supervised.items()}


def score(pipeline: Pipeline, X: pd.DataFrame) -> np.ndarray:
    """Higher = more suspicious, for every model type."""
    if isinstance(pipeline.named_steps["model"], IsolationForest):
        return -pipeline.score_samples(X)
    return pipeline.predict_proba(X)[:, 1]
