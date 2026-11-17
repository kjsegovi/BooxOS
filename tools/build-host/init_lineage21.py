#!/usr/bin/env python3
"""Verify Repo and initialize only a pinned Lineage 21 manifest on this Mac.

No platform source sync, build, USB access, firmware operation or Docker setting
change. Sources live in a Linux volume, not the Mac's insensitive filesystem.
"""
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP = ROOT / '.local/repo-bootstrap'
OUT = ROOT / '.local/mac-build-probe'
VOLUME = 'booxos-lineage21-source-20261111'
MANIFEST_COMMIT = '121f4ec5f11dc98ff2c427bc9d23165e914c54bb'
EXPECTED_PRIMARY_KEY = '8BB9AD793E8E6153AF0F9A4416530D5E920F5C65'
REPORT = ROOT / 'work/lineage21-source-init-2026-11-11.json'


def main():
    docker = shutil.which('docker')
    if not docker:
        raise SystemExit('Docker client unavailable')
    context = subprocess.run([docker, 'context', 'inspect'], capture_output=True, text=True, check=True, timeout=10)
    if not json.loads(context.stdout)[0]['Endpoints']['docker']['Host'].startswith('unix://'):
        raise SystemExit('Only local Docker is allowed')
    image = subprocess.run([docker, 'image', 'inspect', 'booxos-android-build:ubuntu22-20261111',
                            '--format', '{{.Id}}'], capture_output=True, text=True, check=True, timeout=10).stdout.strip()
    for item in json.loads((BOOTSTRAP / 'source-manifest.json').read_text()):
        if hashlib.sha256((BOOTSTRAP / item['file']).read_bytes()).hexdigest() != item['sha256']:
            raise SystemExit('Bootstrap file changed')
    record = {'image': image, 'volume': VOLUME, 'manifest_commit': MANIFEST_COMMIT,
              'manifest_branch': 'lineage-21.0', 'full_source_synced': False,
              'boox_access': False, 'docker_settings_changed': False,
              'started_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    common = [docker, 'run', '--rm', '--platform', 'linux/amd64', '--cap-drop', 'ALL',
              '--security-opt', 'no-new-privileges', '--memory', '2g', '--cpus', '2',
              '--pids-limit', '256', '--mount', 'type=bind,src=' + str(BOOTSTRAP) + ',dst=/bootstrap,readonly']
    try:
        verify = ('set -eu; mkdir -m 700 /tmp/repo-gpg; '
                  'gpg --batch --homedir /tmp/repo-gpg --import /bootstrap/maintainer-keys.asc; '
                  'gpg --batch --homedir /tmp/repo-gpg --status-fd 1 --verify /bootstrap/repo.asc /bootstrap/repo')
        result = subprocess.run(common + ['--network', 'none', image, '/bin/bash', '-c', verify],
                                capture_output=True, text=True, timeout=30)
        output = result.stdout + result.stderr
        (OUT / 'repo-signature-verification.txt').write_text(output)
        valid_lines = [line for line in output.splitlines() if line.startswith('[GNUPG:] VALIDSIG ')]
        record['repo_signature_verified'] = (result.returncode == 0 and
            any(EXPECTED_PRIMARY_KEY in line for line in valid_lines))
        if not record['repo_signature_verified']:
            raise RuntimeError('Repo signature did not validate under the documented primary key')
        print('Repo launcher signature verified against the documented Google key.', flush=True)
        existing = subprocess.run([docker, 'volume', 'inspect', VOLUME], capture_output=True, text=True, timeout=10)
        if existing.returncode == 0:
            labels = json.loads(existing.stdout)[0].get('Labels') or {}
            if labels.get('project') != 'BooxOS':
                raise RuntimeError('Existing volume belongs to another task')
        else:
            subprocess.run([docker, 'volume', 'create', '--label', 'project=BooxOS',
                            '--label', 'purpose=lineage21-source', VOLUME],
                           capture_output=True, text=True, check=True, timeout=10)
        if shutil.disk_usage(ROOT).free < 20 * 1024**3:
            raise RuntimeError('Insufficient free host space even for initialization')
        script = ('set -eu; python3 /bootstrap/repo init '
                  '-u https://github.com/LineageOS/android.git '
                  '-b ' + MANIFEST_COMMIT + ' --manifest-upstream-branch lineage-21.0 '
                  '--depth=1 --partial-clone --clone-filter=blob:none --no-clone-bundle --no-tags --git-lfs; '
                  'python3 /bootstrap/repo manifest -o /work/preparation-manifest.xml; '
                  'python3 /bootstrap/repo list -a > /work/preparation-projects.txt; '
                  'printf "MANIFEST_COMMIT="; git -C /work/.repo/manifests rev-parse HEAD; '
                  'printf "PROJECT_COUNT="; wc -l < /work/preparation-projects.txt')
        args = common + ['--name', 'booxos-lineage21-init-20261111', '--mount',
                'type=volume,src=' + VOLUME + ',dst=/work', '--env', 'GIT_CONFIG_COUNT=2',
                '--env', 'GIT_CONFIG_KEY_0=user.name', '--env', 'GIT_CONFIG_VALUE_0=Local BOOX build',
                '--env', 'GIT_CONFIG_KEY_1=user.email', '--env', 'GIT_CONFIG_VALUE_1=boox-build@localhost',
                image, '/bin/bash', '-c', script]
        log = OUT / 'lineage21-init.log'
        with log.open('wb') as stream:
            process = subprocess.Popen(args, stdout=stream, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
            began, last = time.monotonic(), 0
            while process.poll() is None:
                if time.monotonic() - began > 600:
                    subprocess.run([docker, 'stop', '--time', '10', 'booxos-lineage21-init-20261111'],
                                   capture_output=True, timeout=20)
                    raise RuntimeError('Source initialization deadline exceeded')
                if time.monotonic() - last > 25:
                    lines = log.read_text(errors='replace').splitlines()
                    print(json.dumps({'elapsed_seconds': round(time.monotonic() - began),
                                      'stage': lines[-1][-180:] if lines else 'initializing'}), flush=True)
                    last = time.monotonic()
                time.sleep(2)
        record['exit_code'] = process.returncode
        record['elapsed_seconds'] = round(time.monotonic() - began, 2)
        lines = log.read_text(errors='replace').splitlines()
        record['result_lines'] = lines[-18:]
        record['passed'] = process.returncode == 0 and any('MANIFEST_COMMIT=' + MANIFEST_COMMIT in line for line in lines)
    except BaseException as exc:
        record.update(passed=False, failure_type=type(exc).__name__, failure_reason=str(exc))
        raise
    finally:
        REPORT.write_text(json.dumps(record, indent=2) + '\n')
        print(json.dumps(record, indent=2), flush=True)


if __name__ == '__main__':
    main()
