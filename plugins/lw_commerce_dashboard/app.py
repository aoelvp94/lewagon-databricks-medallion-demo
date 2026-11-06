"""FastAPI app mounted by the Airflow 3 API server at ``/lw-commerce``."""

from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, Query
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, JSONResponse, Response
from jinja2 import Environment, FileSystemLoader, Undefined, select_autoescape

from lw_commerce_dashboard.gold import GOLD_SCHEMA, QUERIES, get_snapshot, render_sql

URL_PREFIX = "/lw-commerce"
_HERE = Path(__file__).resolve().parent

try:
    # Airflow does NOT authenticate plugin apps; require a logged-in Airflow user
    # (JWT cookie set by the Airflow UI login, or an explicit Bearer token).
    from airflow.api_fastapi.core_api.security import get_user

    _deps = [Depends(get_user)]
except Exception:  # noqa: BLE001 — allows running the app standalone for tests
    _deps = []

app = FastAPI(
    title="LW Commerce gold dashboard",
    description="Airflow plugin page reading {catalog}.gold.* via Databricks SQL.",
    dependencies=_deps,
)

_env = Environment(
    loader=FileSystemLoader(_HERE / "templates"),
    autoescape=select_autoescape(["html"]),
)


def _fmt_num(value, digits: int = 0) -> str:
    if value is None or isinstance(value, Undefined):
        return "—"
    try:
        return f"{float(value):,.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


_env.filters["num"] = _fmt_num


@app.get("/", response_class=HTMLResponse)
async def dashboard(refresh: bool = Query(False)) -> HTMLResponse:
    snap = await run_in_threadpool(get_snapshot, refresh)
    headline = (snap.results.get("headline") or [{}])[0]
    customers = (snap.results.get("customers") or [{}])[0]
    daily = list(reversed(snap.results.get("daily") or []))
    max_daily = max((float(r.get("revenue_eur") or 0) for r in daily), default=0) or 1
    for r in daily:  # precompute bar height + short label (Decimal/date safe)
        r["_h"] = round(100 * float(r.get("revenue_eur") or 0) / max_daily, 1)
        d = r.get("order_date")
        r["_label"] = d.strftime("%d/%m") if hasattr(d, "strftime") else str(d)
    html = _env.get_template("dashboard.html").render(
        snap=snap,
        schema=GOLD_SCHEMA,
        headline=headline,
        customers=customers,
        daily=daily,
        max_daily=max_daily,
        by_country=snap.results.get("by_country") or [],
        top_products=snap.results.get("top_products") or [],
        fulfillment=snap.results.get("fulfillment") or [],
        top_customers=snap.results.get("top_customers") or [],
        queries={k: render_sql(k, snap.catalog) for k in QUERIES},
        url_prefix=URL_PREFIX,
    )
    return HTMLResponse(html)


@app.get("/api/kpis")
async def kpis_json(refresh: bool = Query(False)) -> JSONResponse:
    snap = await run_in_threadpool(get_snapshot, refresh)
    return JSONResponse(snap.to_json(), status_code=200 if not snap.fatal else 503)


@app.get("/static/icon.svg")
async def icon() -> Response:
    return Response((_HERE / "templates" / "icon.svg").read_text(), media_type="image/svg+xml")
