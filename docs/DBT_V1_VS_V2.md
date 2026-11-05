# dbt Core 1.x vs dbt v2 (Fusion) on Databricks SQL

This repo keeps **three public refs**:

| Ref | Purpose |
|-----|---------|
| `main` | Teaching medallion demo — **dbt-databricks 1.12** (Core 1.x) in the Astro `dbt_venv` |
| `dbt-v1` | Same demo with an explicit Core 1.x pin + notes |
| `dbt-v2` | Docs + recipes for **dbt v2 / Fusion** against Databricks SQL |

## Install paths

### Core 1.x (what `main` / `dbt-v1` ship in Docker)

```bash
python -m venv dbt_venv
dbt_venv/bin/pip install 'dbt-databricks==1.12.4'
```

Astro image (`Dockerfile`) installs that pin into `/usr/local/airflow/dbt_venv` for Cosmos local execution.

On 1.12 you can trial the Rust parser without leaving Core:

```bash
dbt parse --use-v2-parser
dbt compile --use-v2-parser   # needs warehouse creds
```

### dbt v2 / Fusion

```bash
python -m pip install dbt          # Fusion distribution (recommended v2)
# adapter drivers download on first run (Databricks supported)
dbt --version
```

Docs: [Install dbt](https://docs.getdbt.com/docs/local/install-dbt), [Upgrading to v2](https://docs.getdbt.com/docs/dbt-versions/core-upgrade/upgrading-to-v2), [Databricks setup](https://docs.getdbt.com/docs/local/connect-data-platform/databricks-setup).

Profiles still use `type: databricks` with `host` / `http_path` / `token` (or OAuth). Keep secrets in `.env` — never commit them.

## Cosmos + Airflow

**Astronomer Cosmos** today expects a classic Python **dbt-core + adapter** virtualenv (`DbtTaskGroup` + `DatabricksTokenProfileMapping`). On `dbt-v2` we therefore:

- Keep the Airflow/Cosmos path on **dbt-databricks 1.12** inside `dbt_venv` so the teaching DAG still runs under Astro.
- Run **Fusion / `dbt` CLI** side-by-side for local parse/compile/docs benchmarks (`just bench-v2` on that branch).

If/when Cosmos documents first-class Fusion execution, collapse the two paths.

## When v2 matters

- Large projects (hundreds–thousands of nodes): faster parse/compile, stricter validation, Docs v2, static analysis.
- Migration rehearsal via `--use-v2-parser` on 1.12.

## When v2 does **not** matter much

- This classroom medallion (~10 models): warehouse SQL time and Genie demos dominate; parser differences are hard to feel.
- Use `bench/run_bench.sh` on `lw_commerce_scale` (~750 models) to make the gap visible.

## Safety

Never commit `.env`, filled `airflow_settings.yaml`, `*.tfvars`, or PATs. Examples use `REPLACE_ME_*` / `dapi...` placeholders only.
