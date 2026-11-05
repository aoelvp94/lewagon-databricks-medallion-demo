# Branch `dbt-v1` — dbt Core 1.x pin

This branch is the teaching medallion demo with an **explicit Core 1.x** pin:

- Docker `dbt_venv`: `dbt-databricks==1.12.4` (see `Dockerfile`)
- Cosmos / Astro DAG path uses that venv only
- Optional: `dbt parse --use-v2-parser` to rehearse Fusion parser compatibility without leaving 1.12

Do **not** install the `dbt` (Fusion) PyPI package into the Astro `dbt_venv` on this branch — keep Core 1.x for Airflow reproducibility.

See [docs/DBT_V1_VS_V2.md](../docs/DBT_V1_VS_V2.md) and [`bench/`](../bench/).
