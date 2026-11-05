{{ config(
    alias='order_items',
    tags=['silver']
) }}

select
    i.order_id,
    i.product_id,
    i.quantity,
    i.unit_price,
    i.line_amount,
    o.customer_id,
    o.country,
    o.status,
    o.created_at,
    o.order_date,
    p.product_name,
    p.category,
    current_timestamp() as silver_loaded_at
from {{ ref('bronze_order_items') }} i
inner join {{ ref('silver_orders') }} o
    on i.order_id = o.order_id
left join {{ ref('silver_products') }} p
    on i.product_id = p.product_id
where i.quantity > 0
  and i.unit_price > 0
