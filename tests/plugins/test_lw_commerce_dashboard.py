"""Smoke tests for the LW Commerce gold dashboard plugin (no warehouse needed)."""

from __future__ import annotations

import sys
from pathlib import Path

PLUGINS = Path(__file__).resolve().parents[2] / "plugins"
if str(PLUGINS) not in sys.path:
    sys.path.insert(0, str(PLUGINS))

from lw_commerce_dashboard import gold  # noqa: E402

GOLD_TABLES = {"daily_revenue", "top_products", "order_fulfillment", "customer_orders"}


def test_queries_only_read_unprefixed_gold_tables():
    assert {table for table, _ in gold.QUERIES.values()} == GOLD_TABLES
    for key in gold.QUERIES:
        sql = gold.render_sql(key, "workspace")
        assert "`workspace`.`gold`." in sql
        assert "gold_" not in sql.replace("gold_loaded_at", "")


def test_rejects_unsafe_catalog():
    try:
        gold.fq_gold("workspace`; DROP", "daily_revenue")
    except ValueError:
        return
    raise AssertionError("unsafe identifier accepted")


def test_page_renders_without_credentials(monkeypatch):
    from fastapi.testclient import TestClient

    from lw_commerce_dashboard.app import _deps, app

    for var in ("DATABRICKS_HOST", "DATABRICKS_HTTP_PATH", "DATABRICKS_TOKEN"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(gold, "fetch_gold", lambda: gold.GoldSnapshot(fatal="Missing Databricks settings"))
    for dep in _deps:
        app.dependency_overrides[dep.dependency] = lambda: None
    try:
        resp = TestClient(app).get("/?refresh=1")
    finally:
        app.dependency_overrides.clear()
    assert resp.status_code == 200
    assert "Can't reach the Databricks SQL Warehouse" in resp.text


def test_plugin_registers_nav_entry():
    import lw_commerce_dashboard_plugin as plugin_mod

    plugin = plugin_mod.LWCommerceDashboardPlugin
    assert plugin.fastapi_apps[0]["url_prefix"] == "/lw-commerce"
    view = plugin.external_views[0]
    assert view["name"] == "LW Commerce KPIs"
    assert view["url_route"] == "lw-commerce-kpis"
