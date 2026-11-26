#!/usr/bin/env python3
"""End-to-end self-test without a range: a fake PLC (Modbus server + the same
hysteresis logic as water_tank.st), the real field sim, the real HMI, and the
real attack tool. Run: python tests/test_process.py
"""
import json
import os
import socket
import socketserver
import struct
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COILS = [False] * 8
HR = {1024: 500, 1025: 0, 1026: 0}
LOCK = threading.Lock()


class FakePLC(socketserver.BaseRequestHandler):
    def handle(self):
        s = self.request
        while True:
            hdr = s.recv(7)
            if len(hdr) < 7:
                return
            tid, _p, length, unit = struct.unpack(">HHHB", hdr)
            pdu = s.recv(length - 1)
            fc = pdu[0]
            with LOCK:
                if fc == 1:
                    addr, cnt = struct.unpack(">HH", pdu[1:5])
                    bits = 0
                    for i in range(cnt):
                        bits |= int(COILS[addr + i]) << i
                    nbytes = (cnt + 7) // 8
                    resp = bytes([1, nbytes]) + bits.to_bytes(nbytes, "little")
                elif fc == 3:
                    addr, cnt = struct.unpack(">HH", pdu[1:5])
                    resp = bytes([3, cnt * 2]) + b"".join(struct.pack(">H", HR.get(addr + i, 0)) for i in range(cnt))
                elif fc == 5:
                    addr, val = struct.unpack(">HH", pdu[1:5])
                    COILS[addr] = val == 0xFF00
                    resp = pdu[:5]
                elif fc == 6:
                    addr, val = struct.unpack(">HH", pdu[1:5])
                    HR[addr] = val
                    resp = pdu[:5]
                else:
                    resp = bytes([fc | 0x80, 1])
            s.sendall(struct.pack(">HHHB", tid, 0, len(resp) + 1, unit) + resp)


def plc_logic():
    init = False
    while True:
        with LOCK:
            if not init:
                COILS[2] = True
                init = True
            HR[1025] = HR[1025] or 800
            HR[1026] = HR[1026] or 200
            lvl = HR[1024]
            if COILS[2]:
                if lvl <= HR[1026]:
                    COILS[0] = True
                if lvl >= HR[1025]:
                    COILS[0] = False
            COILS[3] = lvl >= 950
            COILS[4] = lvl <= 50
        time.sleep(0.05)


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def run_attack(port, *args):
    return subprocess.run([sys.executable, os.path.join(ROOT, "attacks/ot_attack.py"),
                           "--target", "127.0.0.1", "--i-own-this", "--port", str(port), *args],
                          capture_output=True, text=True, timeout=30, env={**os.environ, "PYTHONPATH": ""})


def main():
    mb_port = free_port()
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", mb_port), FakePLC)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    threading.Thread(target=plc_logic, daemon=True).start()

    # The tools use a fixed port 502; patch via a tiny shim on PYTHONPATH.
    shim = tempfile.mkdtemp()
    with open(os.path.join(ROOT, "src/mbtcp.py")) as fh:
        src = fh.read().replace("port=502", f"port={mb_port}")
    with open(os.path.join(shim, "mbtcp.py"), "w") as fh:
        fh.write(src)

    tmp = tempfile.mkdtemp()
    proc_log = os.path.join(tmp, "process.jsonl")
    audit_log = os.path.join(tmp, "actions.jsonl")
    hmi_port = free_port()
    env = {**os.environ, "PYTHONPATH": shim}

    def launch(script, *extra):
        # run a copy next to the shim so `from mbtcp import` resolves to it
        dst = os.path.join(shim, os.path.basename(script))
        with open(os.path.join(ROOT, script)) as a, open(dst, "w") as b:
            b.write(a.read())
        return subprocess.Popen([sys.executable, dst, *extra], env=env,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    sim = launch("ansible/roles/ot_field_sim/files/field_sim.py",
                 "--plc", "127.0.0.1", "--interval", "0.1", "--log", proc_log)
    hmi = launch("ansible/roles/ot_hmi/files/hmi.py",
                 "--plc", "127.0.0.1", "--port", str(hmi_port), "--poll", "0.2", "--audit", audit_log)
    ok = True
    try:
        time.sleep(4)
        # 1. physics + control loop cycles between setpoints
        levels = [json.loads(line)["tank"]["level"] for line in open(proc_log)]
        assert len(levels) > 15, "field sim not writing"
        assert min(levels) < 500 or max(levels) > 500, "level not moving"
        print(f"[ok] field sim: {len(levels)} ticks, level {min(levels)}..{max(levels)}")

        # 2. HMI reads state
        st = json.load(urllib.request.urlopen(f"http://127.0.0.1:{hmi_port}/api/state"))
        assert st["connected"] and st["mode_auto"] and st["hi_setpoint"] == 800, st
        print(f"[ok] HMI state: level={st['tank_level']} auto={st['mode_auto']}")

        # 3. HMI command -> Modbus write + audit entry
        req = urllib.request.Request(f"http://127.0.0.1:{hmi_port}/api/cmd",
                                     data=json.dumps({"target": "drain_valve", "value": 1}).encode(),
                                     headers={"Content-Type": "application/json"})
        assert json.load(urllib.request.urlopen(req))["ok"]
        assert COILS[1] is True, "drain coil not written"
        audit = [json.loads(line) for line in open(audit_log)]
        assert audit[-1]["ot"]["modbus"] == {"function_code": 5, "address": 1}
        print("[ok] HMI command written and audited")

        # 4. attack tool: read, mode change, setpoint tamper, guard
        out = run_attack(mb_port, "read")
        assert "tank_level" in out.stdout, out.stderr
        run_attack(mb_port, "write-coil", "2", "0")
        run_attack(mb_port, "write-reg", "1025", "990")
        assert COILS[2] is False and HR[1025] == 990
        diag = run_attack(mb_port, "diag", "4")
        assert "exception" in diag.stdout, diag.stdout + diag.stderr
        guard = subprocess.run([sys.executable, os.path.join(ROOT, "attacks/ot_attack.py"),
                                "--target", "8.8.8.8", "read"], capture_output=True, text=True)
        assert guard.returncode != 0 and "refusing" in guard.stderr
        print("[ok] attack tool: read / write-coil / write-reg / diag exception / scope guard")
    except AssertionError as exc:
        ok = False
        print("[FAIL]", exc)
    finally:
        sim.terminate()
        hmi.terminate()
        srv.shutdown()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
