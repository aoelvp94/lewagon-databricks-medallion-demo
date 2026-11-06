"""Gold-layer queries for the LW Commerce dashboard.

Reuses ``include/databricks_client.py`` so the dashboard resolves credentials
exactly like the DAG: Airflow connection ``databricks_sql`` first, then
``DATABRICKS_HOST`` / ``DATABRICKS_HTTP_PATH`` / ``DATABRICKS_TOKEN`` /
``DATABRICKS_CATALOG`` env vars (set by docker-compose.override.yml).
"""

from __future__ import annotations

import os
import re
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

# include/ lives in AIRFLOW_HOME (/usr/local/airflow on Astro); make it importable
# from the API server process the same way DAGs see it.
_AIRFLOW_HOME = os.environ.get("AIRFLOW_HOME") or str(Path(__file__).resolve().parents[2])
if _AIRFLOW_HOME not in sys.path:
    sys.path.insert(0, _AIRFLOW_HOME)

GOLD_SCHEMA = "gold"
_IDENT = re.compile(r"^[A-Za-z0-9_\-]+$")

# Each query reads ONE gold table. {t} is replaced with the fully-qualified name.
QUERIES: dict[str, tuple[str, str]] = {
    # key: (gold table, SQL)
    "headline": (
        "daily_revenue",
        """
        SELECT
          ROUND(SUM(revenue_eur), 2)                                  AS revenue_eur,
          SUM(orders)                                                  AS orders,
          ROUND(SUM(revenue_eur) / NULLIF(SUM(orders), 0), 2)          AS avg_order_value_eur,
          COUNT(DISTINCT country)                                      AS countries,
          MIN(order_date)                                              AS first_order_date,
          MAX(order_date)                                              AS last_order_date,
          MAX(gold_loaded_at)                                          AS gold_loaded_at
        FROM {t}
        """,
    ),
    "customers": (
        "customer_orders",
        """
        SELECT
          COUNT(*)                                                     AS customers,
          ROUND(AVG(revenue_eur), 2)                                   AS avg_revenue_per_customer_eur,
          ROUND(100.0 * AVG(CASE WHEN orders > 1 THEN 1 ELSE 0 END), 1) AS repeat_customer_pct
        FROM {t}
        """,
    ),
    "daily": (
        "daily_revenue",
        """
        SELECT order_date,
               ROUND(SUM(revenue_eur), 2) AS revenue_eur,
               SUM(orders)                AS orders
        FROM {t}
        GROUP BY order_date
        ORDER BY order_date DESC
        LIMIT 14
        """,
    ),
    "by_country": (
        "daily_revenue",
        """
        SELECT country,
               ROUND(SUM(revenue_eur), 2)                         AS revenue_eur,
               SUM(orders)                                         AS orders,
               ROUND(SUM(revenue_eur) / NULLIF(SUM(orders), 0), 2) AS avg_order_value_eur
        FROM {t}
        GROUP BY country
        ORDER BY revenue_eur DESC
        """,
    ),
    "top_products": (
        "top_products",
        """
        SELECT product_name, category, units_sold, revenue_eur, orders
        FROM {t}
        ORDER BY revenue_eur DESC
        LIMIT 10
        """,
    ),
    "fulfillment": (
        "order_fulfillment",
        """
        SELECT status,
               SUM(order_count)                                                AS order_count,
               ROUND(100.0 * SUM(order_count) / SUM(SUM(order_count)) OVER (), 1) AS pct
        FROM {t}
        GROUP BY status
        ORDER BY CASE status
                   WHEN 'created' THEN 1 WHEN 'paid' THEN 2 WHEN 'shipped' THEN 3
                   WHEN 'delivered' THEN 4 WHEN 'cancelled' THEN 5 ELSE 6 END
        """,
    ),
    "top_customers": (
        "customer_orders",
        """
        SELECT customer_id, primary_country, orders, revenue_eur, avg_order_value_eur, last_order_date
        FROM {t}
        ORDER BY revenue_eur DESC
        LIMIT 10
        """,
    ),
}


@dataclass
class GoldSnapshot:
    catalog: str = "workspace"
    fetched_at: datetime = field(default_factory=datetime.now)
    elapsed_s: float = 0.0
    fatal: str | None = None  # credentials / connection problem
    results: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)  # per-query (e.g. table missing)

    @property
    def is_empty(self) -> bool:
        headline = (self.results.get("headline") or [{}])[0]
        return not self.fatal and not headline.get("orders")

    def to_json(self) -> dict[str, Any]:
        return {
            "catalog": self.catalog,
            "schema": GOLD_SCHEMA,
            "fetched_at": self.fetched_at.isoformat(timespec="seconds"),
            "elapsed_s": round(self.elapsed_s, 2),
            "fatal": self.fatal,
            "errors": self.errors,
            "results": {k: [{c: _jsonable(v) for c, v in row.items()} for row in rows]
                        for k, rows in self.results.items()},
            "queries": {k: render_sql(k, self.catalog) for k in QUERIES},
        }


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _short_error(exc: BaseException) -> str:
    text = str(exc).strip().splitlines()[0] if str(exc).strip() else type(exc).__name__
    if "TABLE_OR_VIEW_NOT_FOUND" in str(exc):
        text = "TABLE_OR_VIEW_NOT_FOUND — run the lw_commerce_lakehouse DAG to build gold."
    return text[:300]


def fq_gold(catalog: str, table: str) -> str:
    if not _IDENT.match(catalog) or not _IDENT.match(table):
        raise ValueError(f"Unsafe identifier: {catalog}.{table}")
    return f"`{catalog}`.`{GOLD_SCHEMA}`.`{table}`"


def render_sql(key: str, catalog: str) -> str:
    table, sql = QUERIES[key]
    return " ".join(sql.format(t=fq_gold(catalog, table)).split())


def fetch_gold() -> GoldSnapshot:
    """Run every dashboard query on one Databricks SQL connection."""
    started = time.monotonic()
    snap = GoldSnapshot(catalog=os.environ.get("DATABRICKS_CATALOG") or "workspace")
    try:
        from include.databricks_client import databricks_connection, databricks_settings

        snap.catalog = databricks_settings()["catalog"]
        with databricks_connection() as conn:
            with conn.cursor() as cur:
                for key in QUERIES:
                    try:
                        cur.execute(render_sql(key, snap.catalog))
                        cols = [d[0] for d in (cur.description or [])]
                        snap.results[key] = [dict(zip(cols, row)) for row in cur.fetchall()]
                    except Exception as exc:  # noqa: BLE001 — show per-section error
                        snap.errors[key] = _short_error(exc)
    except Exception as exc:  # noqa: BLE001 — missing creds / warehouse unreachable
        snap.fatal = _short_error(exc)
    snap.elapsed_s = time.monotonic() - started
    return snap


# Small TTL cache: a page refresh must not wake the SQL warehouse every time.
_CACHE_TTL_S = int(os.environ.get("LW_DASHBOARD_CACHE_SECONDS", "60"))
_cache: dict[str, Any] = {"snap": None, "at": 0.0}
_lock = threading.Lock()


def get_snapshot(refresh: bool = False) -> GoldSnapshot:
    with _lock:
        snap = _cache["snap"]
        fresh = snap is not None and (time.monotonic() - _cache["at"]) < _CACHE_TTL_S
        if refresh or not fresh or snap.fatal:
            snap = fetch_gold()
            _cache.update(snap=snap, at=time.monotonic())
        return snap
