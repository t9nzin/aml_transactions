"""Time-based train/test split over feature windows.

Random splits would put the same account's later behavior in train and its earlier behavior in
test, so the model would be graded on a past it has effectively seen. Splitting by window keeps
every test row strictly after every train row.
"""

from datetime import date

import pandas as pd


def time_split(
    df: pd.DataFrame, train_window_start: date, test_window_start: date
) -> tuple[pd.DataFrame, pd.DataFrame]:
    train = df[df["window_start"] == train_window_start]
    test = df[df["window_start"] == test_window_start]
    if train.empty or test.empty:
        raise ValueError(
            f"empty split: train={len(train)} rows at {train_window_start}, "
            f"test={len(test)} rows at {test_window_start}"
        )
    if train["window_end"].max() >= test["window_start"].min():
        raise ValueError("train window overlaps test window")
    return train.reset_index(drop=True), test.reset_index(drop=True)
