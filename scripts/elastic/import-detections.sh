#!/usr/bin/env bash
# Import the lab's Elastic detection rules (detections/elastic/rules/*.json).
# Rules use the placeholder __NET__ for the first two octets (e.g. 10.5).
#
#   KIBANA_URL=https://10.5.50.10:5601 ELASTIC_PASSWORD='...' LAB_NET=10.5 ./import-detections.sh
set -euo pipefail

KIBANA_URL="${KIBANA_URL:?set KIBANA_URL}"
ELASTIC_USER="${ELASTIC_USER:-elastic}"
ELASTIC_PASSWORD="${ELASTIC_PASSWORD:?set ELASTIC_PASSWORD}"
LAB_NET="${LAB_NET:?set LAB_NET to 10.<range number>, e.g. 10.5}"
RULE_DIR="$(cd "$(dirname "$0")/../../detections/elastic/rules" && pwd)"

[[ "$LAB_NET" =~ ^10\.[0-9]{1,3}$ ]] || { echo "LAB_NET must look like 10.N"; exit 1; }

out="$(mktemp --suffix=.ndjson)"
trap 'rm -f "$out"' EXIT
for f in "$RULE_DIR"/*.json; do
  sed "s/__NET__/${LAB_NET}/g" "$f" | jq -c '.' >> "$out"
done
echo "[*] importing $(wc -l < "$out") rules from ${RULE_DIR}"

curl -sS -k -u "${ELASTIC_USER}:${ELASTIC_PASSWORD}" -H 'kbn-xsrf: true' \
  -X POST "${KIBANA_URL}/api/detection_engine/rules/_import?overwrite=true" \
  -F "file=@${out};type=application/x-ndjson" | jq '{success, success_count, errors}'
