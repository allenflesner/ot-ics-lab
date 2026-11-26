#!/usr/bin/env bash
# ot-span.sh - virtual SPAN port for the OT lab sensor, run ON THE LUDUS/PROXMOX HOST.
#
# Ludus puts every VM of a range on one VLAN-aware bridge (vmbr1000+N). Linux
# bridges have no built-in port mirroring, so this script uses tc "mirred" to
# copy every frame each lab VM transmits onto a second NIC of the sensor VM.
#
#   - Mirrors INGRESS of each VM tap (= frames the VM sends). Every packet in
#     the lab is sent by some VM, so each packet is captured once.
#   - The router and the sensor itself are excluded (avoids duplicates/loops).
#     Trade-off: traffic that only the router originates (internet->VM) shows
#     as half-flows. That is fine for this lab.
#   - The sensor's span NIC sits on an otherwise-unused VLAN tag, so it never
#     participates in real switching.
#   - tc rules die when a VM restarts (new tap). The systemd timer re-applies.
#
# Usage:
#   sudo RANGE_ID=AL ./ot-span.sh setup     # add sensor NIC, apply, install timer
#   sudo RANGE_ID=AL ./ot-span.sh apply     # (idempotent) re-apply mirrors
#   sudo RANGE_ID=AL ./ot-span.sh status
#   sudo RANGE_ID=AL ./ot-span.sh teardown  # remove mirrors + timer (keeps NIC)
set -euo pipefail

CONF=/etc/ot-span.conf
# shellcheck disable=SC1090
[[ -f "$CONF" ]] && source "$CONF"

RANGE_ID="${RANGE_ID:?set RANGE_ID (your Ludus range/user ID, e.g. AL)}"
SENSOR_NAME="${SENSOR_NAME:-${RANGE_ID}-ot-sensor}"
SPAN_VLAN="${SPAN_VLAN:-250}"
EXCLUDE_REGEX="${EXCLUDE_REGEX:-(-router|-ot-sensor)}"
SELF="$(readlink -f "$0")"

log() { printf '[ot-span] %s\n' "$*"; }
die() { printf '[ot-span] ERROR: %s\n' "$*" >&2; exit 1; }

command -v qm >/dev/null || die "qm not found - run this on the Proxmox/Ludus host"
command -v tc >/dev/null || die "tc not found (apt install iproute2)"

vmid_by_name() {
  qm list | awk -v n="$1" 'NR>1 && $2==n {print $1}'
}

lab_vms() {
  # running VMs in this range, minus exclusions -> "vmid name"
  qm list | awk -v p="${RANGE_ID}-" 'NR>1 && index($2,p)==1 && $3=="running" {print $1, $2}' \
    | grep -Ev -- "${EXCLUDE_REGEX}" || true
}

sensor_id() {
  local id
  id="$(vmid_by_name "$SENSOR_NAME")"
  [[ -n "$id" ]] || die "sensor VM '$SENSOR_NAME' not found (deploy the range first)"
  echo "$id"
}

span_dev() { echo "tap$(sensor_id)i1"; }

cmd_setup() {
  local sid bridge
  sid="$(sensor_id)"
  if qm config "$sid" | grep -q '^net1:'; then
    log "sensor $SENSOR_NAME ($sid) already has net1"
  else
    bridge="$(qm config "$sid" | sed -n 's/^net0:.*bridge=\([^,]*\).*/\1/p')"
    [[ -n "$bridge" ]] || die "could not read sensor net0 bridge"
    log "adding net1 to $SENSOR_NAME on $bridge tag=$SPAN_VLAN (firewall off)"
    qm set "$sid" --net1 "virtio,bridge=${bridge},tag=${SPAN_VLAN},firewall=0"
    log "hot-plugged; if ens19 does not appear in the guest, reboot the sensor VM"
  fi

  printf 'RANGE_ID=%q\nSENSOR_NAME=%q\nSPAN_VLAN=%q\nEXCLUDE_REGEX=%q\n' \
    "$RANGE_ID" "$SENSOR_NAME" "$SPAN_VLAN" "$EXCLUDE_REGEX" > "$CONF"
  install -m 0755 "$SELF" /usr/local/sbin/ot-span.sh

  cat > /etc/systemd/system/ot-span.service <<'EOF'
[Unit]
Description=OT lab virtual SPAN - (re)apply tc mirred rules

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/ot-span.sh apply
EOF
  cat > /etc/systemd/system/ot-span.timer <<'EOF'
[Unit]
Description=Re-apply OT lab SPAN mirrors every 30s (VM restarts recreate taps)

[Timer]
OnBootSec=60
OnUnitActiveSec=30
AccuracySec=5

[Install]
WantedBy=timers.target
EOF
  systemctl daemon-reload
  systemctl enable --now ot-span.timer
  cmd_apply
  log "done. Next: ludus range deploy -t user-defined-roles --limit ${SENSOR_NAME}"
}

cmd_apply() {
  local dst vmid name tap changed=0
  dst="$(span_dev)"
  ip link show "$dst" >/dev/null 2>&1 || die "$dst missing - is the sensor running with net1? (run setup)"
  while read -r vmid name; do
    [[ -n "${vmid:-}" ]] || continue
    for tap in /sys/class/net/tap"${vmid}"i*; do
      [[ -e "$tap" ]] || continue
      tap="$(basename "$tap")"
      if tc filter show dev "$tap" ingress 2>/dev/null | grep -q "mirred.*${dst}"; then
        continue
      fi
      tc qdisc replace dev "$tap" handle ffff: ingress
      tc filter add dev "$tap" parent ffff: protocol all prio 49 matchall \
        action mirred egress mirror dev "$dst"
      log "mirroring $name ($tap) -> $dst"
      changed=1
    done
  done < <(lab_vms)
  [[ "$changed" -eq 1 ]] || true
}

cmd_status() {
  local dst vmid name tap
  dst="$(span_dev)"
  log "sensor span device: $dst"
  while read -r vmid name; do
    [[ -n "${vmid:-}" ]] || continue
    for tap in /sys/class/net/tap"${vmid}"i*; do
      [[ -e "$tap" ]] || continue
      tap="$(basename "$tap")"
      if tc filter show dev "$tap" ingress 2>/dev/null | grep -q "mirred.*${dst}"; then
        printf '  %-28s %-12s MIRRORED\n' "$name" "$tap"
      else
        printf '  %-28s %-12s not mirrored\n' "$name" "$tap"
      fi
    done
  done < <(lab_vms)
}

cmd_teardown() {
  local vmid name tap
  systemctl disable --now ot-span.timer 2>/dev/null || true
  while read -r vmid name; do
    for tap in /sys/class/net/tap"${vmid}"i*; do
      [[ -e "$tap" ]] || continue
      tc qdisc del dev "$(basename "$tap")" ingress 2>/dev/null || true
    done
  done < <(lab_vms)
  log "mirrors removed (sensor net1 left in place; remove with: qm set <id> --delete net1)"
}

case "${1:-}" in
  setup) cmd_setup ;;
  apply) cmd_apply ;;
  status) cmd_status ;;
  teardown) cmd_teardown ;;
  *) echo "usage: RANGE_ID=<id> $0 {setup|apply|status|teardown}"; exit 2 ;;
esac
