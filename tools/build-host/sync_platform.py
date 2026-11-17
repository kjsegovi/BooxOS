#!/usr/bin/env python3
"""Fetch the Android 14 platform for the approved experimental BOOX install.

Local project-owned Linux volume only. No USB or firmware commands. Preserve
physical Mac disk headroom; stop only this container at the floor or deadline.
"""
import datetime
import json
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
NAME = 'booxos-lineage21-platform-sync-20261111'
VOLUME = 'booxos-lineage21-source-20261111'
MIN_FREE = 80 * 1024**3
BOOTSTRAP = ROOT / '.local/repo-bootstrap'

SCRIPT = r'''
set -eu
git lfs install --skip-repo
python3 /bootstrap/repo init -u https://github.com/LineageOS/android.git \
  -b 121f4ec5f11dc98ff2c427bc9d23165e914c54bb \
  --manifest-upstream-branch lineage-21.0 --depth=1 --partial-clone \
  --clone-filter=blob:limit=10m --no-clone-bundle --no-tags --git-lfs \
  --groups=default,-darwin
python3 - <<'PY'
import json,pathlib,xml.etree.ElementTree as ET
pins=json.loads(pathlib.Path('/plan/lineage21-toolchain-subset-final-2026-11-11.json').read_text())['pins']
manifest=ET.parse('/work/preparation-manifest.xml').getroot()
projects={p.get('path',p.get('name')):p.get('name') for p in manifest.findall('project')}
local=ET.Element('manifest')
for path,commit in pins.items():
    ET.SubElement(local,'extend-project',name=projects[path],path=path,revision=commit)
target=pathlib.Path('/work/.repo/local_manifests/boox-host-pins.xml')
target.parent.mkdir(exist_ok=True)
if target.exists() and target.read_bytes()!=ET.tostring(local):
    raise SystemExit('Existing host pins differ; inspect rather than overwrite')
target.write_bytes(ET.tostring(local))
PY
python3 /bootstrap/repo sync -c --no-tags --no-clone-bundle --optimized-fetch --fail-fast -j2
python3 /bootstrap/repo manifest -r -o /work/lineage21-platform-lock.xml
echo PLATFORM_SYNC_COMPLETE
'''


def main():
    docker = shutil.which('docker')
    context = json.loads(subprocess.run([docker, 'context', 'inspect'], capture_output=True,
                                        text=True, check=True, timeout=10).stdout)
    if not context[0]['Endpoints']['docker']['Host'].startswith('unix://'):
        raise SystemExit('Local Docker context required')
    labels = json.loads(subprocess.run([docker, 'volume', 'inspect', VOLUME], capture_output=True,
                                      text=True, check=True, timeout=10).stdout)[0].get('Labels') or {}
    if labels.get('project') != 'BooxOS':
        raise SystemExit('Source volume ownership changed')
    if shutil.disk_usage(ROOT).free < MIN_FREE:
        raise SystemExit('Physical Mac disk floor reached before sync')
    init = json.loads((ROOT / 'work/lineage21-source-init-2026-11-11.json').read_text())
    record = {'started_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'source_volume': VOLUME, 'image': init['image'], 'passed': False,
              'boox_access': False, 'other_containers_modified': False,
              'minimum_physical_host_free_bytes': MIN_FREE}
    args = [docker, 'run', '--rm', '--name', NAME, '--platform', 'linux/amd64',
            '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--memory', '4g',
            '--cpus', '4', '--pids-limit', '512', '--mount',
            'type=volume,src=' + VOLUME + ',dst=/work', '--mount',
            'type=bind,src=' + str(BOOTSTRAP) + ',dst=/bootstrap,readonly', '--mount',
            'type=bind,src=' + str(ROOT / 'work') + ',dst=/plan,readonly',
            '--env', 'GIT_CONFIG_COUNT=3', '--env', 'GIT_CONFIG_KEY_0=user.name',
            '--env', 'GIT_CONFIG_VALUE_0=Local BOOX build', '--env', 'GIT_CONFIG_KEY_1=user.email',
            '--env', 'GIT_CONFIG_VALUE_1=boox-build@localhost', '--env', 'GIT_CONFIG_KEY_2=pack.threads',
            '--env', 'GIT_CONFIG_VALUE_2=2', '--env', 'GOMAXPROCS=2',
            init['image'], '/bin/bash', '-c', SCRIPT]
    log = ROOT / '.local/mac-build-probe/lineage21-platform-sync.log'
    try:
        with log.open('w') as stream:
            process = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT)
            began, last = time.monotonic(), 0
            while process.poll() is None:
                free = shutil.disk_usage(ROOT).free
                if free < MIN_FREE or time.monotonic() - began > 7200:
                    subprocess.run([docker, 'stop', '--timeout', '15', NAME], capture_output=True, timeout=30)
                    record['stop_reason'] = 'Physical disk floor or two-hour source-fetch deadline'
                    break
                if time.monotonic() - last > 25:
                    lines = log.read_text(errors='replace').splitlines()
                    print(json.dumps({'elapsed_seconds': round(time.monotonic() - began),
                                      'physical_free_GB': round(free / 10**9, 2),
                                      'stage': lines[-1][-220:] if lines else 'starting'}), flush=True)
                    last = time.monotonic()
                time.sleep(2)
            process.wait(timeout=30)
        record.update(exit_code=process.returncode, elapsed_seconds=round(time.monotonic() - began, 2))
        lines = log.read_text(errors='replace').splitlines()
        record['passed'] = process.returncode == 0 and 'PLATFORM_SYNC_COMPLETE' in lines
        if not record['passed']:
            record['failure_tail'] = lines[-35:]
    finally:
        record['physical_host_free_bytes_after'] = shutil.disk_usage(ROOT).free
        (ROOT / 'work/lineage21-platform-sync-2026-11-11.json').write_text(json.dumps(record, indent=2) + '\n')
        print(json.dumps(record, indent=2), flush=True)


if __name__ == '__main__':
    main()
