# data/

Everything in this folder except this file is gitignored.

- `raw/`: Kaggle files as downloaded (`make data`)
- `partitions/`: one Parquet folder per transaction date (`make partition`)
- `warehouse/aml.duckdb`: local DuckDB warehouse
- `exports/`: CSV extracts for the Tableau Public dashboard
