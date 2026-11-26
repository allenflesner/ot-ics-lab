# 2026-11-26 — Lite build on Ludus: fixes and checks

**Profile:** lite · **Range:** 2 (allenadm) · **Operator:** human (Allen) with agent (Lab Manager)

## Goal
Build the lite OT/ICS lab on Ludus, then verify detections.

## Changes made (repo)
- ot_sensor: ca-certificates added to base packages; Zeek ignore_checksums (SPAN frames); Suricata Modbus parser enabled in suricata.yaml; enable list (enable.conf) for suricata-update; rule SID 9000003 simplified to any coil write.
- ot_openplc: ca-certificates added to prerequisites.
- scripts/ludus-host/ot-span.sh: applied on the host with a fix that clears a stale mirror filter before re-adding (see host copy).

## Changes made (live, not in repo)
- Ludus Elastic container role on the host: Kibana healthcheck accepts HTTP/1.1 (patched in the upstream role copy).
- Ludus Elastic agent role on the host: the uninstall step tolerates failure (ignore_errors).
- Suricata: eve-log modbus transaction logging enabled on the sensor (suricata.yaml).
- Zeek: local.zeek checksum setting applied on the sensor role.

## Attack log (UTC)
| Start | End | Technique | Command / action | Source host |
|---|---|---|---|---|
| 23:03:18 | 23:03:21 | T0855 / T0858 | write-coil 2 0 (AUTO to MANUAL) | 10.2.99.10 (kali) |
| 23:04:27 | 23:04:30 | restore | write-coil 2 1 (MANUAL to AUTO) | 10.2.99.10 (kali) |

## What fired
| Time to detect | Source | Rule / SID / notice | Count | True positive? |
|---|---|---|---|---|
| <60 s | Suricata | 9000001 | 3 | yes |
| <60 s | Suricata | 9000003 | 2 | yes |
| <60 s | Zeek | OTLab::Unauthorized_Modbus_Write | 1 | yes |

## What was missed and why
- Suricata 9000003 did not fire at first: the rule was commented out by suricata-update because the Modbus parser was disabled in suricata.yaml, then the coil-table form with an address did not match. Fixed.
- Zeek dropped SPAN frames with offloaded checksums until ignore_checksums was set.

## Tuning applied
- SID 9000003: removed the address qualifier (matches any coil write).

## Hardening applied & re-test result
- Assumed-breach rule turned back off after each test. Re-test not yet run with the firewall at its normal setting.

## Lessons
- SPAN capture needs checksum handling on both Zeek and Suricata.
- suricata-update silently disables rules that fail to load; check the enable list and validate with suricata -T.
- Ludus role uninstall steps can fail on stale Fleet policy conditions; keep the fix in the role, not the VM.
