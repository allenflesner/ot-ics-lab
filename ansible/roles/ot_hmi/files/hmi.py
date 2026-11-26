#!/usr/bin/env python3
"""Water tank HMI (Purdue Level 2). Stdlib only.

- Polls the PLC every 2 s (Modbus FC1 + FC3): this is the "normal" baseline
  traffic your sensor will learn.
- Operator actions become Modbus writes (FC5 coils / FC6 registers) and are
  written to an audit log. In Elastic, a PLC write with no matching HMI audit
  entry is a strong signal of an unauthorized command.
"""
import argparse
import datetime as dt
import json
import logging
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from mbtcp import Client

COILS = ("pump_cmd", "drain_valve", "mode_auto", "high_alarm", "low_alarm")
WRITABLE_COILS = {"pump_cmd": 0, "drain_valve": 1, "mode_auto": 2}
SETPOINT_REGS = {"hi_setpoint": 1025, "lo_setpoint": 1026}

STATE = {"connected": False, "history": []}
STATE_LOCK = threading.Lock()

PAGE = """<!doctype html><html><head><meta charset="utf-8"><title>Tank HMI</title>
<style>
body{font-family:system-ui,sans-serif;background:#10161d;color:#dfe6ee;margin:24px}
h1{font-size:20px;margin:0 0 4px}.sub{color:#8a99a8;font-size:13px;margin-bottom:20px}
.grid{display:grid;grid-template-columns:220px 1fr;gap:24px;max-width:900px}
.tank{position:relative;height:320px;border:3px solid #5b6b7b;border-radius:6px;background:#1b2530;overflow:hidden}
.water{position:absolute;bottom:0;left:0;right:0;background:#2f7fd1;transition:height .8s}
.mark{position:absolute;left:0;right:0;border-top:2px dashed #e0a63a;font-size:11px;color:#e0a63a}
.lvl{font-size:34px;font-weight:600;margin:8px 0}
.card{background:#18212b;border:1px solid #2a3643;border-radius:6px;padding:14px;margin-bottom:12px}
.row{display:flex;justify-content:space-between;align-items:center;margin:6px 0}
.on{color:#4cc38a}.off{color:#8a99a8}.alarm{color:#ff6b6b;font-weight:600}
button{background:#2a3643;color:#dfe6ee;border:1px solid #3c4b5a;border-radius:4px;padding:5px 10px;cursor:pointer}
button:hover{background:#344455}input{width:70px;background:#10161d;color:#dfe6ee;border:1px solid #3c4b5a;padding:4px}
canvas{width:100%;height:90px;background:#10161d;border-radius:4px}
.bad{background:#5a1d1d;padding:8px;border-radius:4px;display:none}
</style></head><body>
<h1>Water Treatment &mdash; Tank T-101</h1><div class="sub">HMI-01 &middot; PLC __PLC__ &middot; Modbus/TCP</div>
<div id="comm" class="bad">COMMUNICATION LOSS WITH PLC</div>
<div class="grid"><div>
<div class="tank"><div id="water" class="water" style="height:50%"></div>
<div id="hi" class="mark">HI SP</div><div id="lo" class="mark">LO SP</div></div>
<div class="lvl" id="lvl">--.- %</div></div><div>
<div class="card"><div class="row"><b>Mode</b><span id="mode_auto"></span>
<span><button onclick="cmd('mode_auto',1)">AUTO</button> <button onclick="cmd('mode_auto',0)">MANUAL</button></span></div>
<div class="row"><b>Inlet pump P-101</b><span id="pump_cmd"></span>
<span><button onclick="cmd('pump_cmd',1)">START</button> <button onclick="cmd('pump_cmd',0)">STOP</button></span></div>
<div class="row"><b>Drain valve V-201</b><span id="drain_valve"></span>
<span><button onclick="cmd('drain_valve',1)">OPEN</button> <button onclick="cmd('drain_valve',0)">CLOSE</button></span></div></div>
<div class="card"><div class="row"><b>High setpoint</b><span id="hi_setpoint"></span>
<span><input id="hi_in" type="number" min="0" max="1000"> <button onclick="sp('hi_setpoint','hi_in')">SET</button></span></div>
<div class="row"><b>Low setpoint</b><span id="lo_setpoint"></span>
<span><input id="lo_in" type="number" min="0" max="1000"> <button onclick="sp('lo_setpoint','lo_in')">SET</button></span></div></div>
<div class="card"><div class="row"><b>High level alarm</b><span id="high_alarm"></span></div>
<div class="row"><b>Low level alarm</b><span id="low_alarm"></span></div></div>
<div class="card"><b>Level trend (10 min)</b><canvas id="trend" width="600" height="90"></canvas></div>
</div></div>
<script>
const onoff=(v,a)=>v?`<span class="${a?'alarm':'on'}">${a?'ACTIVE':'ON'}</span>`:'<span class="off">OFF</span>';
async function refresh(){try{const s=await (await fetch('/api/state')).json();
document.getElementById('comm').style.display=s.connected?'none':'block';if(!s.connected)return;
const p=s.tank_level/10;document.getElementById('lvl').textContent=p.toFixed(1)+' %';
document.getElementById('water').style.height=p+'%';
document.getElementById('hi').style.bottom=(s.hi_setpoint/10)+'%';document.getElementById('lo').style.bottom=(s.lo_setpoint/10)+'%';
document.getElementById('mode_auto').innerHTML=s.mode_auto?'<span class="on">AUTO</span>':'<span class="alarm">MANUAL</span>';
for(const k of ['pump_cmd','drain_valve'])document.getElementById(k).innerHTML=onoff(s[k]);
for(const k of ['high_alarm','low_alarm'])document.getElementById(k).innerHTML=onoff(s[k],true);
for(const k of ['hi_setpoint','lo_setpoint'])document.getElementById(k).textContent=(s[k]/10).toFixed(1)+' %';
const c=document.getElementById('trend'),g=c.getContext('2d');g.clearRect(0,0,c.width,c.height);
g.strokeStyle='#2f7fd1';g.lineWidth=2;g.beginPath();const h=s.history;
h.forEach((v,i)=>{const x=i*(c.width/Math.max(h.length-1,1)),y=c.height-(v/1000)*c.height;i?g.lineTo(x,y):g.moveTo(x,y)});g.stroke();
}catch(e){document.getElementById('comm').style.display='block'}}
async function post(b){await fetch('/api/cmd',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)});refresh()}
function cmd(t,v){post({target:t,value:v})}
function sp(t,id){const v=Math.round(parseFloat(document.getElementById(id).value)*10);if(!isNaN(v))post({target:t,value:v})}
setInterval(refresh,2000);refresh();
</script></body></html>"""


def utcnow():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def poller(client, interval):
    while True:
        try:
            coils = client.read_coils(0, len(COILS))
            regs = client.read_holding_registers(1024, 3)
            with STATE_LOCK:
                STATE.update(dict(zip(COILS, coils)))
                STATE.update({"tank_level": regs[0], "hi_setpoint": regs[1], "lo_setpoint": regs[2]})
                STATE["connected"] = True
                STATE["history"] = (STATE["history"] + [regs[0]])[-300:]
        except Exception as exc:
            logging.warning("poll failed: %s", exc)
            client.close()
            with STATE_LOCK:
                STATE["connected"] = False
        time.sleep(interval)


def make_handler(client, audit_path, plc_ip):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, code, body, ctype="application/json"):
            data = body.encode() if isinstance(body, str) else body
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path == "/api/state":
                with STATE_LOCK:
                    self._send(200, json.dumps(STATE))
            elif self.path in ("/", "/index.html"):
                self._send(200, PAGE.replace("__PLC__", plc_ip), "text/html; charset=utf-8")
            else:
                self._send(404, '{"error":"not found"}')

        def do_POST(self):
            if self.path != "/api/cmd":
                return self._send(404, '{"error":"not found"}')
            try:
                length = int(self.headers.get("Content-Length", "0"))
                req = json.loads(self.rfile.read(length) or b"{}")
                target, value = req["target"], int(req["value"])
                if target in WRITABLE_COILS:
                    client.write_coil(WRITABLE_COILS[target], bool(value))
                    fc, addr = 5, WRITABLE_COILS[target]
                elif target in SETPOINT_REGS:
                    if not 0 <= value <= 1000:
                        raise ValueError("setpoint out of range")
                    client.write_register(SETPOINT_REGS[target], value)
                    fc, addr = 6, SETPOINT_REGS[target]
                else:
                    raise ValueError(f"unknown target {target}")
            except Exception as exc:
                return self._send(400, json.dumps({"error": str(exc)}))
            entry = {
                "@timestamp": utcnow(),
                "event": {"kind": "event", "category": ["configuration"], "action": "hmi-operator-command",
                          "dataset": "ot_hmi_audit", "module": "otlab"},
                "source": {"ip": self.client_address[0]},
                "destination": {"ip": plc_ip, "port": 502},
                "ot": {"hmi_target": target, "value": value,
                       "modbus": {"function_code": fc, "address": addr}},
            }
            with open(audit_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry) + "\n")
            self._send(200, '{"ok":true}')

        def log_message(self, fmt, *args):
            logging.info("%s %s", self.client_address[0], fmt % args)

    return Handler


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plc", default=os.environ.get("OT_PLC_IP", "127.0.0.1"))
    ap.add_argument("--port", type=int, default=int(os.environ.get("OT_HMI_PORT", "8080")))
    ap.add_argument("--poll", type=float, default=2.0)
    ap.add_argument("--audit", default=os.environ.get("OT_HMI_AUDIT", "/var/log/ot-hmi/actions.jsonl"))
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    # Separate connections: polling and commands, like many real HMIs.
    threading.Thread(target=poller, args=(Client(args.plc), args.poll), daemon=True).start()
    server = ThreadingHTTPServer(("0.0.0.0", args.port), make_handler(Client(args.plc), args.audit, args.plc))
    logging.info("HMI listening on :%d, PLC %s", args.port, args.plc)
    server.serve_forever()


if __name__ == "__main__":
    main()
