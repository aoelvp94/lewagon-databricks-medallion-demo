"""LW Commerce - invented API for the Le Wagon Databricks medallion demo."""
import os
from datetime import datetime
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query

from .data import ORDERS, PRODUCTS

API_KEY = os.getenv("API_KEY", "lewagon-demo")
app = FastAPI(title="LW Commerce API", version="1.0.0")


def check_key(x_api_key: Optional[str] = Header(default=None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="invalid or missing X-API-Key")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/v1/products", dependencies=[Depends(check_key)])
def products():
    return {"data": PRODUCTS, "count": len(PRODUCTS)}


@app.get("/v1/orders", dependencies=[Depends(check_key)])
def orders(updated_since: Optional[datetime] = None,
           page: int = Query(1, ge=1),
           page_size: int = Query(100, ge=1, le=500)):
    rows = ORDERS
    if updated_since:
        if updated_since.tzinfo is None:
            raise HTTPException(422, "updated_since must include timezone, e.g. 2026-10-10T00:00:00Z")
        rows = [o for o in rows if datetime.fromisoformat(o["updated_at"]) > updated_since]
    start = (page - 1) * page_size
    chunk = rows[start:start + page_size]
    return {"data": chunk, "page": page, "page_size": page_size, "total": len(rows),
            "next_page": page + 1 if start + page_size < len(rows) else None}
