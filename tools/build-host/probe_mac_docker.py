#!/usr/bin/env python3
"""Bounded local Linux/Android-host-tool probe, never a full ROM build.

Uses already pinned/downloaded official Ubuntu and Android tools. No network,
USB devices, Docker socket, or writable project tree is exposed to the test.
"""
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / '.local/mac-build-probe'
REPORT = ROOT / 'work/mac-linux-toolchain-probe-2026-11-11.json'


def main():
    docker = shutil.which('docker')
    if not docker:
        raise SystemExit('Docker client unavailable')
    context = subprocess.run([docker, 'context', 'inspect'], capture_output=True, text=True, check=True, timeout=10)
    endpoint = json.loads(context.stdout)[0].get('Endpoints', {}).get('docker', {}).get('Host', '')
    if not endpoint.startswith('unix://'):
        raise SystemExit('Only the local Docker context is permitted')
    image = json.loads((INPUT / 'ubuntu-image.json').read_text())['image']
    if not image.startswith('docker.io/library/ubuntu@sha256:'):
        raise SystemExit('Expected pinned official Ubuntu image')
    binary = json.loads((INPUT / 'android-toolchain-probe.json').read_text())
    if hashlib.sha256((INPUT / 'ninja').read_bytes()).hexdigest() != binary['sha256']:
        raise SystemExit('Android build-tool digest changed')
    runtimes = json.loads((INPUT / 'ninja-runtimes.json').read_text())
    for item in runtimes:
        if hashlib.sha256((INPUT / 'lib64' / item['file']).read_bytes()).hexdigest() != item['sha256']:
            raise SystemExit('Android runtime digest changed')
    history = []
    if REPORT.exists():
        old = json.loads(REPORT.read_text())
        history = old.get('attempt_history', [])
        history.append({k: old.get(k) for k in ['started_at_utc', 'passed', 'stderr']})
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d%H%M%S')
    volume = 'booxos-host-probe-' + stamp
    record = {'kind': 'Experimental Mac amd64 Linux / Android Ninja probe',
              'image': image, 'platform': 'linux/amd64', 'boox_access': False,
              'docker_settings_changed': False, 'attempt_history': history,
              'started_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    created = False
    try:
        subprocess.run([docker, 'volume', 'create', '--label', 'project=BooxOS',
                        '--label', 'purpose=host-probe', volume], capture_output=True,
                       text=True, check=True, timeout=10)
        created = True
        args = [docker, 'run', '--rm', '--name', volume, '--platform', 'linux/amd64',
                '--network', 'none', '--cap-drop', 'ALL', '--security-opt',
                'no-new-privileges', '--pids-limit', '128', '--memory', '2g',
                '--cpus', '2', '--read-only', '--env', 'LD_LIBRARY_PATH=/probe/lib64',
                '--tmpfs', '/tmp:rw,nosuid,nodev,size=64m', '--mount',
                'type=bind,src=' + str(INPUT) + ',dst=/probe,readonly', '--mount',
                'type=volume,src=' + volume + ',dst=/workspace', image,
                '/bin/sh', '/probe/probe.sh']
        began = time.monotonic()
        result = subprocess.run(args, capture_output=True, text=True, timeout=90)
        record.update(exit_code=result.returncode, stdout=result.stdout.strip(),
                      stderr=result.stderr.strip(), elapsed_seconds=round(time.monotonic() - began, 2),
                      passed=result.returncode == 0 and 'TINY_BUILD=linux-x86-build-tool-ok' in result.stdout)
    except BaseException as exc:
        record.update(passed=False, failure_type=type(exc).__name__, failure_reason=str(exc))
        raise
    finally:
        if created:
            cleanup = subprocess.run([docker, 'volume', 'rm', volume], capture_output=True,
                                     text=True, timeout=10)
            record['temporary_probe_volume_removed'] = cleanup.returncode == 0
        REPORT.write_text(json.dumps(record, indent=2) + '\n')
        print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
