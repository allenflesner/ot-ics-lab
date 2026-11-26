# Deploy

All `ludus` commands run wherever your Ludus CLI is configured. Steps marked **[host]** run as root on the Proxmox/Ludus host.

## 1. Add roles

```bash
./scripts/ludus-host/upload-roles.sh
ludus ansible role list     # expect ot_openplc ot_field_sim ot_hmi ot_jumphost ot_sensor + 2 badsectorlabs roles
```

## 2. Configure and deploy

```bash
cp ludus/range-config.full.yml /tmp/otlab.yml     # or range-config.lite.yml
# edit ludus_elastic_password, versions if desired
ludus range config set -f /tmp/otlab.yml
ludus range deploy
ludus range logs -f          # first build: 45-90 min (OpenPLC compile, Elastic pull, Windows)
ludus range status           # note your range number N -> IPs are 10.N.x.y
```

## 3. Virtual SPAN for the sensor **[host]**

```bash
sudo RANGE_ID=<your range id> ./scripts/ludus-host/ot-span.sh setup
sudo ot-span.sh status       # every lab VM should say MIRRORED
```
This hot-plugs `net1` into the sensor (appears as `ens19`), installs an idempotent `ot-span.timer`, and applies the mirrors.

## 4. Finish the sensor

```bash
ludus range deploy -t user-defined-roles --limit <id>-ot-sensor
```
Verify on the sensor:
```bash
sudo /opt/zeek/bin/zeekctl status
systemctl is-active suricata pcap-ring
sudo tail -f /opt/zeek/logs/current/modbus.log | jq -c '{ts, src:."id.orig_h", func}'
sudo tail -f /var/log/suricata/fast.log
```

## 5. Elastic

See [04-elastic.md](04-elastic.md). Short version:
```bash
export KIBANA_URL=https://10.N.50.10:5601 ELASTIC_PASSWORD='ChangeMe-OTlab-2026' LAB_NET=10.N
./scripts/elastic/fleet-add-ot-integrations.sh
./scripts/elastic/import-detections.sh
```

## 6. Check the plant

Browse to the HMI at `http://10.N.30.10:8080` over Ludus WireGuard. You should see the tank cycling between 20 % and 80 %.

## 7. Snapshot a clean baseline

```bash
ludus testing start    # snapshots VMs (except elastic & sensor) and blocks internet
# ... run a scenario ...
ludus testing stop     # reverts the plant to clean; your telemetry stays
```

## Locking down internet access

Once built, set `external_default: REJECT` in the config and `ludus range deploy -t network`. Real OT networks have no internet; this also forces you to stage tools properly.

## Redeploy / iterate on one role

```bash
ludus ansible role add -d ansible/roles/ot_hmi --force
ludus range deploy -t user-defined-roles --limit <id>-ot-hmi
```
