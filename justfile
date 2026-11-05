# LW Commerce — local Astro + Cosmos + dbt on Databricks SQL Warehouse
# Analytics warehouse is Databricks; Airflow metadata stays on Astro Postgres.
set shell := ["bash", "-eu", "-o", "pipefail", "-c"]
set dotenv-load := true

project := justfile_directory()
dag_id := "lw_commerce_lakehouse"
airflow_url := env_var_or_default("AIRFLOW_URL", "http://localhost:8080")
api_url := env_var_or_default("API_URL", "http://localhost:8000")

default:
    @just --list

# --- lifecycle ---------------------------------------------------------------

start:
    cd "{{ project }}" && astro dev start

stop:
    cd "{{ project }}" && astro dev stop

restart:
    cd "{{ project }}" && astro dev restart

kill:
    cd "{{ project }}" && astro dev kill

build:
    cd "{{ project }}" && astro dev build

reset: kill
    cd "{{ project }}" && astro dev start

# --- API (also started by docker-compose.override via `just start`) ----------

api:
    cd "{{ project }}/api" && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8000

api-docker:
    cd "{{ project }}/api" && docker compose up --build

smoke:
    curl -s "{{ api_url }}/health" && echo && curl -s -H "X-API-Key: ${API_KEY:-lewagon-demo}" "{{ api_url }}/v1/orders?page_size=2" | head -c 400 && echo

fixtures:
    cd "{{ project }}/api" && python export_samples.py
    cp "{{ project }}/api/sample_responses/products.json" "{{ project }}/include/data/sample_products.json"
    cp "{{ project }}/api/sample_responses/orders.json" "{{ project }}/include/data/sample_orders.json"

# --- observability -----------------------------------------------------------

logs *args:
    cd "{{ project }}" && astro dev logs {{ args }}

ps:
    cd "{{ project }}" && astro dev ps

parse:
    cd "{{ project }}" && astro dev parse

ui:
    open "{{ airflow_url }}" || xdg-open "{{ airflow_url }}" || true
    @echo "{{ airflow_url }}"

# --- pipeline ----------------------------------------------------------------

wait-dag:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "Waiting for DAG {{ dag_id }} to appear…"
    for _ in $(seq 1 60); do
      if cd "{{ project }}" && astro dev run dags list 2>/dev/null | rg -q "{{ dag_id }}"; then
        echo "Found {{ dag_id }}."
        exit 0
      fi
      sleep 2
    done
    echo "Timed out waiting for {{ dag_id }}" >&2
    exit 1

trigger: wait-dag
    cd "{{ project }}" && astro dev run dags unpause -y {{ dag_id }}
    cd "{{ project }}" && astro dev run dags trigger {{ dag_id }}
    @echo "Triggered {{ dag_id }}. UI: {{ airflow_url }}/dags/{{ dag_id }}"

runs:
    cd "{{ project }}" && astro dev run dags list-runs {{ dag_id }}

# --- warehouse / dbt ---------------------------------------------------------

warehouse_cli cmd:
    #!/usr/bin/env bash
    set -euo pipefail
    container="$(docker ps -q --filter 'name=lewagon-databricks-medallion-demo' --filter 'name=scheduler' | head -1)"
    if [[ -z "${container}" ]]; then
      # Fallback: any project-*scheduler* in this folder's compose project
      container="$(docker ps --format '{{.ID}} {{.Names}}' | awk '/scheduler/ && /lewagon|medallion/ {print $1; exit}')"
    fi
    if [[ -z "${container}" ]]; then
      echo "Scheduler container not running. Start with: just start" >&2
      exit 1
    fi
    docker exec -w /usr/local/airflow "${container}" python include/warehouse_cli.py {{ cmd }}

ping:
    just warehouse_cli ping

kpis:
    just warehouse_cli kpis

counts:
    just warehouse_cli counts

bash:
    cd "{{ project }}" && astro dev bash --scheduler

dbt-run *args:
    #!/usr/bin/env bash
    set -euo pipefail
    container="$(docker ps -q --filter 'name=lewagon-databricks-medallion-demo' --filter 'name=scheduler' | head -1)"
    if [[ -z "${container}" ]]; then
      container="$(docker ps --format '{{.ID}} {{.Names}}' | awk '/scheduler/ && /lewagon|medallion/ {print $1; exit}')"
    fi
    if [[ -z "${container}" ]]; then
      echo "Scheduler container not running. Start with: just start" >&2
      exit 1
    fi
    docker exec -w /usr/local/airflow "${container}" bash -lc \
      'source /usr/local/airflow/dbt_venv/bin/activate && cd /usr/local/airflow/dags/dbt/lw_commerce && dbt run --profiles-dir . {{ args }}'

# --- optional terraform (schemas only) ---------------------------------------

tf-init:
    cd "{{ project }}/terraform" && terraform init

tf-plan:
    cd "{{ project }}/terraform" && terraform plan

tf-apply:
    cd "{{ project }}/terraform" && terraform apply

# --- demo --------------------------------------------------------------------

demo: start
    @echo "Checking Databricks SQL Warehouse from Astro scheduler…"
    @if just ping; then \
      echo "Warehouse reachable."; \
    else \
      echo "Warehouse ping failed — fill .env + airflow_settings.yaml (see README), then retry: just ping"; \
      echo "Continuing to trigger the DAG anyway."; \
    fi
    just smoke || true
    just trigger
    @echo ""
    @echo "Airflow:  {{ airflow_url }}  (admin / admin)"
    @echo "API:      {{ api_url }}  (X-API-Key: $${API_KEY:-lewagon-demo})"
    @echo "Catalog:  $${DATABRICKS_CATALOG:-workspace} (raw / bronze / silver / gold)"
    @echo "Genie:    see docs/GENIE_DEMO.md after gold tables land"

# --- dbt bench (parse/compile; no secret echo) --------------------------------

bench:
    #!/usr/bin/env bash
    set -euo pipefail
    DBT_BIN="${DBT_BIN:-}"
    if [[ -z "${DBT_BIN}" ]]; then
      if [[ -x /usr/local/airflow/dbt_venv/bin/dbt ]]; then
        DBT_BIN=/usr/local/airflow/dbt_venv/bin/dbt
      else
        DBT_BIN="$(command -v dbt || true)"
      fi
    fi
    if [[ -z "${DBT_BIN}" ]]; then
      echo "No dbt binary found. Install dbt-databricks 1.12 or set DBT_BIN." >&2
      exit 1
    fi
    DBT_BIN="${DBT_BIN}" "{{ project }}/bench/run_bench.sh"

scale-gen per_layer="250":
    python3 "{{ project }}/bench/generate_scale_project.py" --per-layer {{ per_layer }}
