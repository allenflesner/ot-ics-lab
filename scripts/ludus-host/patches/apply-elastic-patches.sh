#!/usr/bin/env bash
# Apply the two OT-lab patches to the Ludus Elastic role copies on the Ludus host.
#   1) ecp-kibana healthcheck accepts HTTP/1.1 or HTTP/2 302
#   2) Elastic agent uninstall step tolerates failure (ignore_errors)
# Idempotent. Backups are written as <file>.bak-patch. Run as root on the Ludus
# host after the badsectorlabs Elastic roles have been added to Ludus.
# Remove these patches once the upstream roles fix the same issues.
set -euo pipefail

python3 - <<'PY'
import glob, os, shutil

HC_MARK = 'Accept HTTP/1.1 or HTTP/2 302'
HC_BLOCK = [
    '- name: Accept HTTP/1.1 or HTTP/2 302 in the ecp-kibana healthcheck\n',
    '  ansible.builtin.replace:\n',
    '    path: "{{ ludus_elastic_container_install_path }}/docker-compose.yml"\n',
    "    regexp: \"grep -q 'HTTP/2 302'\"\n",
    "    replace: \"grep -Eq 'HTTP/[12].* 302'\"\n",
    '\n',
]

def backup(p):
    b = p + '.bak-patch'
    if not os.path.exists(b):
        shutil.copy2(p, b)

def patch_hc(p):
    lines = open(p).read().splitlines(True)
    if any(HC_MARK in l for l in lines):
        return 'already patched'
    for i, l in enumerate(lines):
        if 'Copy the .env template to the host' in l:
            backup(p)
            open(p, 'w').write(''.join(lines[:i] + HC_BLOCK + lines[i:]))
            return 'patched'
    return 'anchor not found'

def patch_un(p):
    lines = open(p).read().splitlines(True)
    for i, l in enumerate(lines):
        if 'elastic-agent uninstall -f' in l:
            for j in range(i + 1, min(i + 6, len(lines))):
                if lines[j].lstrip().startswith('when:'):
                    if j + 1 < len(lines) and 'ignore_errors' in lines[j + 1]:
                        return 'already patched'
                    backup(p)
                    lines.insert(j + 1, '  ignore_errors: true\n')
                    open(p, 'w').write(''.join(lines))
                    return 'patched'
    return 'anchor not found'

hc = glob.glob('/opt/ludus/users/*/.ansible/roles/badsectorlabs.ludus_elastic_container/tasks/install.yml') + glob.glob('/opt/ludus/sources/*/ansible/roles/ludus_elastic_container/tasks/install.yml')
un = glob.glob('/opt/ludus/users/*/.ansible/roles/badsectorlabs.ludus_elastic_agent/tasks/linux.yml') + glob.glob('/opt/ludus/sources/*/ansible/roles/ludus_elastic_agent/tasks/linux.yml')
for p in hc:
    print(p, patch_hc(p))
for p in un:
    print(p, patch_un(p))
if not hc and not un:
    print('no Ludus Elastic role copies found')
PY
