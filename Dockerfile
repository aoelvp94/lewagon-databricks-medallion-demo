# Astro Runtime for Airflow 3.3 (matches brewery-cosmos-demo mold)
# Runtime 3.3-2 ships Python 3.14 — need dbt-databricks with cp314 wheels.
FROM astrocrpublic.azurecr.io/runtime:3.3-2

# Isolate dbt from Airflow deps (Cosmos local execution mode).
RUN python -m venv /usr/local/airflow/dbt_venv && \
    /usr/local/airflow/dbt_venv/bin/pip install --upgrade pip && \
    /usr/local/airflow/dbt_venv/bin/pip install --no-cache-dir \
      --index-url https://pypi.org/simple \
      --only-binary=:all: \
      "dbt-databricks==1.12.4" \
      "pandas>=2.2.3"
