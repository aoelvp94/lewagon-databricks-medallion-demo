{{ config(
    alias='products',
    tags=['bronze', 'dedupe']
) }}

/*
  Bronze: flatten product JSON landing payload and keep one row per product_id.
  Prefer the newest ingest (latest ingested_at, then highest ingest_id).
*/

with flattened as (
    select
        ingest_id,
        batch_id,
        product_id,
        ingested_at,
        get_json_object(payload, '$.name') as name,
        get_json_object(payload, '$.category') as category,
        cast(get_json_object(payload, '$.unit_price') as double) as unit_price,
        get_json_object(payload, '$.currency') as currency,
        cast(get_json_object(payload, '$.updated_at') as timestamp) as updated_at
    from {{ source('raw', 'products_ingest') }}
),

ranked as (
    select
        *,
        row_number() over (
            partition by product_id
            order by ingested_at desc, ingest_id desc
        ) as _dedupe_rank
    from flattened
)

select
    product_id,
    name,
    category,
    unit_price,
    currency,
    updated_at,
    batch_id as source_batch_id,
    ingested_at as source_ingested_at,
    current_timestamp() as bronze_loaded_at
from ranked
where _dedupe_rank = 1
