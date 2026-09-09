#!/usr/bin/env bash
#
# shard_projects_to_hubs.sh
# Distributes up to 3000 projects across an array of Hub Scoping Projects
#

set -eo pipefail

ORG_ID="$1"
shift
HUB_PROJECTS=("$@") # Pass all hub project IDs as arguments

if [[ -z "${ORG_ID}" || ${#HUB_PROJECTS[@]} -eq 0 ]]; then
  echo "Usage: $0 <ORGANIZATION_ID> <HUB_1> <HUB_2> ... <HUB_N>"
  echo "Example: $0 123456789012 mon-hub-01 mon-hub-02 mon-hub-03 mon-hub-04 mon-hub-05 mon-hub-06 mon-hub-07 mon-hub-08"
  exit 1
fi

NUM_HUBS=${#HUB_PROJECTS[@]}
echo "==> Fetching all active projects for Org ${ORG_ID}..."
ALL_PROJECTS=($(gcloud projects list --filter="parent.id:${ORG_ID} AND lifecycleState:ACTIVE" --format="value(projectId)"))
TOTAL_PROJECTS=${#ALL_PROJECTS[@]}

echo "Found ${TOTAL_PROJECTS} projects to distribute across ${NUM_HUBS} hubs."
MAX_PER_HUB=$(( (TOTAL_PROJECTS + NUM_HUBS - 1) / NUM_HUBS ))
echo "Target batch size: ~${MAX_PER_HUB} projects per hub."

if [[ ${MAX_PER_HUB} -gt 375 ]]; then
  echo "ERROR: Batch size (${MAX_PER_HUB}) exceeds Google Cloud's 375 limit! Add more hub projects."
  exit 1
fi

HUB_INDEX=0
COUNT_IN_CURRENT_HUB=0

for PROJ in "${ALL_PROJECTS[@]}"; do
  CURRENT_HUB="${HUB_PROJECTS[$HUB_INDEX]}"

  # Skip if project is one of the hubs
  for H in "${HUB_PROJECTS[@]}"; do
    if [[ "${PROJ}" == "${H}" ]]; then
      continue 2
    fi
  done

  echo "Adding ${PROJ} -> ${CURRENT_HUB}..."
  gcloud beta monitoring metrics-scopes create "projects/${PROJ}" --project="${CURRENT_HUB}" --quiet || true

  ((COUNT_IN_CURRENT_HUB++))
  if [[ ${COUNT_IN_CURRENT_HUB} -ge ${MAX_PER_HUB} ]]; then
    ((HUB_INDEX++))
    COUNT_IN_CURRENT_HUB=0
  fi
done

echo "==> Successfully sharded ${TOTAL_PROJECTS} projects across ${NUM_HUBS} hubs."
