-- Total gold.daily_revenue must reconcile with non-cancelled silver.order_items.
with g as (select coalesce(sum(revenue_eur), 0) as v from {{ ref('daily_revenue') }}),
     s as (select coalesce(round(sum(line_amount), 2), 0) as v
           from {{ ref('silver_order_items') }} where status != 'cancelled')
select g.v as gold_total, s.v as silver_total
from g cross join s
where abs(g.v - s.v) > 0.05 * greatest(1, (select count(*) from {{ ref('daily_revenue') }}))
