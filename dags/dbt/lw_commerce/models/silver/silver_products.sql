{{ config(
    alias='products',
    tags=['silver']
) }}

select
    product_id,
    name as product_name,
    category,
    unit_price,
    currency,
    updated_at,
    source_batch_id,
    source_ingested_at,
    current_timestamp() as silver_loaded_at
from {{ ref('bronze_products') }}
where unit_price > 0
