# Wireshark for OT

## Get packets

- **Historical:** carve from the sensor ring buffer with `scripts/sensor/pull-pcap.sh`, then `scp` to Kali or your workstation.
- **Live remote capture from the sensor (Kali/Linux):**
  ```bash
  ssh root@10.N.50.20 'tcpdump -i ens19 -U -s0 -w - port 502 or port 8080 or arp' | wireshark -k -i -
  ```
- **On the EWS:** Wireshark is installed by Chocolatey. Install **Npcap** manually (its installer can't be fully silent) to capture locally.

## Install the lab profile

Copy `wireshark/colorfilters` into a profile folder named `OT-Lab` (paths in the file header), then *Edit → Configuration Profiles → OT-Lab*. Writes turn orange, exceptions red, diagnostics purple.

## Display filters worth memorising

| Goal | Filter |
|---|---|
| All Modbus | `mbtcp` |
| Writes only | `modbus.func_code in {5 6 15 16 22 23}` |
| Writes from anyone but the HMI and field I/O | `modbus.func_code in {5 6 15 16} && !(ip.src in {10.N.30.10 10.N.40.20})` |
| Writes to the setpoint registers | `modbus.func_code == 6 && modbus.reference_num in {1025 1026}` |
| Writes to the mode coil | `modbus.func_code == 5 && modbus.reference_num == 2` |
| Exceptions (attacker probing unsupported FCs) | `modbus.exception_code` |
| Diagnostics / fingerprinting | `modbus.func_code in {8 17 43}` |
| OpenPLC web logins | `http.request.method == "POST" && http.request.uri contains "login"` |
| Duplicate IP / ARP spoofing | `arp.duplicate-address-detected \|\| arp.duplicate-address-frame` |

> Field names vary slightly by Wireshark version (`modbus.reference_num` vs `modbus.regnum16`). Right-click a field → *Apply as Filter* to get the exact name in yours.

## Analysis workflow

1. **Statistics → Conversations → IPv4**: in a healthy plant you'll see exactly three Modbus talkers to the PLC. A fourth is your attacker.
2. **Statistics → I/O Graph**: plot `mbtcp` packets/sec; add a second line for writes. Floods and spoof loops are obvious spikes.
3. **Decode the value**: select a FC6 frame → *Register Value*. Compare with the HMI audit log.
4. **Follow → TCP Stream** on port 8080 to read the attacker's OpenPLC session (credentials in clear text — a finding in itself).
5. Export the specific packets (*File → Export Specified Packets*) as evidence for the journal (keep pcaps out of git; note the hash).
