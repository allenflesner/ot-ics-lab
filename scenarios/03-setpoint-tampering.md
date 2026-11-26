# 03 — Setpoint tampering (the quiet attack)

**Objective:** Leave the PLC in AUTO but move the high setpoint to 99 %. The plant still looks like it is "working" — just closer to the edge. Harder to notice than scenario 02.

**ATT&CK for ICS:** T0836 Modify Parameter · T0832 Manipulation of View (if paired with 05)

## Attack (Kali)

```bash
python3 ot_attack.py --target 10.N.40.10 read
python3 ot_attack.py --target 10.N.40.10 write-reg 1025 990   # HI setpoint 80 % -> 99 %
python3 ot_attack.py --target 10.N.40.10 write-reg 1026 900   # LO setpoint 20 % -> 90 % (tank lives near the top)
```
Watch the cycle: the high alarm now trips every cycle, and with BASE_DEMAND changes or a closed drain, overflow is one bad day away.

**Variant — insider via HMI:** browse to the HMI from the jump host and change setpoints with the UI. Same Modbus bytes, but now the source is the HMI and there's an audit-log entry. Which rules still fire?

## What you should see

| Source | Evidence |
|---|---|
| Suricata | 9000002 (setpoint write from non-HMI), 9000001 |
| Zeek | `modbus_detailed.log` FC6 address 1025 value 990 |
| Elastic | `otlab-0001`; for the HMI variant only the **process** shows it (alarm rate change) and the HMI audit log records who |
| Wireshark | `modbus.func_code == 6 && modbus.reference_num == 1025` |

## Detect — exercise
Write a rule for *setpoint outside engineering limits* regardless of source: ES|QL over `logs-zeek_icsnpp-*` (`modbus_detailed`) where `address IN (1025, 1026)` and the written value > 900 or < 100. This is a "process-aware" detection that also catches the insider variant.

## Respond & harden
Restore 800/200 from the HMI. Then add bounds-checking to the PLC program (clamp setpoints in ST) and redeploy via the EWS — defense in the controller itself.

## Journal prompts
- Why are parameter changes more dangerous than obvious commands?
- How would you baseline "normal" setpoint changes in a plant with real operators?
