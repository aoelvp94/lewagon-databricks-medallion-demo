#!/usr/bin/env python3
"""CLI helpers for warehouse KPI / count checks (used by just recipes)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from include.databricks_client import catalog_name, databricks_connection, fetch_dicts, fq  # noqa: E402


def cmd_ping() -> int:
    with databricks_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
    print(f"ok catalog={catalog_name()}")
    return 0


def cmd_kpis() -> int:
    tables = [
        "daily_revenue",
        "top_products",
        "order_fulfillment",
        "customer_orders",
    ]
    for table in tables:
        name = fq("gold", table)
        print(f"-- {name}")
        for row in fetch_dicts(f"SELECT * FROM {name} LIMIT 10"):
            print(row)
    return 0


def cmd_counts() -> int:
    catalog = catalog_name()
    relations = [
        ("raw", "products_ingest"),
        ("raw", "orders_ingest"),
        ("bronze", "products"),
        ("bronze", "orders"),
        ("bronze", "order_items"),
        ("silver", "products"),
        ("silver", "orders"),
        ("silver", "order_items"),
        ("gold", "daily_revenue"),
        ("gold", "top_products"),
        ("gold", "order_fulfillment"),
        ("gold", "customer_orders"),
    ]
    with databricks_connection() as conn:
        with conn.cursor() as cur:
            for schema, table in relations:
                name = f"{catalog}.{schema}.{table}"
                try:
                    cur.execute(f"SELECT count(*) FROM `{catalog}`.`{schema}`.`{table}`")
                    count = cur.fetchone()[0]
                    print(f"{name}\t{count}")
                except Exception as exc:  # noqa: BLE001
                    print(f"{name}\tERROR: {exc}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="LW Commerce Databricks warehouse CLI")
    parser.add_argument("command", choices=["ping", "kpis", "counts"])
    args = parser.parse_args()
    if args.command == "ping":
        return cmd_ping()
    if args.command == "kpis":
        return cmd_kpis()
    return cmd_counts()


if __name__ == "__main__":
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    raise SystemExit(main())
