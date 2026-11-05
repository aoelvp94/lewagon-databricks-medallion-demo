# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze - ingest LW Commerce API -> Delta
# MAGIC Pulls `/v1/products` and `/v1/orders` (paginated) over HTTP with `X-API-Key`.
# MAGIC If `source.api_base_url` is empty, falls back to fixtures in `api/sample_responses/`.

# COMMAND ----------
import json, os, urllib.request
from datetime import datetime, timezone

import dlt
from pyspark.sql import functions as F

def conf(key, default=""):
    try:
        return spark.conf.get(key, default) or default
    except Exception:
        return default

API_BASE_URL = conf("source.api_base_url").rstrip("/")
API_KEY = conf("source.api_key", "lewagon-demo")
FIXTURES_DIR = conf("source.fixtures_dir", "")


def _get(path):
    url = f"{API_BASE_URL}{path}"
    req = urllib.request.Request(url, headers={"X-API-Key": API_KEY, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read()), url


def _fixture(name):
    base = FIXTURES_DIR or os.path.join(os.getcwd(), "..", "..", "api", "sample_responses")
    path = os.path.join(base, f"{name}.json")
    with open(path) as f:
        return json.load(f), f"file://{path}"


def fetch(resource):
    """Returns list of (raw_json_string, source_url)."""
    if not API_BASE_URL:
        body, url = _fixture(resource)
        return [(json.dumps(r), url) for r in body["data"]]
    if resource == "products":
        body, url = _get("/v1/products")
        return [(json.dumps(r), url) for r in body["data"]]
    rows, page = [], 1
    while page:
        body, url = _get(f"/v1/orders?page={page}&page_size=200")
        rows += [(json.dumps(r), url) for r in body["data"]]
        page = body.get("next_page")
    return rows


def to_df(resource):
    rows = fetch(resource)
    return (spark.createDataFrame(rows, "raw string, _source_url string")
            .withColumn("_ingested_at", F.lit(datetime.now(timezone.utc)).cast("timestamp")))

# COMMAND ----------
@dlt.table(name="raw_products", comment="Raw /v1/products payloads")
def raw_products():
    return to_df("products")


@dlt.table(name="raw_orders", comment="Raw /v1/orders payloads (all pages)")
def raw_orders():
    return to_df("orders")
