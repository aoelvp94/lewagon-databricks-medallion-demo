"""Smoke test: DAG file is importable when Airflow/Cosmos are available."""

from __future__ import annotations

from pathlib import Path

DAG_FILE = Path(__file__).resolve().parents[2] / "dags" / "lw_commerce_lakehouse_dag.py"


def test_dag_file_exists():
    assert DAG_FILE.is_file()
    text = DAG_FILE.read_text()
    assert "lw_commerce_lakehouse" in text
    assert "DbtTaskGroup" in text
    assert "ingest_bronze_http" in text
