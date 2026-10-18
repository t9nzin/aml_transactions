VARIANT ?= HI-Small
export DBT_PROFILES_DIR := $(CURDIR)/dbt
export AML_DUCKDB_PATH := $(CURDIR)/data/warehouse/aml.duckdb
DBT := cd dbt && uv run dbt

.PHONY: setup data partition load dbt-build dbt-docs test train airflow-up backfill export-dashboard

setup:
	uv sync

data:
	uv run python scripts/download_data.py --variant $(VARIANT)

partition:
	uv run python scripts/partition_by_day.py data/raw/$(VARIANT)_Trans.csv data/partitions

load:
	uv run python scripts/load_day.py --all
	uv run python scripts/parse_patterns.py data/raw/$(VARIANT)_Patterns.txt

dbt-build:
	$(DBT) build

dbt-docs:
	$(DBT) docs generate && $(DBT) docs serve

test:
	uv run pytest
