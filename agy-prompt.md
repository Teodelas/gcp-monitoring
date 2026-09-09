You are an expert Google Cloud Observability and Data Engineer.

Create an `implementation_plan.md` to execute a one-time data extraction that pulls a 1-day report of average CPU, Memory, and Storage utilization across all Google Cloud projects in my organization, grouped by GCP Service and Project ID.

### Context & References:
Use the logic and scripts from these repository files:
1. PromQL Query Definitions:
   https://github.com/Teodelas/gcp-dev/blob/main/service-level-monitoring.promql
2. Project Sharding Script:
   https://github.com/Teodelas/gcp-dev/blob/main/shard_projects_to_hubs.sh

### Objective:
Run a one-time batch extraction over the past 24 hours of data and export the consolidated results to a clean CSV / spreadsheet (`gcp_fleet_utilization_1day_report.csv`).

### Implementation Plan Requirements:
1. **Temporary Metrics Scope Setup**:
   - Plan the execution of `shard_projects_to_hubs.sh` across 8 temporary hub projects to link all projects into queryable metrics scopes (respecting the 375 limit).

2. **24-Hour Range Execution**:
   - Adapt the PromQL queries from `service-level-monitoring.promql` to query the 24-hour historical window (using `avg_over_time(...[24h])` or PromQL range API).
   - Cover Compute Engine, Cloud SQL, Cloud Run, GKE, AlloyDB, and Memorystore.

3. **Data Extraction & Consolidation Script**:
   - Write a Python/Bash runner that iterates over the 8 hub project endpoints via the Cloud Monitoring Prometheus API (`/v1/projects/{HUB_ID}/location/global/prometheus/api/v1/query`).
   - Merge all records into a single consolidated output file (`gcp_fleet_utilization_1day_report.csv`) with the columns:
     `project_id, service, metric_type, avg_utilization_percent`

4. **Verification & Cleanup**:
   - Provide steps to verify data completeness across projects.
   - Include optional cleanup commands to remove the metrics scopes once the report is generated.

Write the detailed plan to `implementation_plan.md` and request feedback before running the extraction.
