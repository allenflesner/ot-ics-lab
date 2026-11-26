#!/usr/bin/env bash
# Carve a time window out of the sensor's rolling pcap for Wireshark.
# Run on the sensor (or via ssh). Requires wireshark-common (editcap/mergecap).
#
#   sudo ./pull-pcap.sh "2026-11-25 21:00:00" "2026-11-25 21:15:00" /tmp/scenario02.pcap
set -euo pipefail
start="${1:?start time 'YYYY-MM-DD HH:MM:SS'}"
end="${2:?end time}"
out="${3:-/tmp/otlab-$(date +%s).pcap}"
dir="${PCAP_DIR:-/var/pcap}"

command -v mergecap >/dev/null || apt-get install -y wireshark-common >/dev/null
tmp="$(mktemp --suffix=.pcap)"
trap 'rm -f "$tmp"' EXIT
mergecap -w "$tmp" "$dir"/otlab.pcap*
editcap -A "$start" -B "$end" "$tmp" "$out"
echo "wrote $out ($(du -h "$out" | cut -f1)). Copy it off with:"
echo "  scp $(hostname -I | awk '{print $1}'):$out ."
