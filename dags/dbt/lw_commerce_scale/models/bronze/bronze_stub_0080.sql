-- synthetic scale stub; no external secrets
select
  80 as stub_id,
  cast(current_timestamp() as timestamp) as loaded_at,
  'bronze_stub_0080' as model_name
