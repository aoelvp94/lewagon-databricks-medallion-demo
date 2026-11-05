#!/usr/bin/env python3
"""Generate a large lightweight dbt project for parse/compile benchmarks.

Creates fan-out bronze stubs plus dependent silver/gold models.
No warehouse secrets — SQL is synthetic constants only.
"""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "dags" / "dbt" / "lw_commerce_scale"


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--per-layer", type=int, default=250, help="models per bronze/silver/gold layer")
    args = p.parse_args()
    n = args.per_layer
    if n < 1:
        raise SystemExit("--per-layer must be >= 1")

    write(
        ROOT / "dbt_project.yml",
        f"""name: lw_commerce_scale
version: 1.0.0
config-version: 2
profile: lw_commerce_scale

model-paths: ["models"]
macro-paths: ["macros"]
clean-targets: ["target", "dbt_packages"]

models:
  lw_commerce_scale:
    bronze:
      +schema: bronze_scale
      +materialized: view
      +tags: ["bronze", "scale"]
    silver:
      +schema: silver_scale
      +materialized: view
      +tags: ["silver", "scale"]
    gold:
      +schema: gold_scale
      +materialized: view
      +tags: ["gold", "scale"]
""",
    )

    write(
        ROOT / "profiles.yml",
        """# Local CLI only. Tokens come from env — never hardcode.
lw_commerce_scale:
  target: dev
  outputs:
    dev:
      type: databricks
      host: "{{ env_var('DATABRICKS_HOST') }}"
      http_path: "{{ env_var('DATABRICKS_HTTP_PATH') }}"
      token: "{{ env_var('DATABRICKS_TOKEN') }}"
      catalog: "{{ env_var('DATABRICKS_CATALOG', 'workspace') }}"
      schema: "{{ env_var('DATABRICKS_SCHEMA', 'bronze_scale') }}"
      threads: 4
""",
    )

    write(
        ROOT / "macros" / "generate_schema_name.sql",
        """{% macro generate_schema_name(custom_schema_name, node) -%}
  {%- if custom_schema_name is none -%}
    {{ target.schema }}
  {%- else -%}
    {{ custom_schema_name | trim }}
  {%- endif -%}
{%- endmacro %}
""",
    )

    write(ROOT / ".gitignore", "target/\ndbt_packages/\nlogs/\n")

    for i in range(n):
        write(
            ROOT / "models" / "bronze" / f"bronze_stub_{i:04d}.sql",
            f"""-- synthetic scale stub; no external secrets
select
  {i} as stub_id,
  cast(current_timestamp() as timestamp) as loaded_at,
  'bronze_stub_{i:04d}' as model_name
""",
        )
        write(
            ROOT / "models" / "silver" / f"silver_stub_{i:04d}.sql",
            f"""select
  stub_id,
  loaded_at,
  model_name,
  stub_id * 10 as stub_metric
from {{{{ ref('bronze_stub_{i:04d}') }}}}
""",
        )
        write(
            ROOT / "models" / "gold" / f"gold_stub_{i:04d}.sql",
            f"""select
  stub_id,
  stub_metric,
  stub_metric + 1 as kpi_proxy
from {{{{ ref('silver_stub_{i:04d}') }}}}
""",
        )

    total = n * 3
    write(
        ROOT / "README.md",
        f"""# lw_commerce_scale

Synthetic fan-out project for **parse/compile** benchmarks (~{total} models: {n} per layer).

Regenerate:

```bash
python bench/generate_scale_project.py --per-layer {n}
```

SQL contains only constants / `ref()` — no hosts, tokens, or warehouse IDs.
""",
    )
    print(f"Wrote {total} models under {ROOT} ({n} per layer)")


if __name__ == "__main__":
    main()
