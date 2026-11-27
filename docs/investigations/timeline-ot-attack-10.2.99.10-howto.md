# Timeline "OT lab attack 10.2.99.10 - 2026-11-27 16:20-16:41Z"

Created by Alert Investigator (one write, approved by Allen via Lab Manager, for this task only).
- Timeline id: `63759501-b00a-4604-93ad-be5f4618447c` (Kibana 8.17.4, Security > Timelines, type: default, saved as a query timeline, not pinned events)
- Open: Kibana > Security > Timelines > "OT lab attack 10.2.99.10 - 2026-11-27 16:20-16:41Z". Direct link (format not tested in a browser): https://localhost:5601/app/security/timelines?timeline=(id:'63759501-b00a-4604-93ad-be5f4618447c',isOpen:!t)
- Absolute range saved: 2026-11-27T16:20:00Z to 16:41:00Z (Kibana shows it in your browser time zone, US Central = 10:20-10:41)
- Match count when created: 3,225 events (Elasticsearch count of the same query): zeek.modbus 1,218; Suricata 1,217; Elastic alerts 664; ot_process 86; zeek.notice 18; zeek.http 15; zeek.weird 7. Verified through the API read-back (title, range, indices, query match the file); not opened in the Kibana UI.
- Sorted oldest first. Columns: @timestamp, event.dataset, message, kibana.alert.rule.name, suricata.eve.alert.signature, zeek.notice.msg, url.original, zeek.modbus.function, source.ip, destination.ip, host.name, tank.level_pct.
- Indices: logs-suricata.eve-*, logs-zeek.*, logs-zeek_icsnpp-*, logs-ot_process-*, logs-ot_hmi_audit-*, .alerts-security.alerts-default

## What is in it, and what was left out
In: Suricata alerts from 10.2.99.10 for SIDs 9000001, 9000002, 9000003, 9000010, 9000011, 9000020, 9000021, 9000022, 9000030-9000033; Zeek http / notice / weird for 10.2.99.10; Zeek modbus from 10.2.99.10 except READ_HOLDING_REGISTERS; ot_process records with high alarm, low alarm, overflow or mode_auto=false; Elastic alerts from 10.2.99.10 except rules "OT Lab control or conduit policy violation" and "Attempted Administrator Privilege Gain"; the investigated alert 7e37a35d....
Out (too noisy): 68,926 routine READ_HOLDING_REGISTERS reads; ~3,600 port-scan connection records (zeek.connection); 35k zeek_icsnpp records; sids 9000012/9000013/9000041 scan/conduit alerts; those two excluded alert rules (about 3,860 alerts). Drop the `not ...` parts of the query to include them.

## KQL (paste in the timeline query bar)
```
(data_stream.dataset:"suricata.eve" and source.ip:"10.2.99.10" and suricata.eve.alert.signature_id:(9000001 or 9000002 or 9000003 or 9000010 or 9000011 or 9000020 or 9000021 or 9000022 or 9000030 or 9000031 or 9000032 or 9000033)) or (data_stream.dataset:(zeek.http or zeek.notice or zeek.weird) and (source.ip:"10.2.99.10" or destination.ip:"10.2.99.10")) or (data_stream.dataset:"zeek.modbus" and source.ip:"10.2.99.10" and not zeek.modbus.function:"READ_HOLDING_REGISTERS") or (data_stream.dataset:"ot_process" and (tank.overflow:true or plc_outputs.high_alarm:true or plc_outputs.low_alarm:true or plc_outputs.mode_auto:false)) or (kibana.alert.uuid:* and source.ip:"10.2.99.10" and not kibana.alert.rule.name:("OT Lab control or conduit policy violation" or "Attempted Administrator Privilege Gain")) or kibana.alert.uuid:"7e37a35d46f5771b7143a2a669b7f5693d52721f75bddad9eeb2d2014867c01b"
```

## Manual steps in Kibana (fallback, if the timeline is missing or you want to rebuild it)
1. Kibana menu > Security > Timelines.
2. Click "Create new timeline" (the + / New button, "Default timeline").
3. In the timeline, open the data-source picker next to the query bar and select the indices listed above (or "Security default" plus `.alerts-security.alerts-default`, `logs-zeek.*`, `logs-suricata.eve-*`, `logs-zeek_icsnpp-*`, `logs-ot_process-*`).
4. Click the date picker at the top of the timeline > "Absolute" tab. Start: Nov 27, 2026 16:20:00.000 UTC; End: Nov 27, 2026 16:41:00.000 UTC. Kibana shows your browser time zone: for US Central that is 10:20:00 to 10:41:00. Click Update.
5. In the KQL query bar, paste the KQL above (set the dropdown to "Filter"/KQL) and press Enter. You should see about 3,225 events.
6. Optional: sort by @timestamp ascending, and use the Fields button to add the columns listed above.
7. To keep only chosen events: in the results, drag an event's value (such as source.ip) into the "Drop anything highlighted here" row, or use the row's "Pin event" (pin icon) so it stays after you change the query. Pinned events are kept with the timeline.
8. Click the title ("Untitled timeline") or the Save icon > set Title `OT lab attack 10.2.99.10 - 2026-11-27 16:20-16:41Z`, add a description > Save.

## Saved search fallback (Discover)
If the Timeline API had not worked, the same KQL and time range would be saved as a Discover saved search on a data view covering `logs-*`. Not needed; the timeline was created.
