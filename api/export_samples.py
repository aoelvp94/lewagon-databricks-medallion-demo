"""Regenerate api/sample_responses/ fixtures (used by bronze when api_base_url is empty)."""
import json, pathlib
from app.data import ORDERS, PRODUCTS

out = pathlib.Path(__file__).parent / "sample_responses"
out.mkdir(exist_ok=True)
(out / "products.json").write_text(json.dumps({"data": PRODUCTS, "count": len(PRODUCTS)}, indent=1))
(out / "orders.json").write_text(json.dumps({"data": ORDERS, "total": len(ORDERS)}, indent=1))
print("wrote", out)
