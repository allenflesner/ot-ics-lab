# Coverage map

Update after each validated scenario run. "Validated" = fired during an attack run AND stayed quiet across 24 h of baseline.

| Technique | Scenario | Zeek | Suricata | Elastic | Physics | Time to detect | Validated (date) |
|---|---|---|---|---|---|---|---|
| T0846 Remote System Discovery | 01 | Unknown_Modbus_Client, Conduit_Violation | 9000012, 9000013 | otlab-0002, 0003 | — | | |
| T0888 Remote System Info Discovery | 01 | Modbus_Recon_Function | 9000010, 9000011 | otlab-0005 | — | | |
| T0855 Unauthorized Command Message | 02 | Unauthorized_Modbus_Write | 9000001 | otlab-0001 | | | |
| T0858 Change Operating Mode | 02 | | 9000003 | otlab-0004 | | | |
| T0879 Damage to Property | 02 | | | otlab-0008 | overflow | | |
| T0836 Modify Parameter | 03 | Unauthorized_Modbus_Write | 9000002 | otlab-0001 | alarm rate | | |
| T0812 Default Credentials | 04 | | 9000030 | otlab-0004 | | | |
| T0843 Program Download | 04 | http.log | 9000031, 9000033 | otlab-0007 | behaviour change | | |
| T0881 Service Stop | 04 | http.log | 9000032 | otlab-0007 | HMI frozen | | |
| T0856 Spoof Reporting Message | 05 | Unauthorized_Modbus_Write | 9000001 | otlab-0001, 0009 | truth ≠ view | | |
| T0830 Adversary-in-the-Middle | 05 | weird.log | ET ARP | otlab-0009 | | | |
| T0814 Denial of Service | 06 | Modbus_Recon_Function | 9000020, 9000022 | otlab-0006 | | | |
| T0859 Valid Accounts | 07 | ssh.log | ET SSH | prebuilt SSH rules | | | |
| T0886 Remote Services | 07 | Conduit_Violation | 9000040, 9000041 | otlab-0003 | | | |
