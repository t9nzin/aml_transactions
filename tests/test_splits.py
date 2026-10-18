from datetime import date

import pandas as pd
import pytest

from aml.splits import time_split


def frame(windows):
    return pd.DataFrame(
        [
            {"account_id": f"a{i}", "window_start": start, "window_end": end}
            for i, (start, end) in enumerate(windows)
        ]
    )


def test_split_keeps_test_strictly_after_train():
    df = frame([(date(2022, 9, 1), date(2022, 9, 5)), (date(2022, 9, 6), date(2022, 9, 10))] * 3)
    train, test = time_split(df, date(2022, 9, 1), date(2022, 9, 6))
    assert len(train) == len(test) == 3
    assert train.window_end.max() < test.window_start.min()


def test_overlapping_windows_are_rejected():
    df = frame([(date(2022, 9, 1), date(2022, 9, 6)), (date(2022, 9, 6), date(2022, 9, 10))])
    with pytest.raises(ValueError, match="overlaps"):
        time_split(df, date(2022, 9, 1), date(2022, 9, 6))


def test_missing_window_is_rejected():
    df = frame([(date(2022, 9, 1), date(2022, 9, 5))])
    with pytest.raises(ValueError, match="empty split"):
        time_split(df, date(2022, 9, 1), date(2022, 9, 6))
