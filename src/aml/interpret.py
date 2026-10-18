"""Interpretable logistic regression (statsmodels) with odds ratios per standard deviation.

A curated, non-redundant feature set: the payment-format shares sum to 1, so including all of
them makes the design matrix singular; a few informative formats are kept and the rest are the
reference group.
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm

LOG_TERMS = ["fan_out", "fan_in", "tx_out_count", "tx_in_count", "usd_out_mean", "max_tx_per_hour"]
LINEAR_TERMS = ["share_cross_bank", "share_cross_currency", "share_ach", "share_cash",
                "share_bitcoin", "flow_balance"]
GRAPH_TERMS = ["round_trip", "in_short_cycle"]


class StandardizedLogit:
    def __init__(self, use_graph: bool):
        self.terms = LOG_TERMS + LINEAR_TERMS + (GRAPH_TERMS if use_graph else [])

    def _design(self, df: pd.DataFrame) -> pd.DataFrame:
        X = df[self.terms].astype(float).copy()
        X[LOG_TERMS] = np.log1p(X[LOG_TERMS])
        X = X.rename(columns={c: f"log1p_{c}" for c in LOG_TERMS})
        return X

    def fit(self, df: pd.DataFrame, y: pd.Series) -> "StandardizedLogit":
        X = self._design(df)
        self.mean_, self.std_ = X.mean(), X.std(ddof=0).replace(0, 1)
        Z = sm.add_constant((X - self.mean_) / self.std_)
        self.result_ = sm.Logit(y.astype(float).to_numpy(), Z).fit(disp=False, maxiter=200)
        return self

    def predict_proba(self, df: pd.DataFrame) -> np.ndarray:
        Z = sm.add_constant((self._design(df) - self.mean_) / self.std_, has_constant="add")
        return np.asarray(self.result_.predict(Z))

    def coefficient_table(self) -> pd.DataFrame:
        r = self.result_
        ci = r.conf_int()
        table = pd.DataFrame(
            {
                "coef_per_sd": r.params,
                "std_err": r.bse,
                "odds_ratio_per_sd": np.exp(r.params),
                "or_ci_low": np.exp(ci[0]),
                "or_ci_high": np.exp(ci[1]),
                "p_value": r.pvalues,
            }
        )
        table.index.name = "term"
        return table.drop(index="const").sort_values("coef_per_sd", key=np.abs, ascending=False)
