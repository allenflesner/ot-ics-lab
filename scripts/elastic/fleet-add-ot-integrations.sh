#!/usr/bin/env bash
# Add Zeek, Suricata and System integrations to the lab agent policy via the
# Kibana Fleet API. Run from anywhere that can reach Kibana (Ludus host, Kali,
# or your workstation over Ludus WireGuard).
#
#   KIBANA_URL=https://10.5.50.10:5601 ELASTIC_PASSWORD='...' ./fleet-add-ot-integrations.sh
#
# Optional: POLICY_ID=<id> to target a specific agent policy. Otherwise the
# first non-Fleet-Server policy is used (the one ludus_elastic_container made).
#
# Custom JSON logs (ICSNPP extras, process truth, HMI audit) are added in the
# Kibana UI on purpose - see docs/04-elastic.md - so you learn the workflow.
set -euo pipefail

KIBANA_URL="${KIBANA_URL:?set KIBANA_URL, e.g. https://10.5.50.10:5601}"
ELASTIC_USER="${ELASTIC_USER:-elastic}"
ELASTIC_PASSWORD="${ELASTIC_PASSWORD:?set ELASTIC_PASSWORD}"
PACKAGES="${PACKAGES:-zeek suricata system}"
CURL=(curl -sS -k -u "${ELASTIC_USER}:${ELASTIC_PASSWORD}" -H 'kbn-xsrf: true' -H 'Content-Type: application/json')

command -v jq >/dev/null || { echo "jq is required"; exit 1; }

api() { "${CURL[@]}" "$@"; }

if [[ -z "${POLICY_ID:-}" ]]; then
  POLICY_ID="$(api "${KIBANA_URL}/api/fleet/agent_policies?perPage=100" \
    | jq -r '[.items[] | select((.has_fleet_server // false) | not) | select((.is_managed // false) | not)][0].id')"
fi
[[ -n "$POLICY_ID" && "$POLICY_ID" != "null" ]] || { echo "No agent policy found; set POLICY_ID"; exit 1; }
echo "[+] target agent policy: ${POLICY_ID}"

existing="$(api "${KIBANA_URL}/api/fleet/package_policies?perPage=1000" \
  | jq -r --arg p "$POLICY_ID" '.items[] | select(.policy_id==$p or ((.policy_ids // []) | index($p))) | .package.name')"

for pkg in $PACKAGES; do
  if grep -qx "$pkg" <<<"$existing"; then
    echo "[=] ${pkg} already on policy"
    continue
  fi
  version="$(api "${KIBANA_URL}/api/fleet/epm/packages/${pkg}" | jq -r '.item.version // .response.version')"
  [[ -n "$version" && "$version" != "null" ]] || { echo "[!] could not resolve version for ${pkg}"; continue; }
  echo "[*] installing ${pkg} ${version}"
  api -X POST "${KIBANA_URL}/api/fleet/epm/packages/${pkg}/${version}" -d '{"force":true}' >/dev/null
  body="$(jq -n --arg p "$POLICY_ID" --arg n "$pkg" --arg v "$version" \
    '{policy_id:$p, package:{name:$n, version:$v}, name:("otlab-" + $n), namespace:"default",
      description:"Added by ot-ics-lab fleet-add-ot-integrations.sh"}')"
  resp="$(api -X POST "${KIBANA_URL}/api/fleet/package_policies" -d "$body")"
  if jq -e '.item.id' >/dev/null <<<"$resp"; then
    echo "[+] ${pkg} added (default inputs)"
  else
    echo "[!] ${pkg} failed: $(jq -c '.' <<<"$resp" | cut -c1-400)"
  fi
done

cat <<'EOF'

Default paths the integrations will read:
  zeek      /opt/zeek/logs/current/*.log   (JSON - the sensor role enables json-logs)
  suricata  /var/log/suricata/eve.json
Agents on hosts without these files simply ship nothing for them.

Next: docs/04-elastic.md -> add the Custom Logs (Filestream) integration for
  /opt/zeek/logs/current/modbus_*.log, notice.log extras, /var/log/ot-process/*.jsonl,
  /var/log/ot-hmi/*.jsonl
EOF
