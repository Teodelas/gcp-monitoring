#!/usr/bin/env python3
"""
export_fleet_metrics.py
Queries 5-minute PromQL metrics across Google Cloud projects matching an optional prefix
and writes the consolidated results to a CSV file.
python3 export_fleet_metrics.py [OPTIONAL_PREFIX]
"""

import csv
from datetime import datetime, timezone
import json
import subprocess
import sys
import urllib.parse
import urllib.request

# ================= CONFIGURATION =================
# Leave empty ("") to match all active projects, or specify a generic prefix like "prod-" or "app-"
DEFAULT_PREFIX = ""
OUTPUT_CSV = "fleet_utilization_5m_report.csv"

# 5-Minute Unified PromQL Query covering CPU, Memory, and Storage
PROMQL_QUERY = """
  label_replace(
    label_replace(
      avg(sum by (instance_id) (
        avg_over_time(agent_googleapis_com:cpu_utilization{monitored_resource="gce_instance", cpu_state!="idle"}[5m])
      )),
      "service", "Compute Engine", "", ""
    ),
    "metric_type", "CPU", "", ""
  )
or
  label_replace(
    label_replace(
      avg(sum by (instance_id) (
        avg_over_time(agent_googleapis_com:memory_percent_used{monitored_resource="gce_instance", state="used"}[5m])
      )),
      "service", "Compute Engine", "", ""
    ),
    "metric_type", "Memory", "", ""
  )
or
  label_replace(
    label_replace(
      avg(max by (instance_id) (
        avg_over_time(agent_googleapis_com:disk_percent_used{monitored_resource="gce_instance", state="used"}[5m])
      )),
      "service", "Compute Engine", "", ""
    ),
    "metric_type", "Storage", "", ""
  )
or
  label_replace(
    label_replace(
      avg(avg_over_time(cloudsql_googleapis_com:database_cpu_utilization[5m])) * 100,
      "service", "Cloud SQL", "", ""
    ),
    "metric_type", "CPU", "", ""
  )
or
  label_replace(
    label_replace(
      avg(avg_over_time(cloudsql_googleapis_com:database_memory_utilization[5m])) * 100,
      "service", "Cloud SQL", "", ""
    ),
    "metric_type", "Memory", "", ""
  )
or
  label_replace(
    label_replace(
      avg(avg_over_time(cloudsql_googleapis_com:database_disk_utilization[5m])) * 100,
      "service", "Cloud SQL", "", ""
    ),
    "metric_type", "Storage", "", ""
  )
or
  label_replace(
    label_replace(
      avg(avg_over_time(run_googleapis_com:container_cpu_utilizations[5m])) * 100,
      "service", "Cloud Run", "", ""
    ),
    "metric_type", "CPU", "", ""
  )
or
  label_replace(
    label_replace(
      avg(avg_over_time(run_googleapis_com:container_memory_utilizations[5m])) * 100,
      "service", "Cloud Run", "", ""
    ),
    "metric_type", "Memory", "", ""
  )
or
  label_replace(
    label_replace(
      avg(avg_over_time(kubernetes_io:node_cpu_allocatable_utilization[5m])) * 100,
      "service", "GKE Nodes", "", ""
    ),
    "metric_type", "CPU", "", ""
  )
or
  label_replace(
    label_replace(
      avg(avg_over_time(kubernetes_io:node_memory_allocatable_utilization[5m])) * 100,
      "service", "GKE Nodes", "", ""
    ),
    "metric_type", "Memory", "", ""
  )
or
  label_replace(
    label_replace(
      avg(avg_over_time(kubernetes_io:node_ephemeral_storage_allocatable_utilization[5m])) * 100,
      "service", "GKE Nodes", "", ""
    ),
    "metric_type", "Storage", "", ""
  )
"""
# =================================================


def get_auth_token():
    """Retrieve OAuth2 token from active gcloud session."""
    return (
        subprocess.check_output(["gcloud", "auth", "print-access-token"])
        .decode()
        .strip()
    )


def list_projects(prefix=""):
    """Discover active projects matching the optional prefix."""
    cmd = [
        "gcloud",
        "projects",
        "list",
        "--filter=lifecycleState:ACTIVE",
        "--format=value(projectId)",
    ]
    all_projects = subprocess.check_output(cmd).decode().splitlines()
    if prefix:
        return [p for p in all_projects if p.startswith(prefix)]
    return all_projects


def query_project_promql(project_id, token):
    """Executes PromQL against the project's Cloud Monitoring endpoint."""
    url = f"https://monitoring.googleapis.com/v1/projects/{project_id}/location/global/prometheus/api/v1/query"
    data = urllib.parse.urlencode({"query": PROMQL_QUERY}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode())
            if result.get("status") == "success":
                return result.get("data", {}).get("result", [])
    except Exception as e:
        print(f"    [WARN] Project {project_id} query returned: {e}")
    return []


def main():
    prefix = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PREFIX
    if prefix:
        print(f"==> Discovering projects matching prefix '{prefix}'...")
    else:
        print("==> Discovering all active projects...")

    projects = list_projects(prefix)
    print(f"Found {len(projects)} matching project(s).")

    if not projects:
        print("No matching projects found. Exiting.")
        return

    token = get_auth_token()
    rows = []

    print("\n==> Querying 5-minute PromQL metrics per project...")
    for idx, proj in enumerate(projects, 1):
        print(f"[{idx}/{len(projects)}] Processing {proj}...")
        results = query_project_promql(proj, token)
        print(f"    -> Received {len(results)} metric series.")

        for item in results:
            metric = item.get("metric", {})
            val = item.get("value", [None, None])[1]

            service = metric.get("service", "Unknown")
            metric_type = metric.get("metric_type", "Unknown")

            rows.append(
                {
                    "project_id": proj,
                    "service": service,
                    "metric_type": metric_type,
                    "avg_utilization_percent_5m": (
                        round(float(val), 2) if val is not None else "N/A"
                    ),
                    "extracted_at": datetime.now(timezone.utc).isoformat(),
                }
            )

    # Write to CSV
    print(f"\n==> Writing {len(rows)} records to {OUTPUT_CSV}...")
    with open(OUTPUT_CSV, "w", newline="") as csvfile:
        fieldnames = [
            "project_id",
            "service",
            "metric_type",
            "avg_utilization_percent_5m",
            "extracted_at",
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"==> Done! Report saved to {OUTPUT_CSV}\n")


if __name__ == "__main__":
    main()
