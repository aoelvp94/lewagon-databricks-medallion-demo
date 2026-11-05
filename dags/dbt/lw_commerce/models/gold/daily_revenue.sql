{{ config(
    alias='daily_revenue',
    tags=['gold', 'kpi']
) }}

/*
  Gold KPI — daily revenue by country (excludes cancelled orders).
  UC table: {catalog}.gold.daily_revenue
*/

select
    order_date,
    country,
    round(sum(line_amount), 2) as revenue_eur,
    count(distinct order_id) as orders,
    count(distinct customer_id) as customers,
    round(sum(line_amount) / nullif(count(distinct order_id), 0), 2) as avg_order_value_eur,
    current_timestamp() as gold_loaded_at
from {{ ref('silver_order_items') }}
where status != 'cancelled'
group by order_date, country
