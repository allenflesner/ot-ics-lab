#!/usr/bin/env bash
# Add/refresh all lab roles on the Ludus server (run where the ludus CLI is configured).
set -euo pipefail
cd "$(dirname "$0")/../.."

ludus ansible role add badsectorlabs.ludus_elastic_container
ludus ansible role add badsectorlabs.ludus_elastic_agent

for role in ansible/roles/*/; do
  echo "[*] adding local role $(basename "$role")"
  ludus ansible role add -d "$role" --force
done
ludus ansible role list
