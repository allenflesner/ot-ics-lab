# Scenarios

Each scenario has the same sections: **Objective · ATT&CK for ICS · Setup · Attack · What you should see · Detect · Respond & harden · Journal prompts**.

`N` = your Ludus range number. Attacks run from Kali (`10.N.99.10`) unless noted. On Kali:

```bash
git clone https://github.com/<you>/ot-ics-lab && cd ot-ics-lab/attacks
python3 ot_attack.py --help
```

### Reaching the control zone

The firewall blocks Kali from VLAN 40 by design. Pick one per scenario:
- **Assumed breach** (fast): uncomment `SCENARIO assumed breach` in the range config → `ludus range deploy -t network`. Turn it off afterwards.
- **Earn it** (realistic): complete [07 IT→OT pivot](07-it-to-ot-pivot.md) first and run attacks from the foothold you gain.

Before each run: `ludus testing start` (snapshot + clean revert later), note the UTC time, open the HMI and Kibana side by side.

| # | Scenario | Difficulty |
|---|---|---|
| 00 | [Baseline](00-baseline.md) | ★ |
| 01 | [Recon](01-recon.md) | ★ |
| 02 | [Unauthorized command](02-unauthorized-command.md) | ★★ |
| 03 | [Setpoint tampering](03-setpoint-tampering.md) | ★★ |
| 04 | [Program download](04-program-download.md) | ★★ |
| 05 | [Spoofed telemetry / AitM](05-spoofed-telemetry.md) | ★★★ |
| 06 | [Denial of control](06-denial-of-control.md) | ★★ |
| 07 | [IT→OT pivot](07-it-to-ot-pivot.md) | ★★★ |
