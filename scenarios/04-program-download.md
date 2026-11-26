# 04 — Default credentials & rogue program download

**Objective:** Log in to the OpenPLC runtime with default credentials, stop the PLC, and download modified logic. This is the Stuxnet/Triton class of attack: change what the controller *is*, not just what it's told.

**ATT&CK for ICS:** T0812 Default Credentials · T0843 Program Download · T0821 Modify Controller Tasking · T0881 Service Stop · T0889 Modify Program

## Setup
Assumed-breach toggle on (Kali → VLAN 40 any), or run from the EWS in scenario 07.

## Attack (Kali)

1. Browse to `http://10.N.40.10:8080`, log in `openplc / openplc`.
2. **Stop PLC** (dashboard button). Watch the HMI: values freeze — loss of control.
3. Copy `ansible/roles/ot_openplc/files/water_tank.st` and make a malicious edit, e.g. invert the pump logic or hard-code `hi_setpoint := 1000;` every scan. Upload it under *Programs → Upload Program* with an innocent name ("Water Tank Control v2").
4. Compile, start, and watch the HMI.

## What you should see

| Source | Evidence |
|---|---|
| Suricata | 9000030 (default creds in POST /login), 9000031 (upload from non-EWS), 9000032 (stop_plc), 9000033 (compile) |
| Zeek | `http.log` URIs `/login`, `/stop_plc`, `/upload-program`, `/compile-program?file=...`, `/start_plc`; `files.log` shows the uploaded `.st` |
| Elastic | `otlab-0007`; Elastic Defend on the PLC VM shows `iec2c`/`gcc` compile processes spawned by the runtime |
| Process | tank behaviour changes with no Modbus writes from unauthorized hosts at all |
| Wireshark | *Follow TCP Stream* on 8080 shows the password and the full ST source in clear text |

## Detect — exercise
Extract the uploaded program from the pcap (*File → Export Objects → HTTP*) and diff it against the golden `water_tank.st`. Write a hash-based rule: alert when `file.hash.sha256` of any `.st` seen in `logs-zeek.files-*` isn't in your known-good list.

## Respond & harden
1. Restore the golden program via `ludus range deploy -t user-defined-roles --limit <id>-ot-plc` (remove `/opt/ot-lab/.program_deployed` first) — your "known-good backup restore".
2. Change the OpenPLC credentials (set `ot_openplc_password` and implement the change in the role — good extension task).
3. Confirm 9000031 still fires if the upload comes from anywhere but the EWS.

## Journal prompts
- Which artifacts would you collect for an ICS incident report?
- How would you detect this on a real Siemens/Rockwell PLC where there's no HTTP? (hint: ICSNPP s7comm / ENIP-CIP logs, program-download function codes)
