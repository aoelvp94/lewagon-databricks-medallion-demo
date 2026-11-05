{{ config(
    alias='order_items',
    tags=['bronze']
) }}

/*
  Bronze: explode order.items[] from the deduped bronze.orders payload.
  Grain: one row per array element (order line).
*/

with orders as (
    select
        order_id,
        items_payload,
        source_batch_id,
        source_ingested_at
    from {{ ref('bronze_orders') }}
),

parsed as (
    select
        order_id,
        from_json(
            get_json_object(items_payload, '$.items'),
            'array<struct<product_id:string,quantity:int,unit_price:double>>'
        ) as items,
        source_batch_id,
        source_ingested_at
    from orders
),

exploded as (
    select
        order_id,
        item.product_id as product_id,
        item.quantity as quantity,
        item.unit_price as unit_price,
        source_batch_id,
        source_ingested_at
    from parsed
    lateral view outer explode(items) e as item
)

select
    order_id,
    product_id,
    quantity,
    unit_price,
    round(cast(quantity as double) * unit_price, 2) as line_amount,
    source_batch_id,
    source_ingested_at,
    current_timestamp() as bronze_loaded_at
from exploded
where product_id is not null
