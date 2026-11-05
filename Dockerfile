# Astro Runtime for Airflow 3.3 — teaching DAG still needs Core 1.x for Cosmos.
# Fusion / dbt v2 is installed in a *second* venv for CLI benchmarks only.
FROM astrocrpublic.azurecr.io/runtime:3.3-2

# Cosmos path (unchanged): classic dbt-databricks on Core 1.x
RUN python -m venv /usr/local/airflow/dbt_venv && \
    /usr/local/airflow/dbt_venv/bin/pip install --upgrade pip && \
    /usr/local/airflow/dbt_venv/bin/pip install --no-cache-dir \
      --index-url https://pypi.org/simple \
      --only-binary=:all: \
      "dbt-databricks==1.12.4" \
      "pandas>=2.2.3"

# Side-by-side Fusion CLI (dbt v2). Cosmos does NOT use this venv yet.
# Docs: https://docs.getdbt.com/docs/local/install-dbt
RUN python -m venv /usr/local/airflow/dbt_v2_venv && \
    /usr/local/airflow/dbt_v2_venv/bin/pip install --upgrade pip && \
    /usr/local/airflow/dbt_v2_venv/bin/pip install --no-cache-dir "dbt" || \
    (echo "NOTE: Fusion pip install failed on this base image; use host: pip install dbt" \
     && true)
