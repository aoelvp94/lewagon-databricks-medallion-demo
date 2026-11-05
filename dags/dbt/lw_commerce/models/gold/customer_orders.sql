{{ config(
    alias='customer_orders',
    tags=['gold', 'kpi']
) }}

/*
  Gold KPI — customer-level order metrics (LTV proxy, AOV, preferred country).
  UC table: {catalog}.gold.customer_orders
*/

with lines as (
    select *
    from {{ ref('silver_order_items') }}
    where status != 'cancelled'
),

agg as (
    select
        customer_id,
        count(distinct order_id) as orders,
        round(sum(line_amount), 2) as revenue_eur,
        sum(quantity) as units,
        min(order_date) as first_order_date,
        max(order_date) as last_order_date,
        count(distinct country) as countries
    from lines
    group by customer_id
),

top_country as (
    select
        customer_id,
        country as primary_country,
        row_number() over (
            partition by customer_id
            order by sum(line_amount) desc
        ) as rn
    from lines
    group by customer_id, country
)

select
    a.customer_id,
    a.orders,
    a.revenue_eur,
    a.units,
    round(a.revenue_eur / nullif(a.orders, 0), 2) as avg_order_value_eur,
    a.first_order_date,
    a.last_order_date,
    datediff(a.last_order_date, a.first_order_date) as customer_span_days,
    a.countries,
    tc.primary_country,
    current_timestamp() as gold_loaded_at
from agg a
left join top_country tc
    on a.customer_id = tc.customer_id and tc.rn = 1
