-- Databricks / Unity Catalog bootstrap for LW Commerce medallion demo
-- Run via include.lw_commerce_ingest.ensure_landing_table() (catalog substituted at runtime).
-- Schemas: raw (landing) + bronze / silver / gold (dbt).

CREATE SCHEMA IF NOT EXISTS ${catalog}.raw;
CREATE SCHEMA IF NOT EXISTS ${catalog}.bronze;
CREATE SCHEMA IF NOT EXISTS ${catalog}.silver;
CREATE SCHEMA IF NOT EXISTS ${catalog}.gold;

CREATE TABLE IF NOT EXISTS ${catalog}.raw.products_ingest (
    ingest_id   STRING    NOT NULL,
    batch_id    STRING    NOT NULL,
    product_id  STRING    NOT NULL,
    payload     STRING    NOT NULL,
    ingested_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS ${catalog}.raw.orders_ingest (
    ingest_id   STRING    NOT NULL,
    batch_id    STRING    NOT NULL,
    order_id    STRING    NOT NULL,
    payload     STRING    NOT NULL,
    ingested_at TIMESTAMP NOT NULL
);
