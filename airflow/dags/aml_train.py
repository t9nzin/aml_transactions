"""Train and evaluate all models on the current feature mart, then write scores to the warehouse.

Triggered manually (or after a backfill) rather than daily: the models are trained on a full
feature window, not on single days.
"""

import os
from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator

PROJECT = os.environ.get("AML_PROJECT_DIR", "/opt/project")
VENV = "/opt/aml-venv/bin"

with DAG(
    dag_id="aml_train",
    description="Train models on fct_account_features and write scores to the ml schema",
    start_date=datetime(2022, 9, 1),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    tags=["aml"],
) as dag:
    BashOperator(
        task_id="train",
        bash_command=f"cd {PROJECT} && PYTHONPATH={PROJECT}/src MPLBACKEND=Agg {VENV}/python -m aml.train",
        env={"DBT_TARGET": "{{ var.value.get('dbt_target', 'dev') }}"},
        append_env=True,
    )
