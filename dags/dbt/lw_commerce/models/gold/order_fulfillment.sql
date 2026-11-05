{{ config(
    alias='order_fulfillment',
    tags=['gold', 'kpi']
) }}

/*
  Gold KPI — order status funnel by country (created → paid → shipped → delivered / cancelled).
  UC table: {catalog}.gold.order_fulfillment
*/

select
    country,
    status,
    count(*) as order_count,
    count(distinct customer_id) as customers,
    round(100.0 * count(*) / sum(count(*)) over (partition by country), 1) as pct_of_country,
    current_timestamp() as gold_loaded_at
from {{ ref('silver_orders') }}
group by country, status
