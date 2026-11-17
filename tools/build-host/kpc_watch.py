#!/usr/bin/env python3
"""Watch only this build, stopping it before the Windows disk fills."""
import datetime
import json
from pathlib import Path
import shutil
import subprocess
import time

NAME = 'booxos-lineage21-20261115'
ROOT = Path('/home/kjseg/booxos-lineage21-20261115')
record = {'name': NAME, 'boox_access': False, 'minimum_disk_free_GiB': 40}
while True:
    proc = subprocess.run(['docker', 'inspect', '--format', '{{json .State}}', NAME],
                          capture_output=True, text=True)
    if proc.returncode:
        record['error'] = proc.stderr
        break
    state = json.loads(proc.stdout)
    free = shutil.disk_usage('/mnt/c').free
    record.update(state=state, disk_free_GiB=round(free/1024**3, 2),
                  checked_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
    if state['Running'] and free < 40*1024**3:
        record['stop_reason'] = 'Windows disk reached 40 GiB free floor'
        subprocess.run(['docker', 'stop', '--timeout', '30', NAME], capture_output=True)
    (ROOT/'logs/status.json').write_text(json.dumps(record, indent=2)+'\n')
    print(json.dumps(record), flush=True)
    if not state['Running']:
        break
    time.sleep(20)
