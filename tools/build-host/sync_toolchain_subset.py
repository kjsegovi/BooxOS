#!/usr/bin/env python3
"""Fetch only the selected Android 14 build/host tools into our Linux volume.

No platform-wide sync, build, firmware/device operation or Docker setting change.
Stop on the physical Mac disk limit, independently of Docker's virtual capacity.
"""
import datetime
import json
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
VOLUME = 'booxos-lineage21-source-20261111'
NAME = 'booxos-lineage21-toolchain-sync-20261111'
PROJECTS = ['build/blueprint', 'build/make', 'build/soong', 'prebuilts/build-tools',
            'prebuilts/go/linux-x86', 'prebuilts/clang/host/linux-x86',
            'prebuilts/rust', 'prebuilts/jdk/jdk17']
MIN_FREE = 100 * 1024**3


def main():
    docker = shutil.which('docker')
    if not docker:
        raise SystemExit('Local Docker client unavailable')
    info = subprocess.run([docker, 'context', 'inspect'], capture_output=True, text=True, check=True, timeout=10)
    if not json.loads(info.stdout)[0]['Endpoints']['docker']['Host'].startswith('unix://'):
        raise SystemExit('Only the local Docker context is allowed')
    initial = json.loads((ROOT / 'work/lineage21-source-init-2026-11-11.json').read_text())
    if not initial.get('passed') or not initial.get('repo_signature_verified'):
        raise SystemExit('Verified manifest initialization required')
    plan = json.loads((ROOT / 'work/lineage21-host-project-plan-2026-11-11.json').read_text())
    known = {p['path']: p for p in plan['host_projects']}
    if any(path not in known or known[path]['remote'] not in ['aosp', 'github'] for path in PROJECTS):
        raise SystemExit('Unknown/non-public toolchain project')
    if shutil.disk_usage(ROOT).free < MIN_FREE:
        raise SystemExit('Insufficient physical Mac disk space')
    image = initial['image']
    out = ROOT / '.local/mac-build-probe'
    log = out / 'lineage21-toolchain-sync.log'
    report = ROOT / 'work/lineage21-toolchain-sync-2026-11-11.json'
    record = {'projects': PROJECTS, 'volume': VOLUME, 'image': image,
              'platform_wide_sync': False, 'boox_access': False,
              'docker_settings_changed': False, 'minimum_host_free_bytes': MIN_FREE,
              'started_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    # Literal paths above are a fixed allowlist, not user-supplied shell input.
    script = ('set -eu; git lfs install --skip-repo; '
              'python3 /bootstrap/repo init '
              '-u https://github.com/LineageOS/android.git '
              '-b 121f4ec5f11dc98ff2c427bc9d23165e914c54bb '
              '--manifest-upstream-branch lineage-21.0 --depth=1 --partial-clone '
              '--clone-filter=blob:none --no-clone-bundle --no-tags --git-lfs; '
              'python3 /bootstrap/repo sync -c --no-tags --no-clone-bundle '
              '--optimized-fetch --fail-fast -j2 ' + ' '.join(PROJECTS) + '; '
              'printf "TOOLCHAIN_SUBSET_SYNCED\\n"; '
              'for p in ' + ' '.join(PROJECTS) + '; do '
              'printf "PIN %s " "$p"; git -C "/work/$p" rev-parse HEAD; done')
    args = [docker, 'run', '--rm', '--name', NAME, '--platform', 'linux/amd64',
            '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
            '--memory', '6g', '--cpus', '4', '--pids-limit', '512',
            '--mount', 'type=bind,src=' + str(ROOT / '.local/repo-bootstrap') + ',dst=/bootstrap,readonly',
            '--mount', 'type=volume,src=' + VOLUME + ',dst=/work',
            '--env', 'GIT_CONFIG_COUNT=3', '--env', 'GIT_CONFIG_KEY_0=user.name',
            '--env', 'GIT_CONFIG_VALUE_0=Local BOOX build', '--env', 'GIT_CONFIG_KEY_1=user.email',
            '--env', 'GIT_CONFIG_VALUE_1=boox-build@localhost', '--env', 'GIT_CONFIG_KEY_2=pack.threads',
            '--env', 'GIT_CONFIG_VALUE_2=2', '--env', 'GOMAXPROCS=2', image, '/bin/bash', '-c', script]
    try:
        with log.open('wb') as stream:
            process = subprocess.Popen(args, stdout=stream, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
            began, last = time.monotonic(), 0
            while process.poll() is None:
                free = shutil.disk_usage(ROOT).free
                if free < MIN_FREE or time.monotonic() - began > 3600:
                    subprocess.run([docker, 'stop', '--time', '15', NAME], capture_output=True, timeout=25)
                    raise RuntimeError('Physical disk floor or subset sync deadline reached')
                if time.monotonic() - last > 25:
                    lines = log.read_text(errors='replace').splitlines()
                    print(json.dumps({'elapsed_seconds': round(time.monotonic() - began),
                                      'physical_host_free_GB': round(free / 10**9, 2),
                                      'stage': lines[-1][-200:] if lines else 'starting'}), flush=True)
                    last = time.monotonic()
                time.sleep(2)
        record['exit_code'] = process.returncode
        record['elapsed_seconds'] = round(time.monotonic() - began, 2)
        lines = log.read_text(errors='replace').splitlines()
        record['pins'] = [line for line in lines if line.startswith('PIN ')]
        record['passed'] = process.returncode == 0 and 'TOOLCHAIN_SUBSET_SYNCED' in lines
        if not record['passed']:
            record['failure_tail'] = lines[-20:]
    except BaseException as exc:
        record.update(passed=False, failure_type=type(exc).__name__, failure_reason=str(exc))
        raise
    finally:
        record['physical_host_free_bytes_after'] = shutil.disk_usage(ROOT).free
        report.write_text(json.dumps(record, indent=2) + '\n')
        print(json.dumps(record, indent=2), flush=True)


if __name__ == '__main__':
    main()
