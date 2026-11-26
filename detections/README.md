# Detections

| Layer | Location | Format |
|---|---|---|
| Elastic Security rules | [`elastic/rules/`](elastic/rules/) | Kibana detection rule JSON (`__NET__` placeholder) — import with `scripts/elastic/import-detections.sh` |
| Suricata | [`ansible/roles/ot_sensor/templates/ot-lab.rules.j2`](../ansible/roles/ot_sensor/templates/ot-lab.rules.j2) | Jinja-templated rules, SIDs 9000001-9000999 |
| Zeek | [`ansible/roles/ot_sensor/files/ot-lab.zeek`](../ansible/roles/ot_sensor/files/ot-lab.zeek) + [`otlab-site.zeek.j2`](../ansible/roles/ot_sensor/templates/otlab-site.zeek.j2) | Notice framework script + templated allow-lists |

The Suricata and Zeek sources live inside the role because Ludus uploads each role directory on its own. Edit them there.

## Elastic rules

| rule_id | Type | Severity | ATT&CK for ICS |
|---|---|---|---|
| otlab-0001-modbus-write-unauthorized | ES\|QL | critical | T0855 |
| otlab-0002-new-modbus-client | new terms | medium | T0846 |
| otlab-0003-conduit-violation | query | high | T0886 |
| otlab-0004-suricata-otlab-signature | query | high | (per signature) |
| otlab-0005-zeek-otlab-notice | query | high | (per notice) |
| otlab-0006-modbus-flood | threshold | high | T0814, T0829 |
| otlab-0007-openplc-admin-action | query | high | T0843, T0881 |
| otlab-0008-tank-overflow | ES\|QL | critical | T0879, T0880 |
| otlab-0009-write-without-hmi-audit | ES\|QL | high | T0856, T0830 |

See [coverage.md](coverage.md) for what's been validated.
