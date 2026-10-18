"""Parse the laundering patterns file and load it into raw.laundering_patterns.

The file is a sequence of blocks:

    BEGIN LAUNDERING ATTEMPT - FAN-OUT:  Max 16-degree Fan-Out
    2022/09/01 00:06,021174,800737690,012,80011F990,2848.96,Euro,2848.96,Euro,ACH,1
    ...
    END LAUNDERING ATTEMPT - FAN-OUT

Each transaction line has the same layout as the transactions CSV.

    uv run python scripts/parse_patterns.py data/raw/HI-Small_Patterns.txt
"""

import argparse
import re
from datetime import datetime
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WAREHOUSE = ROOT / "data" / "warehouse" / "aml.duckdb"

BEGIN = re.compile(r"^BEGIN LAUNDERING ATTEMPT - (?P<typology>[A-Z-]+):?\s*(?P<detail>.*)$")
FIELDS = [
    "from_bank",
    "from_account",
    "to_bank",
    "to_account",
    "amount_received",
    "receiving_currency",
    "amount_paid",
    "payment_currency",
    "payment_format",
    "is_laundering",
]


def parse(path: Path) -> pd.DataFrame:
    rows, attempt_id, typology, detail = [], 0, None, None
    for line in path.read_text().splitlines():
        if match := BEGIN.match(line):
            attempt_id += 1
            typology, detail = match["typology"], match["detail"].strip() or None
        elif line.startswith("END"):
            typology = detail = None
        elif line[:2] == "20" and typology:
            ts, *values = line.split(",")
            record = dict(zip(FIELDS, values, strict=True))
            record.update(
                attempt_id=attempt_id,
                typology=typology,
                typology_detail=detail,
                transaction_ts=datetime.strptime(ts, "%Y/%m/%d %H:%M"),
            )
            rows.append(record)

    df = pd.DataFrame(rows)
    df["amount_received"] = df["amount_received"].astype(float)
    df["amount_paid"] = df["amount_paid"].astype(float)
    df["is_laundering"] = df["is_laundering"].astype(int)
    return df[["attempt_id", "typology", "typology_detail", "transaction_ts", *FIELDS]]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("patterns", type=Path)
    parser.add_argument("--warehouse", type=Path, default=DEFAULT_WAREHOUSE)
    args = parser.parse_args()

    df = parse(args.patterns)
    args.warehouse.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(args.warehouse)) as con:
        con.execute("create schema if not exists raw")
        con.execute("create or replace table raw.laundering_patterns as select * from df")
    print(f"{df.attempt_id.nunique()} attempts, {len(df):,} transactions")


if __name__ == "__main__":
    main()
