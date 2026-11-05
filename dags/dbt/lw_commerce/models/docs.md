{% docs __overview__ %}
# LW Commerce · Medallion lakehouse (Le Wagon demo)

Invented **LW Commerce** FastAPI → Airflow (Astro) HTTP ingest → Databricks SQL Warehouse →
dbt (run by **Astronomer Cosmos**) → Unity Catalog medallion schemas.

| Layer (UC schema) | Tables | Purpose |
|---|---|---|
| `raw` | `products_ingest`, `orders_ingest` | Append-only API landing, `payload` is STRING JSON |
| `bronze` | `products`, `orders`, `order_items` | Flatten JSON, dedupe latest per key, explode order items |
| `silver` | `products`, `orders`, `order_items` | Clean, typed, enriched entities |
| `gold` | `daily_revenue`, `top_products`, `order_fulfillment`, `customer_orders` | KPIs for Genie / AI/BI |

Open the **lineage graph** (bottom-right button in this UI) to see `raw → bronze → silver → gold`.
Model IDs for bronze/silver keep a layer prefix (`bronze_products`) because dbt model names must be
unique; `alias` maps each one to the unprefixed UC table name (`bronze.products`).
{% enddocs %}

{% docs product_id %}Business key of a product from the LW Commerce API (e.g. `P-001`).{% enddocs %}
{% docs order_id %}Business key of an order from the LW Commerce API.{% enddocs %}
{% docs customer_id %}Customer identifier carried on each order.{% enddocs %}
{% docs country %}ISO-like country code where the order was placed.{% enddocs %}
{% docs order_status %}
Order lifecycle status. Silver normalises to lower-case; expected values:
`created`, `paid`, `shipped`, `delivered`, `cancelled`.
{% enddocs %}
{% docs unit_price %}Price per unit in EUR at the time of the record (must be > 0 in silver).{% enddocs %}
{% docs line_amount %}`quantity × unit_price`, rounded to 2 decimals (EUR).{% enddocs %}
{% docs source_batch_id %}Ingest batch that produced the winning (latest) raw row.{% enddocs %}
{% docs source_ingested_at %}Timestamp the winning raw row landed in `raw.*`.{% enddocs %}
{% docs loaded_at %}Timestamp when dbt (re)built this table.{% enddocs %}
{% docs revenue_eur %}Sum of `line_amount` for non-cancelled orders (EUR).{% enddocs %}
{% docs avg_order_value_eur %}Revenue divided by distinct orders (AOV, EUR).{% enddocs %}
{% docs dedupe_rule %}
Deduplication: `row_number()` over the business key ordered by `ingested_at desc, ingest_id desc`;
only rank 1 is kept, so re-ingesting the API is idempotent.
{% enddocs %}
