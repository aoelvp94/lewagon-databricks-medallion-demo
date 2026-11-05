select
  stub_id,
  stub_metric,
  stub_metric + 1 as kpi_proxy
from {{ ref('silver_stub_0187') }}
