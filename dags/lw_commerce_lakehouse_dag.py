"""
LW Commerce lakehouse DAG (Le Wagon DE teaching demo)

1. Ingest products + orders from the invented LW Commerce FastAPI into Databricks raw.
2. Transform with dbt via Astronomer Cosmos against a Databricks SQL Warehouse,
   visualized as sequential medallion layers in the Airflow graph:
   - bronze: flatten STRING JSON + dedupe
   - silver: typed commerce entities (products, orders, order_items)
   - gold: KPI aggregates (daily revenue, top products, fulfillment, customers)
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path

from airflow.decorators import dag, task
from airflow.models.param import Param
from cosmos import DbtTaskGroup, ExecutionConfig, ProfileConfig, ProjectConfig, RenderConfig
from cosmos.constants import TestBehavior
from cosmos.profiles import DatabricksTokenProfileMapping

try:
    from airflow.sdk import get_current_context
except ImportError:  # Airflow 2 compatibility
    from airflow.operators.python import get_current_context

DBT_PROJECT_PATH = Path(__file__).parent / "dbt" / "lw_commerce"
DBT_EXECUTABLE = f"{os.environ.get('AIRFLOW_HOME', '/usr/local/airflow')}/dbt_venv/bin/dbt"

project_config = ProjectConfig(dbt_project_path=DBT_PROJECT_PATH.as_posix())

profile_config = ProfileConfig(
    profile_name="lw_commerce",
    target_name="dev",
    profile_mapping=DatabricksTokenProfileMapping(
        conn_id="databricks_sql",
        profile_args={
            "catalog": os.environ.get("DATABRICKS_CATALOG", "workspace"),
            "schema": "bronze",
            "threads": 4,
        },
    ),
)

execution_config = ExecutionConfig(
    dbt_executable_path=DBT_EXECUTABLE,
)

_OPERATOR_ARGS = {
    "install_deps": False,
    "append_env": True,
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
    "execution_timeout": timedelta(minutes=45),
}


def _medallion_layer(group_id: str, select: list[str]) -> DbtTaskGroup:
    """One Cosmos task group per medallion layer (visible in the DAG graph)."""
    return DbtTaskGroup(
        group_id=group_id,
        project_config=project_config,
        profile_config=profile_config,
        execution_config=execution_config,
        render_config=RenderConfig(
            select=select,
            test_behavior=TestBehavior.AFTER_ALL,
        ),
        operator_args=_OPERATOR_ARGS,
    )


@dag(
    dag_id="lw_commerce_lakehouse",
    description="HTTP API ingest → Databricks dbt bronze → silver → gold (LW Commerce)",
    schedule="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args={
        "owner": "lewagon",
        "retries": 2,
        "retry_delay": timedelta(minutes=2),
        "execution_timeout": timedelta(minutes=45),
    },
    tags=["cosmos", "dbt", "lewagon", "medallion", "databricks", "commerce"],
    params={
        "max_order_pages": Param(20, type="integer", minimum=1, maximum=50),
    },
    doc_md=__doc__,
)
def lw_commerce_lakehouse():
    @task(task_id="ingest_bronze_http")
    def ingest_bronze_http() -> dict:
        from include.lw_commerce_ingest import ingest_lw_commerce_api

        context = get_current_context()
        params = context["params"]
        return ingest_lw_commerce_api(
            max_order_pages=int(params.get("max_order_pages", 20)),
        )

    bronze = _medallion_layer("bronze", ["path:models/bronze"])
    silver = _medallion_layer("silver", ["path:models/silver"])
    gold = _medallion_layer("gold", ["path:models/gold"])

    ingest_bronze_http() >> bronze >> silver >> gold


lw_commerce_lakehouse()
