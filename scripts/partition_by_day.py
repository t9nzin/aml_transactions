"""Split a raw transactions CSV into one Parquet folder per transaction date.

The raw header repeats the column name "Account" (once after From Bank, once after
To Bank), so columns are renamed by position rather than by name.

Each row gets a deterministic transaction_id: an MD5 of all raw fields plus an
ordinal that separates exact duplicate rows. The id does not depend on file order
or thread scheduling, so rerunning the split produces the same ids.

    uv run python scripts/partition_by_day.py data/raw/HI-Small_Trans.csv data/partitions
"""

import argparse
import shutil
from pathlib import Path

import duckdb

RAW_COLUMNS = {
    "timestamp_raw": "VARCHAR",
    "from_bank": "VARCHAR",
    "from_account": "VARCHAR",
    "to_bank": "VARCHAR",
    "to_account": "VARCHAR",
    "amount_received": "DOUBLE",
    "receiving_currency": "VARCHAR",
    "amount_paid": "DOUBLE",
    "payment_currency": "VARCHAR",
    "payment_format": "VARCHAR",
    "is_laundering": "INTEGER",
}

PARTITION_SQL = """
with src as (
    select
        *,
        strptime(timestamp_raw, '%Y/%m/%d %H:%M') as transaction_ts
    from read_csv(
        ?,
        header = true,
        columns = {columns},
        timestampformat = '%Y/%m/%d %H:%M'
    )
),
numbered as (
    select
        *,
        row_number() over (partition by columns(* exclude (transaction_ts))) as dup_ordinal
    from src
)
select
    md5(concat_ws('|', {raw_cols}, dup_ordinal)) as transaction_id,
    transaction_ts,
    cast(transaction_ts as date) as transaction_date,
    from_bank,
    from_account,
    to_bank,
    to_account,
    amount_received,
    receiving_currency,
    amount_paid,
    payment_currency,
    payment_format,
    is_laundering,
    ? as source_file
from numbered
"""


def build_query() -> str:
    columns = "{" + ", ".join(f"'{k}': '{v}'" for k, v in RAW_COLUMNS.items()) + "}"
    return PARTITION_SQL.format(columns=columns, raw_cols=", ".join(RAW_COLUMNS))


def partition(csv_path: Path, out_dir: Path, con: duckdb.DuckDBPyConnection | None = None) -> int:
    """Write out_dir/transaction_date=YYYY-MM-DD/*.parquet and return the row count."""
    con = con or duckdb.connect()
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    rel = con.sql(build_query(), params=[str(csv_path), csv_path.name])
    con.register("partitioned", rel)
    con.execute(
        f"copy partitioned to '{out_dir}' (format parquet, partition_by (transaction_date))"
    )
    return con.execute(
        f"select count(*) from read_parquet('{out_dir}/*/*.parquet')"
    ).fetchone()[0]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("out_dir", type=Path)
    args = parser.parse_args()
    rows = partition(args.csv, args.out_dir)
    days = sorted(p.name for p in args.out_dir.iterdir() if p.is_dir())
    print(f"wrote {rows:,} rows across {len(days)} days ({days[0]} .. {days[-1]})")


if __name__ == "__main__":
    main()
