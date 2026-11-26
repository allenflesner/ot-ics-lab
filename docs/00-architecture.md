# Architecture

## Purdue model mapping

| Purdue level | Lab VLAN | Hosts | Real-world equivalent |
|---|---|---|---|
| 5/4 Enterprise | 10 | corp-ws | Office network, email, ERP |
| 3.5 IDMZ | 20 | ot-jump | Jump servers, patch/AV relays, historian replicas |
| 3/2 Supervisory | 30 | ot-hmi, ot-ews | Control room HMIs, engineering workstations, SCADA servers |
| 1 Basic control | 40 | ot-plc | PLCs, RTUs, safety controllers |
| 0 Process | 40 (simulated) | ot-field | Pumps, valves, level transmitters, remote I/O |
| — Security | 50 | elastic, ot-sensor | SOC tooling (out-of-band) |
| — Untrusted | 99 | kali | Internet / adversary |

Addresses are `10.<range number>.<VLAN>.<octet>`; the Ludus router is `.254` in each VLAN.

## The process

Tank T-101 holds 0-1000 units (0-100.0 %). Every second the field I/O sim reads the PLC's coils, applies physics, and writes the new level into holding register 1024:

- Pump P-101 on: +12/tick · constant demand: −4/tick · drain valve V-201 open: −10/tick
- PLC (AUTO): pump ON at ≤ LO setpoint (20 %), OFF at ≥ HI setpoint (80 %)
- Alarms: HIGH ≥ 95 %, LOW ≤ 5 % · overflow when level reaches 100 %

| Modbus object | Address | Tag | Who should write it |
|---|---|---|---|
| Coil | 0 | pump_cmd | PLC logic (AUTO) / HMI (MANUAL) |
| Coil | 1 | drain_valve | HMI |
| Coil | 2 | mode_auto | HMI |
| Coil | 3, 4 | high_alarm, low_alarm | PLC logic only |
| Holding register | 1024 | tank_level | Field I/O only |
| Holding register | 1025, 1026 | hi/lo setpoint | HMI / EWS only |

This table **is** your detection baseline: every attack in the scenarios is a write by the wrong party, to the wrong object, or at the wrong rate.

## Normal traffic (what the sensor learns)

| Flow | Function codes | Rate |
|---|---|---|
| HMI → PLC | FC1 read coils 0-4, FC3 read HR 1024-1026 | every 2 s |
| Field → PLC | FC1 read coils, FC6 write HR 1024 | every 1 s |
| HMI → PLC | FC5 / FC6 | only on operator action (and audit-logged) |
| EWS → PLC :8080 | HTTP | only during program changes |

## Firewall (Ludus router) — legitimate conduits only

```
corp(10) --22--> jump(20) --8080--> hmi(30) --502--> plc(40)
                          --3389--> ews(30) --502,8080--> plc(40)
all ------------8220,9200--> elastic(50)
kali(99) --any--> corp(10)
```
Everything else between VLANs is REJECTed. Scenario toggles in the range config deliberately open holes (assumed breach, flat network) so you can practice detection when prevention fails.

## How the sensor sees traffic

Ludus puts each range on one VLAN-aware Linux bridge (`vmbr1000+N`). Linux bridges have no SPAN feature, so `scripts/ludus-host/ot-span.sh` attaches a second NIC to the sensor on an unused VLAN tag and uses `tc ... action mirred` to copy every frame each lab VM *transmits* to it. Because every packet is sent by some VM, each is captured once. The router is excluded to avoid duplicates of routed packets.

## Data flow into Elastic

| Source | Integration | Index pattern |
|---|---|---|
| Zeek conn/modbus/dnp3/http/notice | Zeek | `logs-zeek.*` |
| ICSNPP extras (`modbus_detailed`, `enip`, `s7comm`...) | Custom Logs (Filestream) | `logs-zeek_icsnpp-*` |
| Suricata eve.json | Suricata | `logs-suricata.eve-*` |
| Process ground truth | Custom Logs (Filestream) | `logs-ot_process-*` |
| HMI operator audit | Custom Logs (Filestream) | `logs-ot_hmi_audit-*` |
| Host telemetry (process, auth, Sysmon) | Elastic Defend, System, Windows | `logs-endpoint.*`, `logs-system.*`, `logs-windows.*` |
