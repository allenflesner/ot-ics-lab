#!/usr/bin/env python3
"""Upload, compile and start a Structured Text program on OpenPLC v3.

Drives the same web workflow a human engineer would use (login ->
upload-program -> upload-program-action -> compile-program -> start_plc), so
the role exercises the real code path. Stdlib only.

Exit codes: 0 success, 1 failure.
"""
import argparse
import http.cookiejar
import re
import sqlite3
import sys
import time
import urllib.parse
import urllib.request
import uuid


def build_opener():
    jar = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def post_form(opener, url, fields):
    data = urllib.parse.urlencode(fields).encode()
    with opener.open(url, data, timeout=60) as resp:
        return resp.geturl(), resp.read().decode(errors="replace")


def get(opener, url):
    with opener.open(url, timeout=60) as resp:
        return resp.geturl(), resp.read().decode(errors="replace")


def post_multipart(opener, url, field, filename, content):
    boundary = uuid.uuid4().hex
    head = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'
        "Content-Type: application/octet-stream\r\n\r\n"
    ).encode()
    tail = f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        url,
        data=head + content + tail,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with opener.open(req, timeout=60) as resp:
        return resp.read().decode(errors="replace")


def hidden_value(html, name):
    """Return the value attribute of the <input> whose name/id matches."""
    for tag in re.findall(r"<input[^>]*>", html, flags=re.I):
        if re.search(rf"""(name|id)\s*=\s*['"]{re.escape(name)}['"]""", tag, flags=re.I):
            m = re.search(r"""value\s*=\s*['"]([^'"]*)['"]""", tag, flags=re.I)
            if m:
                return m.group(1)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8080")
    ap.add_argument("--user", default="openplc")
    ap.add_argument("--password", default="openplc")
    ap.add_argument("--program", required=True, help="path to .st file")
    ap.add_argument("--name", default="Water Tank Control")
    ap.add_argument("--description", default="OT-ICS lab water tank hysteresis control")
    ap.add_argument("--db", default="/opt/OpenPLC_v3/webserver/openplc.db")
    ap.add_argument("--timeout", type=int, default=900)
    args = ap.parse_args()

    op = build_opener()
    base = args.url.rstrip("/")

    final_url, _ = post_form(op, f"{base}/login", {"username": args.user, "password": args.password})
    final_url, _ = get(op, f"{base}/dashboard")
    if "login" in final_url:
        print("ERROR: login failed (check credentials)", file=sys.stderr)
        return 1
    print("[+] logged in")

    with open(args.program, "rb") as fh:
        content = fh.read()
    html = post_multipart(op, f"{base}/upload-program", "file", "program.st", content)
    prog_file = hidden_value(html, "prog_file")
    epoch_time = hidden_value(html, "epoch_time")
    if not prog_file or not epoch_time:
        print("ERROR: could not parse upload form (OpenPLC UI changed?)", file=sys.stderr)
        return 1
    print(f"[+] uploaded as {prog_file}")

    post_form(op, f"{base}/upload-program-action", {
        "prog_name": args.name,
        "prog_descr": args.description,
        "prog_file": prog_file,
        "epoch_time": epoch_time,
    })
    get(op, f"{base}/compile-program?file={urllib.parse.quote(prog_file)}")
    print("[*] compiling (this can take a few minutes)...")

    deadline = time.time() + args.timeout
    logs = ""
    while time.time() < deadline:
        time.sleep(5)
        _, logs = get(op, f"{base}/compilation-logs")
        if "Compilation finished successfully" in logs:
            print("[+] compilation finished")
            break
        if re.search(r"error", logs, flags=re.I) and "Compilation finished" in logs:
            print(logs[-2000:], file=sys.stderr)
            print("ERROR: compilation failed", file=sys.stderr)
            return 1
    else:
        print(logs[-2000:], file=sys.stderr)
        print("ERROR: compilation timed out", file=sys.stderr)
        return 1

    get(op, f"{base}/start_plc")
    print("[+] PLC started")

    # Persist "start in run mode" so the PLC survives reboots. Non-fatal.
    try:
        con = sqlite3.connect(args.db)
        con.execute("UPDATE Settings SET Value = 'true' WHERE Key = 'Start_run_mode'")
        con.commit()
        con.close()
        print("[+] Start_run_mode = true")
    except sqlite3.Error as exc:
        print(f"[!] could not set Start_run_mode: {exc} (set it in Settings UI)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
