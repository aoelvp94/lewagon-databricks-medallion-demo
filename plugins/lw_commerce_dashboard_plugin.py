"""LW Commerce KPIs — Airflow 3 UI plugin (gold dashboard).

Teaching point: Airflow ``plugins/`` can host custom web pages inside the Airflow UI.

Airflow 3 replaced Flask-AppBuilder ``appbuilder_views`` / ``appbuilder_menu_items``
with two plugin building blocks, both used here:

* ``fastapi_apps``   — a small FastAPI app mounted on the Airflow API server
                       at ``/lw-commerce`` (HTML page + JSON endpoint).
* ``external_views`` — a navigation entry ("LW Commerce KPIs") that renders the
                       page inside the Airflow UI as an iframe at
                       ``/plugin/lw-commerce-kpis``.

The page queries ``{catalog}.gold.*`` through Databricks SQL with the same
connection path as the DAG (``include/databricks_client.py``: Airflow
connection ``databricks_sql`` → ``DATABRICKS_*`` env fallback).
"""

from __future__ import annotations

from airflow.plugins_manager import AirflowPlugin

from lw_commerce_dashboard.app import URL_PREFIX, app

ICON = f"{URL_PREFIX}/static/icon.svg"


class LWCommerceDashboardPlugin(AirflowPlugin):
    name = "lw_commerce_dashboard"

    fastapi_apps = [
        {
            "app": app,
            "url_prefix": URL_PREFIX,
            "name": "LW Commerce gold dashboard",
        }
    ]

    external_views = [
        {
            "name": "LW Commerce KPIs",
            "href": f"{URL_PREFIX}/",
            "destination": "nav",
            "url_route": "lw-commerce-kpis",
            "icon": ICON,
            "nav_top_level": True,
        }
    ]
