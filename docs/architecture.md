# Architecture notes

See root [README.md](../README.md) for the mermaid diagrams and layer table.

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
