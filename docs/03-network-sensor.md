# Network sensor: Zeek, Suricata, pcap

Passive monitoring is the default in OT because you can't put agents on PLCs and you must never risk the process with active scanning. The sensor sees a copy of every frame and never transmits on the span interface.

## Zeek

- Installed from the official OBS repo at `/opt/zeek`, managed by `zeekctl` (`zeek.service`, cron every 5 min).
- JSON logs in `/opt/zeek/logs/current/`.
- **CISA ICSNPP** packages extend protocol visibility:
  - `icsnpp-modbus` → `modbus_detailed.log` (every request/response with addresses and values), `modbus_read_write_multiple_registers.log`, `modbus_mask_write_register.log`, `modbus_read_device_identification.log`
  - `icsnpp-dnp3`, and best-effort compiled parsers `icsnpp-enip`, `icsnpp-s7comm`, `icsnpp-bacnet`, plus **ACID** (MITRE's ATT&CK-for-ICS Zeek detections)
- **Lab detections** in `ot-lab.zeek` raise notices:

| Notice | Fires when |
|---|---|
| `OTLab::Unauthorized_Modbus_Write` | write FC from a host outside the HMI/field/EWS allow-list |
| `OTLab::Unknown_Modbus_Client` | anyone not in the known-client list speaks Modbus |
| `OTLab::Modbus_Recon_Function` | FC 8 / 17 / 43 (diagnostics, report ID, device ID) |
| `OTLab::Control_Zone_Conduit_Violation` | TCP connection into VLAN 40 from outside VLANs 30/40/50 |

Allow-lists live in `otlab-site.zeek` (templated from role vars).

Useful commands:
```bash
cd /opt/zeek/logs/current
jq -c 'select(.func|test("WRITE")) | {ts, src:."id.orig_h", func}' modbus.log
jq -c '{ts, src:."id.orig_h", unit_id, func, address, quantity, values}' modbus_detailed.log | tail
jq -c '{note, msg, src}' notice.log
zeek-cut -d ts id.orig_h id.resp_h id.resp_p service < conn.log   # if you switch back to TSV
```

## Suricata

- Suricata 7 from bookworm-backports, af-packet on `ens19`, Modbus/DNP3/ENIP app-layer parsers enabled via `--set`.
- Ruleset = ET Open + lab rules (`suricata-update --local /etc/suricata/rules/ot-lab.rules`), refreshed weekly.
- Lab rules use SIDs **9000001-9000999** with `metadata: attack_ics Txxxx`. Source is the Jinja template `ansible/roles/ot_sensor/templates/ot-lab.rules.j2` (rendered with your range IPs).

```bash
sudo tail -f /var/log/suricata/fast.log
sudo jq -c 'select(.event_type=="alert") | {ts:.timestamp, sid:.alert.signature_id, sig:.alert.signature, src:.src_ip, dst:.dest_ip}' /var/log/suricata/eve.json
sudo suricatasc -c ruleset-stats     # rules loaded / failed
```
If a rule fails to load, `journalctl -u suricata | grep -i error` shows the line — Modbus keyword syntax differs slightly between Suricata versions.

## Rolling pcap

`pcap-ring.service` keeps the last 50 × 100 MB (~5 GB) in `/var/pcap/otlab.pcap*`. Carve out a scenario window:
```bash
sudo ./scripts/sensor/pull-pcap.sh "2026-11-25 21:00:00" "2026-11-25 21:15:00" /tmp/s02.pcap
```
Then open it in Wireshark with the lab profile ([05-wireshark.md](05-wireshark.md)).

## Troubleshooting

| Symptom | Check |
|---|---|
| No `modbus.log` | `sudo ot-span.sh status` on host; `sudo tcpdump -ni ens19 port 502 -c 5` on sensor |
| Only one direction of traffic | Expected for router-originated flows; for VM↔VM both sides should appear — confirm both VMs are `MIRRORED` |
| `ens19` missing | `qm config <sensor id> \| grep net1`; reboot sensor VM |
| Zeek crashed | `zeekctl diag` |
| Huge conn.log from agents | Adjust `ot_sensor_bpf` in role defaults |
