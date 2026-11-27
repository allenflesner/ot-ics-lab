# Investigation: alert 7e37a35d46f5771b7143a2a669b7f5693d52721f75bddad9eeb2d2014867c01b

Prepared by Alert Investigator. All queries read-only. All times UTC (Allen's local time is US Central, CST = UTC-6 in November: 16:31:44Z = 10:31:44 CST).

## BLUF
- The alerted event is a **false positive for "HMI scanning the PLC"**. The HMI (10.2.30.10) and the field host (10.2.40.20) both sent bursts of SYNs to PLC port 502 and got REJ (connection refused) because the PLC's OpenPLC runtime was stopped. Cause, not a scan by the HMI. Confidence: high (Suricata + Zeek agree on timing and REJ state).
- The same window contains a **true-positive attack sequence from 10.2.99.10** (untrusted zone, no Fleet agent, owner unknown) against the PLC (10.2.40.10): recon, Modbus writes, default-credential login to OpenPLC web (8080), runtime stop, program upload + compile + start, Modbus flood, FC8 listen-only/restart. Confidence: high that it happened (Suricata, Zeek and the OT process log agree); the attacker's identity and intent are unknown.
- Process effect seen in ot_process: mode_auto false 16:27:04-16:28:09; process logging gap 16:30:44-16:31:59; tank high alarm 16:32:43-16:33:01 and overflow at 16:32:48 (level 100%).
- Gaps: ot_hmi_audit has no records in the window; endpoint logs on the PLC/HMI not examined (outside the requested indices); no way to confirm program content that was uploaded.

## 1. The alert
- Alert doc: `.internal.alerts-security.alerts-default-000001`, _id = kibana.alert.uuid = 7e37a35d...c01b
- Detection rule: "Attempted Information Leak" (Elastic prebuilt "External Alerts" rule, rule_id eb079c62-4481-4d6e-9643-3ca499df7aaa, rule uuid 14e4b52d-b086-4e30-a989-3215b0c63587, query `event.kind:alert and not event.module:(endgame or endpoint or cloud_defend)`). The rule just wraps the Suricata alert, so the real detection is the Suricata signature below.
- Alert created 2026-11-27T16:32:35.4Z; original event time 16:31:44.522Z.
- Original Suricata record: `.ds-logs-suricata.eve-default-2026.11.27-000002`, _id `5o7ZHaIB9fWo-dAZXxIN`
- Signature: sid 9000013 "OTLAB Possible Modbus scan - many SYNs to 502", rev 1, attack_ics T0846, severity 2 (medium, risk 47)
- Flow: 10.2.30.10:54428 -> 10.2.40.10:502 tcp, 1 packet (74 bytes), community_id `1:YZcuhqqD6/vr6ciH+QVAjajeFVo=`, sensor allenadm-ot-sensor (interface ens19)
- Same flow in Zeek: `.ds-logs-zeek.connection-default-2026.11.27-000001`, _id `HI7ZHaIB9fWo-dAZXxMN`, state **REJ** ("Connection attempt rejected"), history `Sr`, duration 0.47 ms.
- Host mapping (endpoint metadata): 10.2.30.10 = allenadm-ot-hmi, 10.2.40.10 = allenadm-ot-plc, 10.2.40.20 = allenadm-ot-field, 10.2.20.10 = allenadm-ot-jump, 10.2.50.20 = allenadm-ot-sensor. 10.2.99.10 = no agent, unknown.

## 2. Timeline (window 16:21:44Z - 16:41:44Z, +-10 min of the alert's original event time)
Link labels: C = confirmed (two sources agree), S = single source, I = inferred.

| Time (UTC) | Host / flow | Source index | Event | Record (_id) | Link |
|---|---|---|---|---|---|
| 16:25:27.389 | 10.2.99.10 -> PLC and field | suricata 9000041; zeek.notice | **First suspicious activity.** Untrusted network probes ports 80, 22, 102, 8080, 20000, 44818, 502 on 10.2.40.x. Zeek notice "Control_Zone_Conduit_Violation" | suricata `6I3THaIB9fWo-dAZhZ6u`; zeek.notice `LY3THaIB9fWo-dAZlKeF` (8080, 16:25:27.589) | C |
| 16:25:27.892 | 10.2.99.10 -> 10.2.40.x:502 | suricata 9000013 | Same "many SYNs to 502" signature as the investigated alert, but from 10.2.99.10 (521 hits through 16:31:44) | first `-o3THaIB9fWo-dAZhZ-u` | S |
| 16:25:43.288-.299 | 10.2.99.10 -> PLC:502 | suricata 9000010/9000011; zeek.notice | Modbus device fingerprinting: FC17 (Report Server ID), FC43/14 (Read Device ID). Zeek: Unknown_Modbus_Client, Modbus_Recon_Function | suricata `PY3THaIB9fWo-dAZvrv_`, `P43THaIB9fWo-dAZvrv_`; zeek.notice `943THaIB9fWo-dAZ5Med` | C |
| 16:27:03.352-.449 | 10.2.99.10 -> PLC:502 | zeek.notice; suricata 9000001, 9000003 | Unauthorized Modbus write FC5 (coil write) incl. "mode_auto" coil (AUTO/MANUAL change) | zeek.notice `5Y3VHaIB9fWo-dAZFueu`; suricata `po3VHaIB9fWo-dAZFueu` (9000001), `p43VHaIB9fWo-dAZFueu` (9000003) | C |
| 16:27:04.979 | allenadm-ot-field (PLC outputs) | ot_process | mode_auto = false (first record) | `Bo3VHaIB9fWo-dAZGOgd` | C (matches write above by ~1.5 s) |
| 16:28:08.486-.567 | 10.2.99.10 -> PLC:502 | zeek.notice; suricata 9000003 | Second FC5 write (mode_auto) | zeek.notice `WY3WHaIB9fWo-dAZKPnk`; suricata `G43WHaIB9fWo-dAZAfjL` | C |
| 16:28:09.097 | allenadm-ot-field | ot_process | mode_auto = false (last record); back to auto | `So3WHaIB9fWo-dAZAviZ` | C |
| 16:28:30.964 / 16:28:31.007 | 10.2.99.10 -> PLC:502 | zeek.notice; suricata 9000002 | Modbus WRITE FC6 to setpoint registers from non-HMI host; repeats until 16:36:08 and again 16:41 | zeek.notice `dY3WHaIB9fWo-dAZd_wn`; suricata `vI3WHaIB9fWo-dAZUPoJ` | C |
| 16:30:41.230-.240 | 10.2.99.10 -> PLC:8080 | zeek.http; suricata 9000030 | POST /login to OpenPLC web (UA curl/8.23.0), HTTP 302. Alert: "login attempt with default credentials" | zeek.http `S47YHaIB9fWo-dAZcw2Z`; suricata `BI7YHaIB9fWo-dAZTAyY` | C (login success is **inferred** from later 200/302 replies) |
| 16:30:43.129 / 16:30:45.448 | 10.2.99.10 -> PLC:8080 | zeek.http; suricata 9000032 | GET /stop_plc (HTTP 302), alert "OpenPLC runtime stop requested" | zeek.http `TI7YHaIB9fWo-dAZcw2Z`; suricata `Ro7YHaIB9fWo-dAZcw2Z` | C |
| 16:30:44 - 16:31:59 | allenadm-ot-field | ot_process | **No process records** (last at 16:30:44, next at 16:32:00) | gap seen in 10 s histogram | S, inferred = PLC runtime stopped |
| 16:30:45.746 / 16:30:46.471 | field (10.2.40.20) and HMI (10.2.30.10) -> PLC:502 | zeek.connection | First REJ from each, ~1 s after the stop request. 42 REJ each through 16:33:42 | state REJ docs, query Q8 | C |
| 16:30:52 - 16:30:59 | 10.2.99.10 -> PLC:8080 | zeek.http / zeek.weird | GET /upload-program (200); weird truncated_tcp_payload | zeek.http `Yo7YHaIB9fWo-dAZcw2Z`, `d47YHaIB9fWo-dAZmw5x` | S |
| 16:31:05.767 - 16:31:43.805 | 10.2.40.20 -> PLC:502 | suricata 9000013 | 10 "many SYNs" alerts from the field host (retry storm into a closed port) | sid 9000013 query Q6 | C (REJ state) |
| 16:31:06.489 - **16:31:44.522** | 10.2.30.10 -> PLC:502 | suricata 9000013; zeek.connection | 10 "many SYNs" alerts from the HMI; **16:31:44.522 is the investigated alert**, flow state REJ | suricata `5o7ZHaIB9fWo-dAZXxIN`; zeek `HI7ZHaIB9fWo-dAZXxMN` | C |
| 16:31:47.825 - .868 | 10.2.99.10 -> PLC:8080 | zeek.http; suricata 9000030/31/33 | New login (Python-urllib/3.14), POST /upload-program, POST /upload-program-action, GET /compile-program?file=387188.st (all HTTP 200). Alerts: default credentials, program upload from non-EWS host, program compile/launch | zeek.http `5Y7ZHaIB9fWo-dAZhhQr`, `5o7ZHaIB9fWo-dAZhhQr`; suricata `CI7ZHaIB9fWo-dAZXxMN` (9000031), `Do7ZHaIB9fWo-dAZXxMN` (9000033) | C |
| 16:31:58.009 | 10.2.99.10 -> PLC:8080 | zeek.http | GET /start_plc (HTTP 302): runtime started again | `HY7ZHaIB9fWo-dAZhhUr` | S |
| 16:32:00.482 | allenadm-ot-field | ot_process | Process records resume; low_alarm = true first seen | `qo7ZHaIB9fWo-dAZvBYQ` | C (PLC back) |
| 16:32:35.4 | Kibana | alerts index | Alert 7e37a35d... created (rule "Attempted Information Leak") | alert doc | C |
| 16:32:43.562 - 16:33:01.598 | allenadm-ot-field | ot_process | high_alarm = true (level 94.8-96%) | `_I7aHaIB9fWo-dAZMRtR` ... `147aHaIB9fWo-dAZfx56` | S |
| 16:32:48.572 | allenadm-ot-field | ot_process | tank.overflow = true, level 100% | `VI7aHaIB9fWo-dAZWB1m` | S |
| 16:33:42.664 | HMI -> PLC:502 | zeek.connection | Last REJ from HMI (field: 16:33:42.029) | query Q8 | C |
| 16:34:08.557, 16:35:14.836 | 10.2.99.10 -> PLC:502 | zeek.notice | More unauthorized FC6 writes | `9o7bHaIB9fWo-dAZlSkZ`, `r47cHaIB9fWo-dAZgDw1` | S |
| 16:38:55.314 - 16:39:25 | 10.2.99.10 -> PLC:502 | suricata 9000022; 2250008 | Modbus request flood (3 alerts); "Modbus Data mismatch" 34,460 hits in 30 s | `GY7fHaIB9fWo-dAZ03fk` | C |
| 16:39:34.090 / 16:39:36.995 | 10.2.99.10 -> PLC:502 | suricata 9000020/21; zeek.notice | Modbus FC8/4 Force Listen Only Mode, then FC8/1 Restart Communications | suricata `mZHhHaIB9fWo-dAZQapX`, `q5HhHaIB9fWo-dAZQapX`; zeek.notice `MpDgHaIB9fWo-dAZcFeI` | C |
| 16:40:52.498 / 16:40:54.484 | 10.2.99.10 -> PLC:8080/502 | zeek.http; suricata 9000041/12 | Fresh /login GET (curl) and another conduit violation | zeek.http `0JHhHaIB9fWo-dAZ3LiZ` | S |

Attack-technique tags below come from the `attack_ics` field on the matching Suricata alerts (rule-supplied, not my inference): T0846, T0888, T0855, T0858, T0836, T0812, T0881, T0843, T0821, T0814, T0816, T0886.

## 3. Verdict
- Investigated alert (sid 9000013, HMI -> PLC:502, 16:31:44.522): **false positive / benign side effect**. Evidence: Zeek state REJ, PLC refused the connection; first REJ from both HMI and field host came about 1 s after "/stop_plc" (16:30:43-45) from 10.2.99.10; both hosts retry on a fixed cadence; the HMI's connection stats before today were normal (earlier same-day burst at ~15:23 also shows REJ=42, which suggests an earlier runtime stop; not investigated).
- The surrounding activity from 10.2.99.10: **true positive** (unauthorized access, writes, PLC runtime stop, program upload/start, flood).
- Unknown: who/what 10.2.99.10 is (no agent; could be an authorised test, which I cannot tell from logs); what logic the uploaded program contains (file `387188.st`); whether the 16:32:48 overflow was caused by the stop/restart or by the setpoint writes (both are candidates).
- Not checked: ot_hmi_audit (0 docs in window), endpoint events on allenadm-ot-plc/-hmi/-field, Linux auth logs, and why field host 10.2.40.20 started "non-HMI setpoint write" alerts (573) at 16:31:59 right after the PLC restart (inferred: simulator resuming writes; not confirmed).

## 4. Replicable steps (Kibana Dev Tools, or curl against Elasticsearch)
Use the Dev Tools console in Kibana (`GET`/`POST` lines below). Window: `2026-11-27T16:21:44Z` to `2026-11-27T16:41:44Z`. Replace times for other alerts.

Q1. Find the alert (fields: `_id`, `kibana.alert.uuid`)
```
POST /.internal.alerts-security.alerts-default-*,.alerts-security.alerts-*/_search
{"query":{"bool":{"should":[{"ids":{"values":["7e37a35d46f5771b7143a2a669b7f5693d52721f75bddad9eeb2d2014867c01b"]}},{"term":{"kibana.alert.uuid":"7e37a35d46f5771b7143a2a669b7f5693d52721f75bddad9eeb2d2014867c01b"}}],"minimum_should_match":1}}}
```
Read: `kibana.alert.rule.name`, `kibana.alert.original_time`, `source.ip`, `destination.ip`, `suricata.eve.alert.signature(_id)`, `network.community_id`, `agent.name`.

Q2. Same flow in all network sources (community_id)
```
POST /logs-suricata.eve-*,logs-zeek.*,logs-zeek_icsnpp-*/_search
{"sort":[{"@timestamp":"asc"}],"query":{"term":{"network.community_id":"1:YZcuhqqD6/vr6ciH+QVAjajeFVo="}}}
```
KQL (Discover, data view logs-*): `network.community_id : "1:YZcuhqqD6/vr6ciH+QVAjajeFVo="`

Q3. Record counts per index in the window for both IPs
```
POST /logs-suricata.eve-*,logs-zeek.*,logs-zeek_icsnpp-*,logs-ot_process-*,logs-ot_hmi_audit-*/_search?size=0
{"query":{"bool":{"filter":[{"range":{"@timestamp":{"gte":"2026-11-27T16:21:44Z","lte":"2026-11-27T16:41:44Z"}}},{"bool":{"should":[{"terms":{"source.ip":["10.2.30.10","10.2.40.10"]}},{"terms":{"destination.ip":["10.2.30.10","10.2.40.10"]}},{"terms":{"related.ip":["10.2.30.10","10.2.40.10"]}}],"minimum_should_match":1}}]}},"aggs":{"idx":{"terms":{"field":"_index"}}}}
```
Note: ot_process/ot_hmi_audit have no IP fields (they use `ot.plc_ip`, `host.name`); correlate them by time and host.

Q4. All Suricata alerts for the IPs, grouped
```
POST /logs-suricata.eve-*/_search?size=0
{"query":{"bool":{"filter":[{"range":{"@timestamp":{"gte":"2026-11-27T16:21:44Z","lte":"2026-11-27T16:41:44Z"}}},{"term":{"suricata.eve.event_type":"alert"}},{"bool":{"should":[{"terms":{"source.ip":["10.2.30.10","10.2.40.10"]}},{"terms":{"destination.ip":["10.2.30.10","10.2.40.10"]}}],"minimum_should_match":1}}]}},"aggs":{"s":{"multi_terms":{"terms":[{"field":"suricata.eve.alert.signature_id"},{"field":"suricata.eve.alert.signature"},{"field":"source.ip"},{"field":"destination.ip"},{"field":"destination.port"}],"size":30}}}}
```
Q5. First and last alert per OTLAB signature, with _id (adds `top_hits`, sort `@timestamp` asc/desc, filter `suricata.eve.alert.signature_id >= 9000000`).

Q6. History of the investigated signature by source
```
POST /logs-suricata.eve-*/_search?size=0
{"query":{"term":{"suricata.eve.alert.signature_id":9000013}},"aggs":{"src":{"terms":{"field":"source.ip"},"aggs":{"h":{"date_histogram":{"field":"@timestamp","fixed_interval":"1h"}}}}}}
```
Q7. Zeek notice / weird / http / known_services / software for 10.2.99.10, .30.10, .40.10, .40.20 in the window
```
POST /logs-zeek.notice-*,logs-zeek.weird-*,logs-zeek.http-*,logs-zeek.known_services-*,logs-zeek.software-*/_search?size=60
{"sort":[{"@timestamp":"asc"}],"query":{"bool":{"filter":[{"range":{"@timestamp":{"gte":"2026-11-27T16:21:44Z","lte":"2026-11-27T16:41:44Z"}}},{"bool":{"should":[{"terms":{"source.ip":["10.2.99.10","10.2.30.10","10.2.40.10","10.2.40.20"]}},{"terms":{"destination.ip":["10.2.99.10","10.2.30.10","10.2.40.10","10.2.40.20"]}}],"minimum_should_match":1}}]}}}
```
Q8. Connection states from HMI and field host to PLC:502 (shows REJ burst)
```
POST /logs-zeek.connection-*/_search?size=0
{"query":{"bool":{"filter":[{"range":{"@timestamp":{"gte":"2026-11-27T16:10:00Z","lte":"2026-11-27T16:45:00Z"}}},{"terms":{"source.ip":["10.2.30.10","10.2.40.20"]}},{"term":{"destination.ip":"10.2.40.10"}},{"term":{"destination.port":502}}]}},"aggs":{"src":{"terms":{"field":"source.ip"},"aggs":{"t":{"date_histogram":{"field":"@timestamp","fixed_interval":"2m"},"aggs":{"st":{"terms":{"field":"zeek.connection.state"}}}}}}}}
```
First REJ per source: same query with an added filter `{"term":{"zeek.connection.state":"REJ"}}` and aggs `min`/`max` on `@timestamp`.

Q9. OT process state (ot_process): per 2-minute bucket, terms on `plc_outputs.mode_auto`, `plc_outputs.pump_cmd`, `plc_outputs.high_alarm`, `plc_outputs.low_alarm`, avg `tank.level_pct`; first/last record for each abnormal state by sorting on `@timestamp` with a term filter (e.g. `plc_outputs.mode_auto:false`, `tank.overflow:true`). Gap check: `date_histogram` fixed_interval 10s with `min_doc_count:0` over 16:30:20-16:32:30.

Q10. ot_hmi_audit in window: `POST /logs-ot_hmi_audit-*/_search` with the same time range filter. Result: 0 hits.

Q11. Host-to-IP map: `POST /metrics-endpoint.metadata_current_default/_search?size=20` with `_source` of `host.name`, `host.ip`.

## 5. Suggested follow-ups (all need Allen's yes before any change; nothing was changed)
- Look at allenadm-ot-plc endpoint events (`logs-endpoint.events.process-*`, `.network-*`) and `logs-system.auth-*` around 16:30-16:32 for the OpenPLC process restart and the uploaded file `387188.st`.
- Tell whether 10.2.99.10 is an authorised test host; if yes, this is an exercise and the verdict changes to "expected".
- Tune the 9000013 rule to ignore or lower severity for REJ/known-supervisory sources (a suggestion; no rule was changed).
- Replace the Elastic key used by the investigator with a read-only one (current key has write/delete/manage). Allen has decided to keep the current key for this lab, so this is optional.
