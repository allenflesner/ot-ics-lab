# 01 — OT discovery from a foothold

**Objective:** An adversary who has reached the control zone maps the devices and fingerprints the PLC. Catch it before anything is written.

**ATT&CK for ICS:** T0846 Remote System Discovery · T0888 Remote System Information Discovery · T0842 Network Sniffing (optional)

## Setup
Assumed-breach toggle on (or run from your 07 foothold).

## Attack (Kali)

```bash
# Host & service discovery (TCP connect scan - no raw SYN tricks needed)
nmap -sT -Pn -n -p 22,80,102,502,8080,20000,44818 10.N.40.0/24 -oN /tmp/s01-scan.txt

# Modbus fingerprinting
nmap -sT -Pn -p 502 --script modbus-discover 10.N.40.10
python3 ot_attack.py --target 10.N.40.10 identify

# Read the process image (what does each register mean?)
python3 ot_attack.py --target 10.N.40.10 read
watch -n 2 python3 ot_attack.py --target 10.N.40.10 read
```

## What you should see

| Source | Evidence |
|---|---|
| Suricata | SID 9000012 (connection into control zone), 9000013 (SYN burst to 502), 9000010 (FC17), 9000011 (FC43), plus ET SCAN rules |
| Zeek | `notice.log`: `OTLab::Control_Zone_Conduit_Violation`, `OTLab::Unknown_Modbus_Client`, `OTLab::Modbus_Recon_Function`; `conn.log` full of `S0`/`REJ` states |
| Elastic | `otlab-0002` new Modbus client, `otlab-0003` conduit violation, `otlab-0004`, `otlab-0005` |
| Wireshark | `modbus.func_code in {17 43}`; *Conversations* shows a new talker; exceptions where FC43 is unsupported |

## Detect — exercise
Write an ES\|QL hunt that lists every source that touched more than 5 distinct ports on VLAN 40 in 10 minutes. Is that a better scan detector than 9000013?

## Respond & harden
- Kill the conduit (turn the toggle off); confirm 9000012 stops.
- Discuss: OpenPLC answers FC17/43 to anyone. Real PLCs often do too — what compensating control would you put in front (protocol-aware firewall, Modbus FC allow-list)?

## Journal prompts
- Time from first packet to first alert in Elastic?
- Which signal would you page on at 3 a.m., and which would you leave as context?
