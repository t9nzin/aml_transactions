"""Read marts from and write model outputs to the warehouse (DuckDB locally, Snowflake in prod).

The target follows DBT_TARGET (dev = DuckDB, prod = Snowflake), the same switch dbt uses.
"""

import os
from contextlib import contextmanager

import duckdb
import pandas as pd

from aml.config import WAREHOUSE_PATH

OUTPUT_SCHEMA = "ml"


def target() -> str:
    return os.environ.get("DBT_TARGET", "dev")


def _duckdb_path() -> str:
    return os.environ.get("AML_DUCKDB_PATH", str(WAREHOUSE_PATH))


@contextmanager
def _snowflake():
    import snowflake.connector  # optional dependency: uv sync --extra snowflake

    con = snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        role=os.environ.get("SNOWFLAKE_ROLE", "AML_ROLE"),
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "AML_WH"),
        database=os.environ.get("SNOWFLAKE_DATABASE", "AML"),
    )
    try:
        yield con
    finally:
        con.close()


def read_sql(sql: str) -> pd.DataFrame:
    if target() == "prod":
        with _snowflake() as con:
            df = con.cursor().execute(sql).fetch_pandas_all()
        df.columns = df.columns.str.lower()
        return df
    with duckdb.connect(_duckdb_path(), read_only=True) as con:
        return con.sql(sql).df()


def read_table(name: str) -> pd.DataFrame:
    return read_sql(f"select * from {name}")


def write_table(df: pd.DataFrame, name: str, schema: str = OUTPUT_SCHEMA) -> None:
    """Replace schema.name with the contents of df."""
    if target() == "prod":
        from snowflake.connector.pandas_tools import write_pandas

        with _snowflake() as con:
            con.cursor().execute(f"create schema if not exists {schema}")
            write_pandas(
                con,
                df,
                table_name=name.upper(),
                schema=schema.upper(),
                auto_create_table=True,
                overwrite=True,
                quote_identifiers=False,
                use_logical_type=True,
            )
        return
    with duckdb.connect(_duckdb_path()) as con:
        con.execute(f"create schema if not exists {schema}")
        con.register("frame", df)
        con.execute(f"create or replace table {schema}.{name} as select * from frame")
