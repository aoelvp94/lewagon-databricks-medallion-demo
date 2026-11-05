{{ config(
    alias='gold_top_products',
    tags=['gold', 'kpi']
) }}

/*
  Gold KPI — product ranking by revenue and units sold.
*/

select
    product_id,
    product_name,
    category,
    sum(quantity) as units_sold,
    round(sum(line_amount), 2) as revenue_eur,
    count(distinct order_id) as orders,
    count(distinct customer_id) as customers,
    current_timestamp() as gold_loaded_at
from {{ ref('silver_order_items') }}
where status != 'cancelled'
group by product_id, product_name, category
