#!/usr/bin/env python3
"""Continue the authorized build after the existing transfer completes."""
import base64
import datetime
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
TRANSFER = ROOT/'work/kpc-transfer-2026-11-15.json'
REPORT = ROOT/'work/kpc-launch-2026-11-15.json'
began = time.monotonic()
while not TRANSFER.exists():
    if time.monotonic()-began > 4*3600:
        raise SystemExit('Source transfer did not finish within four hours')
    time.sleep(20)
record = json.loads(TRANSFER.read_text())
if not record['passed']:
    raise SystemExit('Transfer failed; build not started')
script = '& wsl -d Ubuntu -u root --exec python3 /home/kjseg/booxos-lineage21-20261115/kpc_launch.py; exit $LASTEXITCODE'
encoded = base64.b64encode(script.encode('utf-16le')).decode()
result = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=20',
                         'framework-windows', 'powershell -NoProfile -EncodedCommand '+encoded],
                        capture_output=True, text=True, timeout=180)
report = {'checked_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'exit_code': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}
REPORT.write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report), flush=True)
raise SystemExit(result.returncode)
