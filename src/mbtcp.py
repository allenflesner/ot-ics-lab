"""Minimal, dependency-free Modbus/TCP client (Python 3 stdlib only).

Used by the field simulator, the HMI, and the attack toolkit so the lab does
not depend on pymodbus (whose API changes between releases).

Canonical copy lives in src/mbtcp.py. Run scripts/sync-shared.sh after editing
so the copies inside the Ansible roles and attacks/ stay identical (CI checks).
"""
import socket
import struct
import threading


class ModbusError(Exception):
    """Raised when the server answers with a Modbus exception response."""


class Client:
    def __init__(self, host, port=502, unit=1, timeout=3.0):
        self.host = host
        self.port = port
        self.unit = unit
        self.timeout = timeout
        self.sock = None
        self.tid = 0
        self.lock = threading.Lock()

    # -- connection handling -------------------------------------------------
    def connect(self):
        self.close()
        self.sock = socket.create_connection((self.host, self.port), timeout=self.timeout)

    def close(self):
        if self.sock is not None:
            try:
                self.sock.close()
            except OSError:
                pass
        self.sock = None

    def _recv_exact(self, n):
        buf = b""
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("connection closed by peer")
            buf += chunk
        return buf

    # -- core request ----------------------------------------------------------
    def request(self, pdu):
        """Send a PDU (function code + data), return the response PDU."""
        with self.lock:
            if self.sock is None:
                self.connect()
            self.tid = (self.tid + 1) & 0xFFFF
            mbap = struct.pack(">HHHB", self.tid, 0, len(pdu) + 1, self.unit)
            try:
                self.sock.sendall(mbap + pdu)
                header = self._recv_exact(7)
                _tid, _proto, length, _unit = struct.unpack(">HHHB", header)
                body = self._recv_exact(length - 1)
            except (OSError, ConnectionError):
                self.close()
                raise
        if body[0] & 0x80:
            raise ModbusError(f"exception code {body[1]} for function {body[0] & 0x7F}")
        return body

    # -- common function codes -------------------------------------------------
    def read_coils(self, addr, count):  # FC 1
        body = self.request(struct.pack(">BHH", 1, addr, count))
        data = body[2:]
        return [bool((data[i // 8] >> (i % 8)) & 1) for i in range(count)]

    def read_holding_registers(self, addr, count):  # FC 3
        body = self.request(struct.pack(">BHH", 3, addr, count))
        return list(struct.unpack(f">{count}H", body[2:2 + 2 * count]))

    def write_coil(self, addr, value):  # FC 5
        self.request(struct.pack(">BHH", 5, addr, 0xFF00 if value else 0x0000))

    def write_register(self, addr, value):  # FC 6
        self.request(struct.pack(">BHH", 6, addr, int(value) & 0xFFFF))

    def report_server_id(self):  # FC 17
        return self.request(struct.pack(">B", 17))

    def raw(self, function_code, payload=b""):
        return self.request(struct.pack(">B", function_code) + payload)
