"""Load the account feature mart and define which columns the models see."""

import pandas as pd

from aml import io

LABEL = "is_suspicious"
ID_COLUMNS = ["account_id", "window_start", "window_end", "bank"]

# Heavy-tailed counts, amounts and durations: modeled on a log1p scale.
LOG_FEATURES = [
    "tx_count",
    "tx_out_count",
    "tx_in_count",
    "usd_out_total",
    "usd_in_total",
    "usd_out_mean",
    "usd_in_mean",
    "usd_out_max",
    "usd_in_max",
    "fan_out",
    "fan_in",
    "max_tx_per_hour",
    "active_hours",
    "mean_gap_minutes",
    "min_gap_minutes",
    "pass_through_ratio",
]

# Already bounded in [0, 1] or small integers.
LINEAR_FEATURES = [
    "share_cross_bank",
    "share_cross_currency",
    "share_self_transfer",
    "share_ach",
    "share_bitcoin",
    "share_cash",
    "share_cheque",
    "share_credit_card",
    "share_reinvestment",
    "share_wire",
    "flow_balance",
    "active_days",
]

CATEGORICAL_FEATURES = ["dominant_payment_format"]

# From aml.graph, computed per window with networkx.
GRAPH_LOG_FEATURES = ["scc_size"]
GRAPH_LINEAR_FEATURES = ["round_trip", "in_short_cycle"]


def feature_columns(use_graph: bool) -> tuple[list[str], list[str], list[str]]:
    """(log-scaled numeric, linear numeric, categorical) feature names."""
    log, linear = list(LOG_FEATURES), list(LINEAR_FEATURES)
    if use_graph:
        log += GRAPH_LOG_FEATURES
        linear += GRAPH_LINEAR_FEATURES
    return log, linear, list(CATEGORICAL_FEATURES)


def load_features() -> pd.DataFrame:
    df = io.read_table("marts.fct_account_features")
    df["window_start"] = pd.to_datetime(df["window_start"]).dt.date
    df["window_end"] = pd.to_datetime(df["window_end"]).dt.date
    return df.sort_values(["window_start", "account_id"]).reset_index(drop=True)
