# dbt parse/compile harness

Compares the tiny teaching project (`dags/dbt/lw_commerce`, ~10 models) with a synthetic scale project (`dags/dbt/lw_commerce_scale`, ~750 models).

## Regenerate scale DAG

```bash
python bench/generate_scale_project.py --per-layer 250   # 750 models
python bench/generate_scale_project.py --per-layer 333   # ~999 models
```

Generated SQL uses only constants and `ref()` — no tokens or hosts.

## Run timings

```bash
# Core 1.12 / dbt-databricks (branch dbt-v1 or main Astro dbt_venv)
export DBT_BIN=/usr/local/airflow/dbt_venv/bin/dbt   # or: python -m pip install 'dbt-databricks==1.12.4'
./bench/run_bench.sh

# Optional: Fusion / dbt v2 binary (branch dbt-v2)
export DBT_BIN=dbt   # after: python -m pip install dbt && dbt --version
./bench/run_bench.sh
```

`compile` needs `DATABRICKS_*` in the environment; the script never prints those values. Results land in `bench/results/` (gitignored).

## What the numbers mean

| Workload | Why it matters |
|----------|----------------|
| Tiny teaching DAG | Warehouse runtime and pedagogy dominate; parser speed is noise. |
| Scale (~500–1000 nodes) | `dbt parse` / `dbt compile` / docs generation dominate local feedback loops. |
| `--use-v2-parser` on 1.12 | Opt-in Rust parser compatibility check before full v2/Fusion migrate. |

See [docs/DBT_V1_VS_V2.md](../docs/DBT_V1_VS_V2.md).

## Sample timings (box, 2026-11-05 Europe/Amsterdam)

Measured with `dbt-databricks==1.12.4` / Core 1.12.0, parse only (no warehouse):

| Project | models | `dbt parse` | `dbt parse --use-v2-parser` |
|---------|-------:|------------:|----------------------------:|
| `lw_commerce` (teaching) | 10 | ~4.9s | ~4.5s |
| `lw_commerce_scale` | 750 | ~6.0s | ~4.4s |

Cold start dominates the tiny project; the scale project shows a clearer win for `--use-v2-parser`. Re-run locally with `./bench/run_bench.sh`. Set `BENCH_COMPILE=1` plus real `DATABRICKS_*` for compile timings.
