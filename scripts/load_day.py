"""Load one day of partitioned transactions into raw.transactions.

The load deletes that date's rows and inserts the partition inside one transaction, so
running it twice for the same date leaves the table unchanged (idempotent).

    uv run python scripts/load_day.py --date 2022-09-01
    uv run python scripts/load_day.py --all          # every partition, oldest first
"""

import argparse
from datetime import date
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PARTITIONS = ROOT / "data" / "partitions"
DEFAULT_WAREHOUSE = ROOT / "data" / "warehouse" / "aml.duckdb"

CREATE_TABLE = """
create schema if not exists raw;
create table if not exists raw.transactions (
    transaction_id varchar not null,
    transaction_ts timestamp not null,
    transaction_date date not null,
    from_bank varchar,
    from_account varchar,
    to_bank varchar,
    to_account varchar,
    amount_received double,
    receiving_currency varchar,
    amount_paid double,
    payment_currency varchar,
    payment_format varchar,
    is_laundering integer,
    source_file varchar,
    loaded_at timestamp
);
"""

COLUMNS = (
    "transaction_id, transaction_ts, transaction_date, from_bank, from_account, to_bank, "
    "to_account, amount_received, receiving_currency, amount_paid, payment_currency, "
    "payment_format, is_laundering, source_file"
)


def partition_path(partitions: Path, day: date) -> Path:
    return partitions / f"transaction_date={day.isoformat()}"


def available_dates(partitions: Path) -> list[date]:
    return sorted(
        date.fromisoformat(p.name.split("=", 1)[1])
        for p in partitions.iterdir()
        if p.is_dir() and p.name.startswith("transaction_date=")
    )


def load_day_duckdb(con: duckdb.DuckDBPyConnection, partitions: Path, day: date) -> int:
    folder = partition_path(partitions, day)
    if not folder.exists():
        raise FileNotFoundError(f"no partition for {day}: {folder}")

    con.execute(CREATE_TABLE)
    con.execute("begin transaction")
    try:
        con.execute("delete from raw.transactions where transaction_date = ?", [day])
        con.execute(
            f"""
            insert into raw.transactions ({COLUMNS}, loaded_at)
            select {COLUMNS}, current_timestamp
            from read_parquet(?, hive_partitioning = true, hive_types = {{'transaction_date': date}})
            """,
            [str(folder / "*.parquet")],
        )
        con.execute("commit")
    except Exception:
        con.execute("rollback")
        raise
    return con.execute(
        "select count(*) from raw.transactions where transaction_date = ?", [day]
    ).fetchone()[0]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--date", type=date.fromisoformat)
    group.add_argument("--all", action="store_true")
    parser.add_argument("--partitions", type=Path, default=DEFAULT_PARTITIONS)
    parser.add_argument("--warehouse", type=Path, default=DEFAULT_WAREHOUSE)
    args = parser.parse_args()

    days = available_dates(args.partitions) if args.all else [args.date]
    args.warehouse.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(args.warehouse)) as con:
        for day in days:
            print(f"{day}: {load_day_duckdb(con, args.partitions, day):,} rows")


if __name__ == "__main__":
    main()
