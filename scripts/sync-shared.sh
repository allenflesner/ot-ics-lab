#!/usr/bin/env bash
# Copy src/mbtcp.py into every place that ships it (Ludus uploads each role
# directory on its own, so roles can't share files via symlinks).
# --check: exit non-zero if any copy has drifted (used by CI).
set -euo pipefail
cd "$(dirname "$0")/.."
targets=(ansible/roles/ot_field_sim/files/mbtcp.py ansible/roles/ot_hmi/files/mbtcp.py attacks/mbtcp.py)
if [[ "${1:-}" == "--check" ]]; then
  rc=0
  for t in "${targets[@]}"; do cmp -s src/mbtcp.py "$t" || { echo "drift: $t"; rc=1; }; done
  exit $rc
fi
for t in "${targets[@]}"; do cp src/mbtcp.py "$t"; echo "synced $t"; done
