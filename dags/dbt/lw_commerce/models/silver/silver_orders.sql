{{ config(
    alias='orders',
    tags=['silver']
) }}

select
    order_id,
    customer_id,
    country,
    lower(trim(status)) as status,
    created_at,
    updated_at,
    date(created_at) as order_date,
    source_batch_id,
    source_ingested_at,
    current_timestamp() as silver_loaded_at
from {{ ref('bronze_orders') }}
where order_id is not null
