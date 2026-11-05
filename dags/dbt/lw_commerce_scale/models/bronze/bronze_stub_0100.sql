-- synthetic scale stub; no external secrets
select
  100 as stub_id,
  cast(current_timestamp() as timestamp) as loaded_at,
  'bronze_stub_0100' as model_name
