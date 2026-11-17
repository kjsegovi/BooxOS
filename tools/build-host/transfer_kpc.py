#!/usr/bin/env python3
"""Copy the existing private Lineage workspace to the user's KPC over SSH."""
import datetime
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
IMAGE = 'sha256:b4ece63d16da55dab0405cd8a691454e30dfac308602ee2797e88f35d53cadb2'
VOLUME = 'booxos-lineage21-source-20261111'
REMOTE = '/home/kjseg/booxos-lineage21-20261115'
LOG = ROOT / 'work/kpc-transfer-2026-11-15.log'
REPORT = ROOT / 'work/kpc-transfer-2026-11-15.json'


def run_pipeline(commands, label, log):
    processes = []
    previous = None
    for command in commands:
        process = subprocess.Popen(command, stdin=previous.stdout if previous else subprocess.DEVNULL,
                                   stdout=subprocess.PIPE if len(processes) < len(commands)-1 else log,
                                   stderr=log)
        if previous:
            previous.stdout.close()
        processes.append(process)
        previous = process
    began = time.monotonic()
    try:
        while any(p.poll() is None for p in processes):
            if any(p.poll() not in (None, 0) for p in processes):
                raise RuntimeError(label + ' pipeline failed')
            check = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
                                    'framework-wsl', 'df -B1 --output=avail /mnt/c | tail -1'],
                                   capture_output=True, text=True, timeout=25)
            free = int(check.stdout.strip()) if check.returncode == 0 else None
            print(json.dumps({'stage': label, 'elapsed_seconds': round(time.monotonic()-began),
                              'kpc_disk_free_GiB': round(free/1024**3, 1) if free else None}), flush=True)
            if free is not None and free < 40*1024**3:
                raise RuntimeError('KPC disk space reached the 40 GiB floor')
            time.sleep(20)
        codes = [p.wait() for p in processes]
        if any(codes):
            raise RuntimeError(label + ' exit codes: ' + str(codes))
    finally:
        for p in reversed(processes):
            if p.poll() is None:
                p.terminate()
        for p in processes:
            try:
                p.wait(timeout=20)
            except subprocess.TimeoutExpired:
                p.kill()


def main():
    record = {'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'destination': REMOTE, 'image': IMAGE, 'passed': False,
              'boox_access': False, 'source_out_directory_excluded': True}
    try:
        with LOG.open('w') as log:
            run_pipeline([['docker', 'save', IMAGE], ['gzip', '-1'],
                          ['ssh', '-o', 'BatchMode=yes', 'framework-windows',
                           'wsl -d Ubuntu -u root --exec docker load']], 'build environment transfer', log)
            run_pipeline([['docker', 'run', '--rm', '--platform', 'linux/amd64', '--network', 'none',
                           '--mount', 'type=volume,src='+VOLUME+',dst=/work,readonly',
                           IMAGE, 'tar', '--exclude=./out', '-cf', '-', '.'],
                          ['gzip', '-1'], ['ssh', '-o', 'BatchMode=yes', 'framework-wsl',
                                          'umask 077; tar --no-same-owner -xzf - -C '+REMOTE+'/source']],
                         'source transfer', log)
        record['passed'] = True
    except BaseException as exc:
        record['error'] = str(exc)
        raise
    finally:
        record['finished_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        REPORT.write_text(json.dumps(record, indent=2)+'\n')
        print(json.dumps(record), flush=True)


if __name__ == '__main__':
    main()
