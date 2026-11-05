terraform {
  required_version = ">= 1.6.0"
  required_providers {
    databricks = {
      source  = "databricks/databricks"
      version = "~> 1.50"
    }
  }
}

provider "databricks" {
  host  = var.databricks_host
  token = var.databricks_token
}

# Optional: create UC schemas ahead of the first DAG run.
# Ingest also runs CREATE SCHEMA IF NOT EXISTS via include/sql/init_warehouse.sql.

resource "databricks_schema" "raw" {
  catalog_name = var.catalog_name
  name         = "raw"
  comment      = "LW Commerce raw landing (API payloads)."
}

resource "databricks_schema" "bronze" {
  catalog_name = var.catalog_name
  name         = "bronze"
  comment      = "LW Commerce bronze (dbt)."
}

resource "databricks_schema" "silver" {
  catalog_name = var.catalog_name
  name         = "silver"
  comment      = "LW Commerce silver (dbt)."
}

resource "databricks_schema" "gold" {
  catalog_name = var.catalog_name
  name         = "gold"
  comment      = "LW Commerce gold KPIs (dbt)."
}

output "schemas" {
  value = {
    raw    = databricks_schema.raw.name
    bronze = databricks_schema.bronze.name
    silver = databricks_schema.silver.name
    gold   = databricks_schema.gold.name
  }
}
