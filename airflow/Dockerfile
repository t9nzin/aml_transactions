FROM apache/airflow:2.10.5-python3.12

# dbt, DuckDB and the modeling stack live in their own virtualenv so they never conflict with
# Airflow's pinned dependencies. Versions come from uv.lock (uv export), so the container
# reads and writes the same DuckDB file format as local runs.
COPY requirements.txt /tmp/aml-requirements.txt
USER root
RUN python -m venv /opt/aml-venv \
    && /opt/aml-venv/bin/pip install --no-cache-dir -r /tmp/aml-requirements.txt
USER airflow
