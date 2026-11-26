# Elastic Security setup

The `badsectorlabs.ludus_elastic_container` role deploys Elasticsearch, Kibana and Fleet Server on `10.N.50.10` and creates an agent policy with Elastic Defend + Windows. Every other VM gets an Elastic Agent enrolled into that policy.

Kibana: `https://10.N.50.10:5601` · user `elastic` · password from the range config.

## 1. Add network integrations (scripted)

```bash
export KIBANA_URL=https://10.N.50.10:5601 ELASTIC_PASSWORD='ChangeMe-OTlab-2026'
./scripts/elastic/fleet-add-ot-integrations.sh
```
Adds **Zeek**, **Suricata** and **System** to the lab policy with default inputs. Hosts without those log files ship nothing for them.

## 2. Add custom JSON logs (do this by hand — it's a skill worth having)

Kibana → **Integrations** → **Custom Logs (Filestream)** → *Add* → choose the lab agent policy. Create one integration per row:

| Integration name | Paths | Dataset name |
|---|---|---|
| otlab-icsnpp | `/opt/zeek/logs/current/modbus_*.log`<br>`/opt/zeek/logs/current/enip*.log`<br>`/opt/zeek/logs/current/cip*.log`<br>`/opt/zeek/logs/current/s7comm*.log` | `zeek_icsnpp` |
| otlab-process | `/var/log/ot-process/*.jsonl` | `ot_process` |
| otlab-hmi-audit | `/var/log/ot-hmi/*.jsonl` | `ot_hmi_audit` |

In **Advanced options → Parsers** paste:
```yaml
- ndjson:
    target: ""
    overwrite_keys: true
    add_error_key: true
```
For `otlab-icsnpp`, also add a processor so Zeek's dotted keys become ECS-ish fields (optional but nicer):
```yaml
- rename:
    fields:
      - {from: "id.orig_h", to: "source.ip"}
      - {from: "id.resp_h", to: "destination.ip"}
      - {from: "id.resp_p", to: "destination.port"}
    ignore_missing: true
    fail_on_error: false
```
Verify in **Discover**: `logs-ot_process-*` should show a document per second with `tank.level`.

## 3. Import detections

```bash
LAB_NET=10.N ./scripts/elastic/import-detections.sh
```
Then **Security → Rules → Detection rules**, filter tag `OT-ICS Lab`. Each rule has an investigation guide (`note`).

## 4. Enable useful prebuilt rules

Security → Rules → *Add Elastic rules*. Good ones for this lab: Linux SSH brute force, potential SSH password grabbing, RDP from unusual source, Elastic Defend malware/behavior protections (on EWS/corp-ws).

## 5. Build an OT dashboard

Suggested panels (Lens):
- `tank.level` over time (line) with `tank.overflow` markers — the physical truth
- Modbus function codes by `source.ip` (`logs-zeek.modbus-*`, stacked bar)
- Unique Modbus clients (metric) — should be exactly 3
- Suricata OTLAB alerts by signature (table)
- HMI audit commands vs. wire writes per minute (two lines on one chart — gaps between them are scenario 5)

Export the dashboard (Stack Management → Saved Objects → Export) into `detections/elastic/dashboards/` so it's versioned.

## Useful ES|QL hunts

```esql
// Who writes to the PLC, and how?
FROM logs-zeek.modbus-*
| WHERE zeek.modbus.function LIKE "WRITE*"
| STATS n = COUNT(*) BY source.ip, zeek.modbus.function
| SORT n DESC

// Talkers into the control zone
FROM logs-zeek.connection-*
| WHERE CIDR_MATCH(destination.ip, "10.N.40.0/24")
| STATS conns = COUNT(*), ports = VALUES(destination.port) BY source.ip

// Tank behaviour per 5 minutes
FROM logs-ot_process-*
| STATS min = MIN(tank.level), max = MAX(tank.level), overflow = MAX(TO_INTEGER(tank.overflow))
    BY bucket = BUCKET(@timestamp, 5 minutes)
| SORT bucket
```
