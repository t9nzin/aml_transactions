"""Write CSV extracts for the Tableau Public dashboard to data/exports/.

Tableau Public cannot connect to DuckDB or Snowflake, so the dashboard reads these files.

    uv run python -m aml.export
"""

import numpy as np
import pandas as pd

from aml import io
from aml.alert_budget import threshold_curve
from aml.config import EXPORTS_DIR

TOP_N = 100
CAPACITY_STEP = 10
CAPACITY_MAX = 2000

QUERIES = {
    "daily_volume": "select * from marts.mart_daily_volume order by transaction_date",
    "laundering_by_format_currency": "select * from marts.mart_laundering_by_format_currency",
    "typology_summary": "select * from marts.mart_typology_summary order by attempts desc",
    "model_comparison": """
        select b.model, b.budget, b.alerts, b.caught, b.positives, b.precision, b.recall,
               b.lift_over_random, m.pr_auc, m.roc_auc,
               m.recall_at_precision_50, m.recall_at_precision_80
        from ml.alert_budget_results b
        join ml.model_metrics m using (model)
        order by b.caught desc
    """,
    "top_flagged_accounts": f"""
        select s.score_rank, s.account_id, s.bank, s.score, s.is_suspicious,
               f.tx_count, f.tx_out_count, f.tx_in_count, f.usd_out_total, f.usd_in_total,
               f.fan_out, f.fan_in, f.share_ach, f.share_cross_bank, f.share_cross_currency,
               f.flow_balance, f.max_tx_per_hour, f.dominant_payment_format
        from ml.model_scores s
        join marts.fct_account_features f using (account_id, window_start)
        where s.model = 'hist_gradient_boosting'
        order by s.score_rank
        limit {TOP_N}
    """,
}


def capacity_curve() -> pd.DataFrame:
    """Laundering accounts caught at every CAPACITY_STEP alerts, per model."""
    scores = io.read_sql("select model, score, is_suspicious from ml.model_scores")
    grid = np.arange(CAPACITY_STEP, CAPACITY_MAX + 1, CAPACITY_STEP)
    rows = []
    for model, g in scores.groupby("model"):
        curve = threshold_curve(g["score"].to_numpy(), g["is_suspicious"].to_numpy())
        # Caught at the largest alert count that fits each budget on the grid.
        idx = np.searchsorted(curve["alerts"], grid, side="right") - 1
        caught = np.where(idx >= 0, curve["caught"][np.maximum(idx, 0)], 0)
        rows.append(pd.DataFrame({"model": model, "alerts": grid, "caught": caught}))
    return pd.concat(rows, ignore_index=True)


def main() -> None:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    for name, sql in QUERIES.items():
        df = io.read_sql(sql)
        df.to_csv(EXPORTS_DIR / f"{name}.csv", index=False)
        print(f"{name}.csv: {len(df):,} rows")
    curve = capacity_curve()
    curve.to_csv(EXPORTS_DIR / "alert_capacity.csv", index=False)
    print(f"alert_capacity.csv: {len(curve):,} rows")


if __name__ == "__main__":
    main()
