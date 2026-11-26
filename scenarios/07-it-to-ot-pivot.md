# 07 — IT → OT pivot through the IDMZ

**Objective:** Start on the "internet", get a corporate foothold, abuse the jump host's weak credential, and reach the PLC the way real intrusions do (Ukraine 2015, Colonial-style IT compromises reaching OT). No firewall toggles.

**ATT&CK for ICS:** T0859 Valid Accounts · T0886 Remote Services · T0822 External Remote Services · T0812 Default Credentials (later)

## Full profile path

1. **Kali → corp-ws (initial access, simulated).** RDP to `10.N.10.21` with the Ludus default local account (assume phished creds). `xfreerdp /v:10.N.10.21 /u:localuser /p:password`
2. **corp-ws → jump (credential abuse).** In PowerShell on corp-ws, try the weak credential (or a short guess list): `ssh otjump@10.N.20.10` → `Plant2026!`. Read `~/README-ops.txt`.
3. **Tunnel to the EWS.** From corp-ws: `ssh -L 13389:10.N.30.20:3389 otjump@10.N.20.10`, then RDP to `127.0.0.1:13389` (Ludus default creds on EWS).
4. **EWS → PLC.** On the EWS browser, `http://10.N.40.10:8080` → scenario 04, or run `ot_attack.py` with the EWS's Python against the PLC — now from an *authorized* writer IP.

## Lite profile path
Kali is allowed to SSH to the jump host (simulating a compromised corp machine), and the jump host can reach the PLC directly:
```bash
hydra -l otjump -P /usr/share/wordlists/fasttrack.txt ssh://10.N.20.10 -t 4
ssh otjump@10.N.20.10
curl -s http://10.N.40.10:8080/login | head
```

## What you should see

| Source | Evidence |
|---|---|
| Elastic (System/Defend on jump) | SSH auth failures then success for `otjump` from corp-ws/Kali; new `ssh` session with `-L` forwarding (Defend process args on corp-ws) |
| Elastic (Windows/Sysmon on corp-ws, EWS) | `ssh.exe` with `-L`, RDP logon type 10 to EWS from `127.0.0.1`-forwarded session (sourced from jump) |
| Zeek | `ssh.log` brute-force pattern (`auth_attempts`), `conn.log` jump→EWS:3389 long-lived session |
| Suricata | 9000041 in lite (untrusted net touching IDMZ); ET SSH brute force rules |
| Prebuilt Elastic rules | SSH brute force, RDP from unusual source |

In the full profile, the final Modbus writes come from the EWS — **allow-listed**. Only the chain (auth logs → tunnel → RDP → web/Modbus) reveals the attack. That's the point.

## Detect — exercise
Write an EQL **sequence** rule: `authentication success for otjump on the jump host` followed within 30 min by `network connection from jump to 10.N.30.20:3389` (Defend network events). This catches the pivot even when every later action is "authorized".

## Respond & harden
- Rotate `ot_jump_password`, set `ot_jump_allow_password_auth: false`, use keys + MFA (discuss), and re-run.
- Disable TCP forwarding on the jump host (`AllowTcpForwarding no`) — re-run step 3 and watch it fail.

## Journal prompts
- Draw the kill chain with timestamps from your Elastic Timeline.
- At which hop would you most want to be alerted, given analyst capacity?
