# Detection engineering workflow

OT detection leans on **determinism**: the same hosts send the same function codes to the same addresses at the same rate, forever. Build detections in three layers:

| Layer | Question | Lab example |
|---|---|---|
| **Allow-list / policy** | Is this party allowed to do this at all? | `otlab-0001` write allow-list, `otlab-0003` conduit policy |
| **Behaviour / baseline** | Is this new or unusual? | `otlab-0002` new Modbus client, `otlab-0006` rate threshold |
| **Physics / impact** | Did the process do something it shouldn't? | `otlab-0008` overflow, `otlab-0009` wire write with no operator action |

The physics layer is what makes OT different: even a perfectly spoofed, allow-listed command still has to move the tank.

## Loop for every scenario

1. **Hypothesis** — "An attacker on the corporate network can switch the PLC to MANUAL."
2. **Emulate** — run the scenario; record UTC start/end in the journal.
3. **Observe** — what did Zeek log? Suricata? Agents? Pcap? Note gaps.
4. **Detect** — write or tune the rule (Elastic JSON in `detections/elastic/rules/`, Suricata in the role template, Zeek in `ot-lab.zeek`).
5. **Validate** — re-run; confirm it fires once, with useful context, and stays quiet during 24 h of normal operation.
6. **Harden** — apply the mitigation; re-run and show it's blocked or caught earlier.
7. **Document** — journal entry + commit.

## Rule conventions

- Elastic `rule_id`: `otlab-NNNN-short-name`; tags include `ATT&CK-ICS: Txxxx Name`.
- Suricata SIDs: 9000001-9000999, `metadata: attack_ics Txxxx`.
- Zeek: new notice types in the `OTLab` module.
- Every rule has an investigation note: triage steps, pivots, response.
- Use `__NET__` for the `10.N` prefix in Elastic rules; `import-detections.sh` substitutes it.

## Coverage map

Keep `detections/coverage.md` updated: one row per ATT&CK-for-ICS technique you've emulated, with which layer(s) caught it and the time-to-detect.
