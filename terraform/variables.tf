variable "databricks_host" {
  type        = string
  description = "Workspace URL, e.g. https://dbc-<workspace>.cloud.databricks.com"
}

variable "databricks_token" {
  type      = string
  sensitive = true
}

variable "catalog_name" {
  type    = string
  default = "workspace"
}
