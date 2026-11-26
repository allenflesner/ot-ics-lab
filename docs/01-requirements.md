# Requirements

## Host

| Profile | RAM (allocated) | vCPU | Disk | Templates |
|---|---|---|---|---|
| **lite** | ~30 GB | ~18 | ~250 GB | debian-12, kali |
| **full** | ~42 GB | ~24 | ~450 GB | debian-12, kali, win11-22h2 |

vCPU can be overcommitted; RAM should not be (Elasticsearch suffers first). If memory is tight, drop `elastic` to 8 GB and `kali` to 4 GB.

## Software

- Ludus installed on Proxmox (Debian host), with the `ludus` CLI configured for your user
- Root shell on the Proxmox host (for `ot-span.sh`)
- Internet access from the range during build (apt, GitHub, Zeek OBS repo, Elastic artifacts)

## Templates

```bash
ludus templates list
ludus templates build -n debian-12-x64-server-template
ludus templates build -n kali-x64-desktop-template
ludus templates build -n win11-22h2-x64-enterprise-template   # full profile only
ludus templates logs -f
```

## Optional: use your existing Elastic instead

If you'd rather send data to an Elastic deployment you already run, remove the `elastic` VM from the config, set `ludus_elastic_fleet_server` and `ludus_elastic_enrollment_token` in `global_role_vars`, and change the "Agents to Fleet" firewall rule to `vlan_dst: public` with your Fleet port. Keep detections in a dedicated space so lab alerts don't mix with real ones.
