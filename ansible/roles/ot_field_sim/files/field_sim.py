#!/usr/bin/env python3
"""Simulated physical process + remote field I/O for the water tank.

Every tick it reads the PLC's output coils (pump, drain valve), runs simple
tank physics, and writes the new level into the PLC's holding register 1024
(%MW0) - the same job a real remote I/O block wired to a level transmitter
would do.

It also writes the "ground truth" of the physical process to a JSON-lines log.
Ship that log to Elastic: comparing what the HMI *shows* with what the tank is
*actually doing* is how you catch spoofed-telemetry attacks.
"""
import argparse
import datetime as dt
import json
import logging
import os
import socket
import time

from mbtcp import Client

REG_LEVEL = 1024
COILS = ("pump_cmd", "drain_valve", "mode_auto", "high_alarm", "low_alarm")

PUMP_INFLOW = 12      # level units per tick when the pump runs
BASE_DEMAND = 4       # constant downstream consumption
DRAIN_OUTFLOW = 10    # extra outflow when the drain valve is open
MAX_LEVEL = 1000


def utcnow():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plc", default=os.environ.get("OT_PLC_IP", "127.0.0.1"))
    ap.add_argument("--interval", type=float, default=float(os.environ.get("OT_SIM_INTERVAL", "1.0")))
    ap.add_argument("--log", default=os.environ.get("OT_PROCESS_LOG", "/var/log/ot-process/process.jsonl"))
    ap.add_argument("--start-level", type=float, default=500.0)
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    host = socket.gethostname()
    client = Client(args.plc)
    level = args.start_level
    logging.info("field sim started, PLC=%s interval=%.1fs", args.plc, args.interval)

    while True:
        try:
            coils = dict(zip(COILS, client.read_coils(0, len(COILS))))
            inflow = PUMP_INFLOW if coils["pump_cmd"] else 0
            outflow = BASE_DEMAND + (DRAIN_OUTFLOW if coils["drain_valve"] else 0)
            raw = level + inflow - outflow
            overflow = raw >= MAX_LEVEL
            dry = raw <= 0
            level = max(0.0, min(float(MAX_LEVEL), raw))
            client.write_register(REG_LEVEL, int(level))

            record = {
                "@timestamp": utcnow(),
                "event": {"kind": "metric", "dataset": "ot_process", "module": "otlab"},
                "host": {"name": host},
                "ot": {"process": "water_tank", "plc_ip": args.plc},
                "tank": {
                    "level": int(level),
                    "level_pct": round(level / 10.0, 1),
                    "inflow": inflow,
                    "outflow": outflow,
                    "overflow": overflow,
                    "dry": dry,
                },
                "plc_outputs": coils,
            }
            with open(args.log, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(record) + "\n")
            if overflow:
                logging.warning("TANK OVERFLOW - physical spill in progress")
        except Exception as exc:  # keep the plant running through PLC restarts
            logging.warning("PLC I/O error: %s", exc)
            client.close()
            time.sleep(2)
            continue
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
