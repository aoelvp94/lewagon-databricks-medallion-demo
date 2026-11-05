"""Shared Databricks SQL Warehouse helpers (ingest + just recipes)."""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from typing import Any, Iterator

from databricks import sql as databricks_sql


def _conn_fields_from_airflow() -> dict[str, str] | None:
    try:
        try:
            from airflow.sdk.bases.hook import BaseHook
        except ImportError:  # Airflow 2 / older Runtime
            from airflow.hooks.base import BaseHook

        conn = BaseHook.get_connection("databricks_sql")
    except Exception:  # noqa: BLE001 — Airflow may be unavailable outside workers
        return None

    extra = conn.extra_dejson or {}
    host = (conn.host or os.environ.get("DATABRICKS_HOST") or "").rstrip("/")
    if host.startswith("https://"):
        host = host[len("https://") :]
    elif host.startswith("http://"):
        host = host[len("http://") :]

    token = (
        conn.password
        or extra.get("token")
        or os.environ.get("DATABRICKS_TOKEN")
        or ""
    )
    http_path = extra.get("http_path") or os.environ.get("DATABRICKS_HTTP_PATH") or ""
    catalog = (
        extra.get("catalog")
        or os.environ.get("DATABRICKS_CATALOG")
        or "workspace"
    )
    return {
        "server_hostname": host,
        "http_path": http_path,
        "access_token": token,
        "catalog": catalog,
    }


def databricks_settings() -> dict[str, str]:
    """Resolve host / http_path / token / catalog from Airflow conn or env."""
    fields = _conn_fields_from_airflow()
    if fields and fields["server_hostname"] and fields["http_path"] and fields["access_token"]:
        return fields

    host = (os.environ.get("DATABRICKS_HOST") or "").rstrip("/")
    if host.startswith("https://"):
        host = host[len("https://") :]
    elif host.startswith("http://"):
        host = host[len("http://") :]

    settings = {
        "server_hostname": host,
        "http_path": os.environ.get("DATABRICKS_HTTP_PATH") or "",
        "access_token": os.environ.get("DATABRICKS_TOKEN") or "",
        "catalog": os.environ.get("DATABRICKS_CATALOG") or "workspace",
    }
    missing = [k for k, v in settings.items() if not v and k != "catalog"]
    if missing:
        raise RuntimeError(
            "Missing Databricks settings: "
            + ", ".join(missing)
            + ". Set DATABRICKS_HOST / DATABRICKS_HTTP_PATH / DATABRICKS_TOKEN "
            + "in .env and the databricks_sql Airflow connection (see .env.example)."
        )
    return settings


def catalog_name() -> str:
    return databricks_settings()["catalog"]


def fq(schema: str, table: str) -> str:
    """Fully-qualified Unity Catalog table name."""
    return f"`{catalog_name()}`.`{schema}`.`{table}`"


@contextmanager
def databricks_connection() -> Iterator[Any]:
    cfg = databricks_settings()
    connection = databricks_sql.connect(
        server_hostname=cfg["server_hostname"],
        http_path=cfg["http_path"],
        access_token=cfg["access_token"],
        catalog=cfg["catalog"],
    )
    try:
        yield connection
    finally:
        connection.close()


def fetch_dicts(query: str, params: tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
    with databricks_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            columns = [d[0] for d in (cur.description or [])]
            return [dict(zip(columns, row)) for row in cur.fetchall()]


def execute_sql(statements: list[str]) -> None:
    with databricks_connection() as conn:
        with conn.cursor() as cur:
            for statement in statements:
                cur.execute(statement)


def extra_json_for_airflow(http_path: str, catalog: str) -> str:
    return json.dumps({"http_path": http_path, "catalog": catalog})
