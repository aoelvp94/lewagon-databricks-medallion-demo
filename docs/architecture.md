# Architecture notes

See root [README.md](../README.md) for the mermaid diagrams and layer table, [STUDENT_GUIDE.md](STUDENT_GUIDE.md) for the step-by-step explanation, and [LINEAGE.md](LINEAGE.md) for table lineage + dbt docs.

## Ingest path (teachable on Free Edition)

`ingest_bronze_http` (Airflow TaskFlow) → `include.lw_commerce_ingest.ingest_lw_commerce_api`:

1. `CREATE SCHEMA/TABLE IF NOT EXISTS` via `include/sql/init_warehouse.sql`
2. `GET /v1/products` + paginated `GET /v1/orders` with `X-API-Key`
3. Multi-row `INSERT` into `raw.products_ingest` / `raw.orders_ingest` (`payload` STRING JSON)
4. On API failure → fixtures under `include/data/`

Optional legacy DLT notebook (not used by the DAG): `notebooks/optional/dlt_bronze_ingest_reference.py`.

## Cosmos

`DatabricksTokenProfileMapping(conn_id="databricks_sql")` + three `DbtTaskGroup`s
selected by `path:models/{bronze,silver,gold}` so the Airflow graph shows medallion layers.

## Table naming

Unity Catalog uses **schema = layer** and **unprefixed table names**:

- `workspace.bronze.products` (not `bronze.bronze_products`)
- `workspace.silver.orders`
- `workspace.gold.daily_revenue` (not `gold.gold_daily_revenue`)

dbt model IDs for bronze/silver keep a layer prefix (`bronze_products`, `silver_products`) so names stay unique in one project; each model sets `alias:` to the unprefixed UC table name. Gold model files are already unprefixed (`daily_revenue.sql`, …).
