terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {}

variable "scoping_project" {
  type        = string
  description = "The central reporting hub project ID."
}

variable "project_prefix" {
  type        = string
  description = "Generic prefix used to filter projects (e.g., prod-, app-)."
  default     = "prod-"
}

variable "organization_id" {
  type        = string
  description = "Optional Google Cloud Organization ID (leave empty if discovering across active credentials)."
  default     = null
}

# 1. Discover all active projects
data "google_projects" "all" {
  filter = var.organization_id != null ? "parent.id:${var.organization_id} AND lifecycleState:ACTIVE" : "lifecycleState:ACTIVE"
}

# 2. Filter for projects starting with the prefix (excluding the hub itself)
locals {
  target_projects = [
    for p in data.google_projects.all.projects : p.project_id
    if startswith(p.project_id, var.project_prefix) && p.project_id != var.scoping_project
  ]
}

# 3. Attach all matching projects to the single scoping project
resource "google_monitoring_monitored_project" "monitored" {
  for_each      = toset(local.target_projects)
  metrics_scope = var.scoping_project
  name          = "locations/global/metricsScopes/${var.scoping_project}/projects/${each.value}"
}

output "monitored_project_count" {
  description = "Total number of projects attached."
  value       = length(local.target_projects)
}

output "monitored_projects" {
  description = "List of project IDs attached to the metrics scope."
  value       = local.target_projects
}
