select
  stub_id,
  loaded_at,
  model_name,
  stub_id * 10 as stub_metric
from {{ ref('bronze_stub_0009') }}
