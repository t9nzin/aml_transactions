from datetime import date

import duckdb

from load_day import available_dates, load_day_duckdb
from partition_by_day import partition
from test_partitioning import HEADER, ROWS


def test_reloading_a_day_is_idempotent(tmp_path):
    csv = tmp_path / "Toy_Trans.csv"
    csv.write_text(HEADER + "\n".join(ROWS) + "\n")
    parts = tmp_path / "parts"
    partition(csv, parts)
    con = duckdb.connect()

    assert available_dates(parts) == [date(2022, 9, 1), date(2022, 9, 2)]
    for day in available_dates(parts):
        load_day_duckdb(con, parts, day)
    before = con.execute("select count(*), bit_xor(hash(transaction_id)) from raw.transactions").fetchone()

    assert load_day_duckdb(con, parts, date(2022, 9, 1)) == 3
    after = con.execute("select count(*), bit_xor(hash(transaction_id)) from raw.transactions").fetchone()
    assert before == after == (len(ROWS), before[1])
