-- Orders should not be dated in the future (clock / parsing bug guard).
select order_id, created_at
from {{ ref('silver_orders') }}
where created_at > current_timestamp() + interval 1 day
