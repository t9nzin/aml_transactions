"""Daily AML pipeline: load one day of transfers, then rebuild and test the dbt project.

Each run handles exactly one transaction date ({{ ds }}), so backfilling the DAG replays the
history day by day:

    airflow dags backfill aml_daily -s 2022-09-01 -e 2022-09-18

Re-running a date is safe: load_day.py replaces that date's raw rows and stg_transactions
rebuilds the same date (delete+insert keyed on transaction_date).

max_active_runs=1 and strictly sequential tasks because DuckDB allows a single writer, and the
incremental staging model expects dates to arrive in order.
"""

import os
from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator

PROJECT = os.environ.get("AML_PROJECT_DIR", "/opt/project")
VENV = "/opt/aml-venv/bin"
TARGET = "{{ var.value.get('dbt_target', 'dev') }}"
VARIANT = "{{ var.value.get('aml_variant', 'HI-Small') }}"

with DAG(
    dag_id="aml_daily",
    description="Load one day of transfers into the warehouse and run dbt build",
    start_date=datetime(2022, 9, 1),
    end_date=datetime(2022, 9, 18),
    schedule="@daily",
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 1},
    tags=["aml"],
) as dag:
    check_partition = BashOperator(
        task_id="check_partition",
        bash_command=f"test -d {PROJECT}/data/partitions/transaction_date={{{{ ds }}}}",
    )

    load_day = BashOperator(
        task_id="load_day",
        bash_command=f"{VENV}/python {PROJECT}/scripts/load_day.py --date {{{{ ds }}}} --target {TARGET}",
    )

    load_patterns = BashOperator(
        task_id="load_patterns",
        bash_command=(
            f"{VENV}/python {PROJECT}/scripts/parse_patterns.py "
            f"{PROJECT}/data/raw/{VARIANT}_Patterns.txt --target {TARGET}"
        ),
    )

    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command=(
            f"cd {PROJECT}/dbt && {VENV}/dbt build --target {TARGET} "
            "--vars '{run_date: \"{{ ds }}\"}'"
        ),
    )

    check_partition >> load_day >> load_patterns >> dbt_build
