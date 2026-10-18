from pathlib import Path

import duckdb
import pytest

from partition_by_day import partition

HEADER = (
    "Timestamp,From Bank,Account,To Bank,Account,Amount Received,Receiving Currency,"
    "Amount Paid,Payment Currency,Payment Format,Is Laundering\n"
)
ROWS = [
    "2022/09/01 00:20,010,8000EBD30,010,8000EBD30,3697.34,US Dollar,3697.34,US Dollar,Reinvestment,0",
    "2022/09/01 00:20,3208,8000F4580,001,8000F5340,0.01,US Dollar,0.01,US Dollar,Cheque,0",
    # exact duplicate of the row above
    "2022/09/01 00:20,3208,8000F4580,001,8000F5340,0.01,US Dollar,0.01,US Dollar,Cheque,0",
    "2022/09/02 13:05,001,8000F5340,0112,800A1B2C3,120.00,Euro,140.00,US Dollar,Wire,1",
]


@pytest.fixture
def raw_csv(tmp_path: Path) -> Path:
    path = tmp_path / "Toy_Trans.csv"
    path.write_text(HEADER + "\n".join(ROWS) + "\n")
    return path


def read(out_dir: Path):
    return duckdb.sql(
        f"select * from read_parquet('{out_dir}/*/*.parquet', hive_partitioning = true)"
    ).df()


def test_one_folder_per_day_and_counts_match(raw_csv, tmp_path):
    out = tmp_path / "parts"
    assert partition(raw_csv, out) == len(ROWS)
    assert sorted(p.name for p in out.iterdir()) == [
        "transaction_date=2022-09-01",
        "transaction_date=2022-09-02",
    ]


def test_duplicate_account_columns_renamed_by_position(raw_csv, tmp_path):
    out = tmp_path / "parts"
    partition(raw_csv, out)
    df = read(out)
    wire = df[df.payment_format == "Wire"].iloc[0]
    assert (wire.from_bank, wire.from_account) == ("001", "8000F5340")
    assert (wire.to_bank, wire.to_account) == ("0112", "800A1B2C3")
    assert wire.amount_paid == 140.0 and wire.amount_received == 120.0


def test_transaction_ids_unique_and_stable(raw_csv, tmp_path):
    partition(raw_csv, tmp_path / "a")
    partition(raw_csv, tmp_path / "b")
    first, second = read(tmp_path / "a"), read(tmp_path / "b")
    assert first.transaction_id.is_unique
    assert set(first.transaction_id) == set(second.transaction_id)
