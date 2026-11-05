"""Deterministic seed data for the LW Commerce fake API."""
import random
from datetime import datetime, timedelta, timezone

SEED = 42
BASE = datetime(2026, 10, 1, tzinfo=timezone.utc)
CATEGORIES = ["books", "electronics", "coffee", "apparel", "stickers"]


def build_products(n: int = 25):
    rnd = random.Random(SEED)
    return [
        {
            "product_id": f"P{i:03d}",
            "name": f"LW {CATEGORIES[i % 5].title()} Item {i}",
            "category": CATEGORIES[i % 5],
            "unit_price": round(rnd.uniform(3, 250), 2),
            "currency": "EUR",
            "updated_at": (BASE + timedelta(hours=i)).isoformat(),
        }
        for i in range(1, n + 1)
    ]


def build_orders(products, n: int = 600):
    rnd = random.Random(SEED + 1)
    statuses = ["created", "paid", "shipped", "delivered", "cancelled"]
    countries = ["AR", "BR", "MX", "CL", "CO", "UY", "NL", "FR"]
    orders = []
    for i in range(1, n + 1):
        created = BASE + timedelta(minutes=rnd.randint(0, 60 * 24 * 30))
        items = []
        for p in rnd.sample(products, rnd.randint(1, 4)):
            items.append({"product_id": p["product_id"], "quantity": rnd.randint(1, 5),
                          "unit_price": p["unit_price"]})
        orders.append({
            "order_id": f"O{i:05d}",
            "customer_id": f"C{rnd.randint(1, 150):04d}",
            "country": rnd.choice(countries),
            "status": rnd.choice(statuses),
            "created_at": created.isoformat(),
            "updated_at": (created + timedelta(hours=rnd.randint(0, 72))).isoformat(),
            "items": items,
        })
    return sorted(orders, key=lambda o: o["updated_at"])


PRODUCTS = build_products()
ORDERS = build_orders(PRODUCTS)
