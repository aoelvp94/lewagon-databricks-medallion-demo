-- Per country, status shares in gold.order_fulfillment must add up to ~100%.
select country, sum(pct_of_country) as total_pct
from {{ ref('order_fulfillment') }}
group by country
having abs(sum(pct_of_country) - 100) > 1
