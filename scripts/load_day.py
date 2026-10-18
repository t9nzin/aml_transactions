"""Load one day of partitioned transactions into raw.transactions.

The load deletes that date's rows and inserts the partition inside one transaction, so
running it twice for the same date leaves the table unchanged (idempotent).

    uv run python scripts/load_day.py --date 2022-09-01
    uv run python scripts/load_day.py --all                  # every partition, oldest first
    uv run python scripts/load_day.py --date 2022-09-01 --target prod   # Snowflake
"""

import argparse
import os
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


SNOWFLAKE_CREATE_TABLE = """
create table if not exists raw.transactions (
    transaction_id varchar not null,
    transaction_ts timestamp_ntz not null,
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
    loaded_at timestamp_ntz
)
"""


def snowflake_connection():
    import snowflake.connector  # optional dependency: uv sync --extra snowflake

    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        role=os.environ.get("SNOWFLAKE_ROLE", "AML_ROLE"),
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "AML_WH"),
        database=os.environ.get("SNOWFLAKE_DATABASE", "AML"),
        schema="RAW",
    )


def load_day_snowflake(con, partitions: Path, day: date) -> int:
    """PUT the day's Parquet files to the stage, then delete + COPY INTO in one transaction.

    The Parquet files do not contain transaction_date (it is the folder name), so COPY uses a
    transform that adds it. FORCE = TRUE is required: Snowflake otherwise skips files it has
    already loaded, which would make a re-run silently load nothing after the delete.
    """
    folder = partition_path(partitions, day)
    if not folder.exists():
        raise FileNotFoundError(f"no partition for {day}: {folder}")
    stage_path = f"@raw.partitions_stage/{folder.name}"
    cur = con.cursor()
    cur.execute(SNOWFLAKE_CREATE_TABLE)
    cur.execute(f"remove {stage_path}/")
    cur.execute(f"put 'file://{folder}/*.parquet' {stage_path}/ auto_compress = false overwrite = true")
    cur.execute("begin")
    try:
        cur.execute("delete from raw.transactions where transaction_date = %s", (day,))
        cur.execute(
            f"""
            copy into raw.transactions ({COLUMNS}, loaded_at)
            from (
                select
                    $1:transaction_id::varchar,
                    $1:transaction_ts::timestamp_ntz,
                    '{day.isoformat()}'::date,
                    $1:from_bank::varchar,
                    $1:from_account::varchar,
                    $1:to_bank::varchar,
                    $1:to_account::varchar,
                    $1:amount_received::double,
                    $1:receiving_currency::varchar,
                    $1:amount_paid::double,
                    $1:payment_currency::varchar,
                    $1:payment_format::varchar,
                    $1:is_laundering::integer,
                    $1:source_file::varchar,
                    current_timestamp()::timestamp_ntz
                from {stage_path}/
            )
            file_format = (format_name = 'raw.parquet_format')
            force = true
            """
        )
        cur.execute("commit")
    except Exception:
        cur.execute("rollback")
        raise
    return cur.execute(
        "select count(*) from raw.transactions where transaction_date = %s", (day,)
    ).fetchone()[0]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--date", type=date.fromisoformat)
    group.add_argument("--all", action="store_true")
    parser.add_argument("--partitions", type=Path, default=DEFAULT_PARTITIONS)
    parser.add_argument("--warehouse", type=Path, default=DEFAULT_WAREHOUSE,
                        help="DuckDB file (AML_DUCKDB_PATH overrides)")
    parser.add_argument("--target", choices=["dev", "prod"], default="dev")
    args = parser.parse_args()
    days = available_dates(args.partitions) if args.all else [args.date]
    if args.target == "prod":
        con = snowflake_connection()
        try:
            for day in days:
                print(f"{day}: {load_day_snowflake(con, args.partitions, day):,} rows")
        finally:
            con.close()
        return

    warehouse = Path(os.environ.get("AML_DUCKDB_PATH", args.warehouse))
    warehouse.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(warehouse)) as con:
        for day in days:
            print(f"{day}: {load_day_duckdb(con, args.partitions, day):,} rows")


if __name__ == "__main__":
    main()
