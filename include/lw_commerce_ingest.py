"""Helpers for LW Commerce API ingestion into Databricks SQL Warehouse."""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from include.databricks_client import catalog_name, databricks_connection

logger = logging.getLogger(__name__)

FIXTURE_PRODUCTS = Path(__file__).parent / "data" / "sample_products.json"
FIXTURE_ORDERS = Path(__file__).parent / "data" / "sample_orders.json"
INIT_SQL_PATH = Path(__file__).parent / "sql" / "init_warehouse.sql"


def api_base_url() -> str:
    """Public/local URL of the invented LW Commerce API."""
    return (os.environ.get("API_BASE_URL") or "http://api:8000").rstrip("/")


def api_key() -> str:
    return os.environ.get("API_KEY") or "lewagon-demo"


def ensure_landing_table() -> None:
    """Idempotent Unity Catalog schemas + raw landing tables."""
    catalog = catalog_name()
    template = INIT_SQL_PATH.read_text()
    sql = template.replace("${catalog}", catalog)
    cleaned: list[str] = []
    for part in sql.split(";"):
        lines = [
            line
            for line in part.splitlines()
            if line.strip() and not line.strip().startswith("--")
        ]
        if lines:
            cleaned.append("\n".join(lines))

    with databricks_connection() as conn:
        with conn.cursor() as cur:
            for statement in cleaned:
                cur.execute(statement)
    logger.info("Ensured landing schemas/tables in catalog %s", catalog)


def _get_json(path: str) -> dict[str, Any]:
    url = f"{api_base_url()}{path}"
    response = requests.get(
        url,
        timeout=30,
        headers={
            "Accept": "application/json",
            "X-API-Key": api_key(),
            "User-Agent": "lewagon-databricks-medallion-demo/1.0",
        },
    )
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise ValueError(f"Unexpected API payload type: {type(data)}")
    return data


def fetch_products() -> list[dict[str, Any]]:
    body = _get_json("/v1/products")
    rows = body.get("data") or []
    if not isinstance(rows, list):
        raise ValueError("products.data must be a list")
    return rows


def fetch_orders(max_pages: int = 20, page_size: int = 200) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    page: int | None = 1
    pages = 0
    while page and pages < max_pages:
        body = _get_json(f"/v1/orders?page={page}&page_size={page_size}")
        chunk = body.get("data") or []
        if not isinstance(chunk, list):
            raise ValueError("orders.data must be a list")
        rows.extend(chunk)
        page = body.get("next_page")
        pages += 1
        logger.info("Fetched orders page %s (%s rows, total=%s)", pages, len(chunk), len(rows))
    return rows


def load_fixture_products() -> list[dict[str, Any]]:
    data = json.loads(FIXTURE_PRODUCTS.read_text())
    rows = data.get("data") if isinstance(data, dict) else data
    if not isinstance(rows, list) or not rows:
        raise ValueError("Product fixture must contain a non-empty data list")
    return rows


def load_fixture_orders() -> list[dict[str, Any]]:
    data = json.loads(FIXTURE_ORDERS.read_text())
    rows = data.get("data") if isinstance(data, dict) else data
    if not isinstance(rows, list) or not rows:
        raise ValueError("Order fixture must contain a non-empty data list")
    return rows


def _escape_sql_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "''")


def _rows_from_records(
    records: list[dict[str, Any]],
    id_field: str,
    batch_id: str,
    ingested_at: datetime,
) -> list[tuple[str, str, str, str, datetime]]:
    rows: list[tuple[str, str, str, str, datetime]] = []
    for record in records:
        entity_id = str(record.get(id_field) or "").strip()
        if not entity_id:
            continue
        rows.append(
            (
                str(uuid.uuid4()),
                batch_id,
                entity_id,
                json.dumps(record),
                ingested_at,
            )
        )
    return rows


def _insert_rows(
    table: str,
    id_column: str,
    rows: list[tuple[str, str, str, str, datetime]],
    catalog: str,
    chunk_size: int = 40,
) -> None:
    """
    Multi-row INSERT per chunk.

    Databricks SQL connector's executemany() issues one statement per row
    (~1–2s RTT each) which makes a few hundred rows feel stuck.
    """
    fq_table = f"`{catalog}`.`raw`.`{table}`"
    with databricks_connection() as conn:
        with conn.cursor() as cur:
            for start in range(0, len(rows), chunk_size):
                chunk = rows[start : start + chunk_size]
                value_sql: list[str] = []
                for ingest_id, batch_id, entity_id, payload, ingested_at in chunk:
                    ts = ingested_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                    value_sql.append(
                        "("
                        f"'{_escape_sql_string(ingest_id)}', "
                        f"'{_escape_sql_string(batch_id)}', "
                        f"'{_escape_sql_string(entity_id)}', "
                        f"'{_escape_sql_string(payload)}', "
                        f"TIMESTAMP '{ts}'"
                        ")"
                    )
                sql = (
                    f"INSERT INTO {fq_table} "
                    f"(ingest_id, batch_id, {id_column}, payload, ingested_at) VALUES "
                    + ", ".join(value_sql)
                )
                cur.execute(sql)
                logger.info(
                    "Inserted %s rows %s–%s of %s",
                    table,
                    start + 1,
                    start + len(chunk),
                    len(rows),
                )


def ingest_lw_commerce_api(max_order_pages: int = 20) -> dict[str, Any]:
    """
    Pull products + paginated orders from the invented LW Commerce API and
    append them to raw.products_ingest / raw.orders_ingest.

    Intentionally append-only so bronze can demonstrate deduplication across
    re-runs. Falls back to include/data/sample_*.json when the live API is
    unreachable (offline / no docker api service).
    """
    ensure_landing_table()
    catalog = catalog_name()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    batch_id = f"lw_{stamp}_{uuid.uuid4().hex[:8]}"
    ingested_at = datetime.now(timezone.utc)
    source = "lw_commerce_api"

    try:
        products = fetch_products()
        orders = fetch_orders(max_pages=max_order_pages)
        logger.info(
            "Live API OK base=%s products=%s orders=%s",
            api_base_url(),
            len(products),
            len(orders),
        )
    except Exception as exc:  # noqa: BLE001 — demo resilience
        logger.warning("Live API ingest failed (%s); loading local fixtures", exc)
        source = "fixture"
        batch_id = f"fixture_{stamp}_{uuid.uuid4().hex[:8]}"
        products = load_fixture_products()
        orders = load_fixture_orders()

    product_rows = _rows_from_records(products, "product_id", batch_id, ingested_at)
    order_rows = _rows_from_records(orders, "order_id", batch_id, ingested_at)
    if not product_rows or not order_rows:
        raise RuntimeError("No product/order records available from API or fixture")

    _insert_rows("products_ingest", "product_id", product_rows, catalog)
    _insert_rows("orders_ingest", "order_id", order_rows, catalog)

    summary = {
        "batch_id": batch_id,
        "source": source,
        "catalog": catalog,
        "api_base_url": api_base_url() if source == "lw_commerce_api" else None,
        "products_inserted": len(product_rows),
        "orders_inserted": len(order_rows),
        "ingested_at": ingested_at.isoformat(),
    }
    logger.info("Ingest complete: %s", summary)
    return summary
