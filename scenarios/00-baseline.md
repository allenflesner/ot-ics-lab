# 00 — Baseline the plant

**Objective:** Know exactly what "normal" looks like before hunting abnormal. Every later detection is a deviation from this.

## Do

1. Let the lab run untouched for at least 1 hour.
2. In Kibana Discover (`logs-zeek.modbus-*`), answer:
   - How many distinct `source.ip` talk Modbus to `10.N.40.10`? (expect 2 in lite / 2-3 in full)
   - Which `zeek.modbus.function` values does each send?
   - Requests per minute per source?
3. In `logs-zeek.connection-*`, list every `source.ip → destination.ip:port` pair that crosses a VLAN boundary. Compare with the firewall rules in `docs/00-architecture.md`. Anything unexpected?
4. In `logs-ot_process-*`, chart `tank.level`. Measure one fill/drain cycle period.
5. In Wireshark, open 5 minutes of pcap → *Statistics → Conversations*. Screenshot it: this is your "golden" conversation map.
6. Let all `otlab-*` rules run for 24 h. Any that fire on normal traffic are false positives — tune them now (expected: `Unknown_Modbus_Client` once per restart of Zeek is fine; nothing else should fire).

## Journal prompts

- Write the baseline as a table (talker, FC, address range, rate). This becomes your allow-list spec.
- Which of these would you be able to see *without* the ICSNPP parsers?
- What would change if the HMI polled with FC4 instead of FC3?
