"""Project-wide constants. Values come from notebooks/01_eda.ipynb (see its "Data facts" table)."""

from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PARTITIONS_DIR = DATA_DIR / "partitions"
WAREHOUSE_PATH = DATA_DIR / "warehouse" / "aml.duckdb"
EXPORTS_DIR = DATA_DIR / "exports"
FIGURES_DIR = ROOT / "reports" / "figures"

# Sep 1-10 is the real simulation. Sep 11-18 is a laundering-only tail (~60% laundering share)
# that would let a model learn "active late = launderer", so modeling stops at Sep 10.
MODELING_START = date(2022, 9, 1)
MODELING_END = date(2022, 9, 10)

# Laundering attempts span a median of 3.1 days (p90 4.6), so windows are 5 days long.
# Two tumbling windows: features and labels for train come from the first, test from the second.
WINDOW_DAYS = 5
TRAIN_WINDOW_START = date(2022, 9, 1)
TEST_WINDOW_START = date(2022, 9, 6)

# Investigation capacity, scaled from a weekly budget to the window length.
ALERTS_PER_WEEK = 500
ALERT_BUDGET = round(ALERTS_PER_WEEK * WINDOW_DAYS / 7)

RANDOM_STATE = 42
