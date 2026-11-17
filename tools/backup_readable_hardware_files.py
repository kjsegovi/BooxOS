#!/usr/bin/env python3
"""Copy only inventoried ordinary /onyxconfig files twice over normal ADB.

No service programmer, root, reboot, block-device access or reader-side file
creation. This is a partial file-level supplement, never a raw restore image.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.private/hardware-file-backup-20261111'
ADB = [str(ROOT / '.local/platform-tools/adb'), '-P', '5041', '-d']


def main():
    paths = (OUT / 'source-inventory.txt').read_text().splitlines()
    if not 0 < len(paths) <= 100:
        raise SystemExit('Inventory outside the reviewed file-count bound')
    if len(paths) != len(set(paths)) or any(
        not re.fullmatch(r'/onyxconfig/[A-Za-z0-9_./-]+', p) or '..' in Path(p).parts for p in paths
    ):
        raise SystemExit('Inventory contains an unreviewed path')
    if sys.argv[1:] != ['--run-copy']:
        print(json.dumps({'files': len(paths), 'scope': 'ordinary files beneath /onyxconfig only',
                          'two_reads_and_matching_sha256_required': True, 'reader_writes': False,
                          'raw_partition_backup': False, 'device_access_performed': False}))
        return
    os.umask(0o077)
    env = os.environ.copy()
    env.update(ADB_MDNS_AUTO_CONNECT='', ANDROID_ADB_LOG_PATH=str(ROOT / '.local/adb-server.log'))

    def adb(args, timeout=15):
        return subprocess.run(ADB + args, env=env, capture_output=True, timeout=timeout)

    expected = {'ro.product.model': 'GoColor7_2', 'ro.boot.slot_suffix': '_a', 'sys.boot_completed': '1',
                'ro.build.display.id': '2026-04-21_13-54_4.2-rel_0421_19324b3ea'}

    def preflight():
        actual = {}
        for name in expected:
            p = adb(['shell', 'getprop', name])
            actual[name] = p.stdout.decode().strip()
        if actual != expected:
            raise RuntimeError('Exact original Android A state changed; stopped')
        return actual

    result = {'scope': 'readable ordinary hardware-configuration files; no raw filesystem image',
              'before': preflight(), 'files': [], 'device_writes': False, 'edl_used': False,
              'full_partition_backup': False, 'filesystem_metadata_preserved': False}
    total = 0
    for index, source in enumerate(paths):
        record = {'source': source, 'saved': False}
        result['files'].append(record)
        p = adb(['shell', 'stat', '-c', '%s:%a:%u:%g:%Y', source])
        if p.returncode:
            record['error'] = p.stderr.decode(errors='replace').strip()
            continue
        try:
            fields = p.stdout.decode().strip().split(':')
            size = int(fields[0])
        except (ValueError, IndexError):
            raise RuntimeError('Unexpected file metadata')
        if not 0 <= size <= 24 * 1024**2 or total + size > 48 * 1024**2:
            raise RuntimeError('Hardware file capture size bound exceeded')
        record['source_metadata'] = fields
        first = adb(['exec-out', 'cat', source], timeout=30)
        if first.returncode or len(first.stdout) != size:
            record['error'] = 'First read failed or file size changed'
            continue
        second = adb(['exec-out', 'cat', source], timeout=30)
        digest = hashlib.sha256(first.stdout).hexdigest()
        if second.returncode or len(second.stdout) != size or hashlib.sha256(second.stdout).hexdigest() != digest:
            record['error'] = 'Second read failed or file content changed'
            continue
        dest = OUT / 'files' / source.lstrip('/')
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists() and hashlib.sha256(dest.read_bytes()).hexdigest() != digest:
            raise RuntimeError('Prior saved capture differs; preserve it rather than overwrite')
        dest.write_bytes(first.stdout)
        dest.chmod(0o400)
        record.update(saved=True, bytes=size, sha256=digest, local=str(dest.relative_to(OUT)),
                      repeated_read_matches=True)
        total += size
        if (index + 1) % 5 == 0:
            print(json.dumps({'files_checked': index + 1, 'of': len(paths), 'bytes_saved': total}), flush=True)
    result.update(after=preflight(), saved_files=sum(p['saved'] for p in result['files']), saved_bytes=total)
    (OUT / 'file-manifest.json').write_text(json.dumps(result, indent=2) + '\n')
    inventory_errors = (OUT / 'source-inventory-errors.txt').read_text()
    summary = {k: result[k] for k in ['scope', 'device_writes', 'edl_used', 'full_partition_backup',
                                      'filesystem_metadata_preserved', 'saved_files', 'saved_bytes']}
    summary.update(inventoried_files=len(paths), capture_directory=str(OUT),
                   inventory_had_inaccessible_entries=bool(inventory_errors.strip()),
                   names_and_contents_kept_private=True, original_android_a_verified=True)
    (ROOT / 'work/hardware-file-backup-supplement-2026-11-11.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
