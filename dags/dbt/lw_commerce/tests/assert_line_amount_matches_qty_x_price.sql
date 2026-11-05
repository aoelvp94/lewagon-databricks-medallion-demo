-- Silver line_amount must equal quantity × unit_price (rounded to cents).
select order_id, product_id, quantity, unit_price, line_amount
from {{ ref('silver_order_items') }}
where abs(line_amount - round(quantity * unit_price, 2)) > 0.01
