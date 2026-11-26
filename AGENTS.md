# Instructions for AI agents working on this lab

You have shell access to the Debian host running Ludus and Proxmox. This file
tells you how to build, verify, and document the OT/ICS lab safely. Read it
fully before acting.

## Rules of engagement (non-negotiable)

1. **Scope.** Only touch VMs whose name starts with `<RANGE_ID>-` and only
   send attack traffic to `10.<range_number>.0.0/16`. Never scan, attack, or
   reconfigure anything else on the Proxmox host or the home network.
2. **Destructive actions need a human.** Ask before `ludus range rm`,
   `ludus range deploy` on an already-built range (it may reset VMs),
   `qm destroy`, deleting snapshots, or editing `/etc/network/interfaces`
   on the Proxmox host.
3. **No secrets in git.** Never commit real passwords, API keys, enrollment
   tokens, Ludus API keys, or pcaps. Lab-default passwords in role defaults
   are intentional and documented; anything you generate goes in `.env`
   (git-ignored).
4. **Attack only when asked**, and only the scenario requested. Record the
   start/end time (UTC) of every attack in the session journal.
5. **Don't fix detections by weakening them.** If a rule is noisy, tune with
   explicit allow-lists and document why in the rule's `note` and the journal.

## Build order (with verification gates)

Do not move to the next step until the gate passes. Record gate output in the journal.

| Step | Command | Gate |
|---|---|---|
| 1. Templates | `ludus templates list` | `debian-12-x64-server-template`, `kali-x64-desktop-template` built (+ `win11-22h2-x64-enterprise-template` for full) |
| 2. Roles | `./scripts/ludus-host/upload-roles.sh` | `ludus ansible role list` shows all 5 `ot_*` roles + 2 badsectorlabs roles |
| 3. Config | `ludus range config set -f ludus/range-config.<profile>.yml` | no schema errors |
| 4. Deploy | `ludus range deploy` then `ludus range logs -f` | `ludus range status` shows all VMs; no failed tasks |
| 5. SPAN | `sudo RANGE_ID=<id> ./scripts/ludus-host/ot-span.sh setup` | `ot-span.sh status` shows every lab VM `MIRRORED` |
| 6. Sensor | `ludus range deploy -t user-defined-roles --limit <id>-ot-sensor` | on sensor: `zeekctl status` running; `systemctl is-active suricata pcap-ring` active; `tail /opt/zeek/logs/current/modbus.log` shows FC1/FC3 reads |
| 7. Process | on HMI: `curl -s localhost:8080/api/state` | `connected: true`, `tank_level` changing between polls |
| 8. Fleet | `scripts/elastic/fleet-add-ot-integrations.sh` | Kibana > Fleet: all agents Healthy; Discover shows `logs-zeek.modbus-*` and `logs-suricata.eve-*` |
| 9. Rules | `scripts/elastic/import-detections.sh` | `success_count` = number of rule files; rules enabled |
| 10. Smoke test | from Kali (with assumed-breach toggle on): `python3 attacks/ot_attack.py --target 10.N.40.10 identify` | Suricata SID 9000010 + Zeek `OTLab::Modbus_Recon_Function` + Elastic alert within ~6 min |

### Known fragile points (check these first when something fails)

- **OpenPLC installer** compiles for 10-25 min and occasionally breaks on new
  Debian point releases. Check `/opt/OpenPLC_v3` and `journalctl -u openplc`.
  If `deploy_program.py` can't parse the upload form, the OpenPLC web UI
  changed — upload `water_tank.st` manually via `http://10.N.40.10:8080` and
  report the diff.
- **ICSNPP compiled parsers** (enip, s7comm, bacnet, ACID) are best-effort.
  `zkg list installed` shows what made it. Modbus/DNP3 are script-only and must succeed.
- **SPAN NIC** appears as `ens19` after hot-plug. If missing, reboot the sensor VM.
  `tc` mirrors are re-applied every 30 s by `ot-span.timer`.
- **Elastic versions**: `ludus_elastic_stack_version` and
  `ludus_elastic_agent_version` must match.

## Documentation duties

After every working session, create `journal/YYYY-MM-DD-<topic>.md` from
`journal/TEMPLATE.md`, including: what changed, commands run, gate results,
attack timestamps, alerts that fired (rule name + count), misses, and tuning.
Commit with a clear message (`lab: scenario 02 run, tuned otlab-0001 allow-list`).
Keep the README scenario table and `docs/` in sync with reality — if you
change an IP, port, rule ID or file path, update every reference (`grep -R`).

## Definition of done for a scenario

- Attack reproducible from the scenario doc alone.
- At least one network detection (Zeek or Suricata) **and** one Elastic alert fire.
- Screenshot or exported alert JSON referenced in the journal (no pcaps in git).
- Hardening step applied and the attack re-run to show it's blocked or detected earlier.
