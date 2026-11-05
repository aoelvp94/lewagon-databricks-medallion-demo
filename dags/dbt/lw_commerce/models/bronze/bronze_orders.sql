{{ config(
    alias='orders',
    tags=['bronze', 'dedupe']
) }}

/*
  Bronze: flatten order header fields from STRING JSON; keep latest per order_id.
  Line items live in bronze_order_items (exploded from the same payload).
*/

with flattened as (
    select
        ingest_id,
        batch_id,
        order_id,
        ingested_at,
        get_json_object(payload, '$.customer_id') as customer_id,
        get_json_object(payload, '$.country') as country,
        get_json_object(payload, '$.status') as status,
        cast(get_json_object(payload, '$.created_at') as timestamp) as created_at,
        cast(get_json_object(payload, '$.updated_at') as timestamp) as updated_at,
        payload
    from {{ source('raw', 'orders_ingest') }}
),

ranked as (
    select
        *,
        row_number() over (
            partition by order_id
            order by ingested_at desc, ingest_id desc
        ) as _dedupe_rank
    from flattened
)

select
    order_id,
    customer_id,
    country,
    status,
    created_at,
    updated_at,
    payload as items_payload,
    batch_id as source_batch_id,
    ingested_at as source_ingested_at,
    current_timestamp() as bronze_loaded_at
from ranked
where _dedupe_rank = 1
