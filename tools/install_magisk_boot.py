#!/usr/bin/env python3
"""Install one inspected, exact-model Magisk boot image; no other partitions.

Requires the owner's root-install request and confirmed physical presence.
Never enters EDL, switches slots, erases, relocks, or disables verification.
"""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
ADB = ROOT / '.local/platform-tools/adb'
FB = ROOT / '.local/platform-tools/fastboot'
IMAGE = ROOT / '.private/magisk-root-20261111/boot.img'
EXPECTED = ['GoColor7_2', '2026-04-21_13-54_4.2-rel_0421_19324b3ea', '_a', '1', '0']


def main():
    use_fastbootd = sys.argv[1:] == ['--run-owner-present', '--fastbootd']
    if sys.argv[1:] != ['--run-owner-present'] and not use_fastbootd:
        print(json.dumps({'target': 'boot_a', 'image': str(IMAGE.relative_to(ROOT)),
                          'root_install': True, 'other_partitions_written': False,
                          'slot_change': False, 'data_reset': False, 'EDL': False}))
        return
    output_file = ROOT / ('work/magisk-root-install-fastbootd-2026-11-11.json' if use_fastbootd
                          else 'work/magisk-root-install-2026-11-11.json')
    if output_file.exists():
        raise RuntimeError('An installation report already exists; inspect it before any retry')
    if use_fastbootd:
        prior = json.loads((ROOT / 'work/magisk-root-install-2026-11-11.json').read_text())
        returned = json.loads((ROOT / 'work/native-magisk-write-rejected-stock-return-2026-11-11.json').read_text())
        if prior.get('write_completed') or not returned.get('android_returned'):
            raise RuntimeError('Prior native rejection / stock return not verified')
        flash = [c for c in prior['commands'] if c['arguments'][0] == 'flash']
        if len(flash) != 1 or "FAILED (remote: 'unknown command')" not in flash[0]['response']:
            raise RuntimeError('Prior write outcome is not the known unsupported command')
    review = json.loads((ROOT / 'work/magisk-boot-inspection-2026-11-11.json').read_text())
    if not review.get('passed') or hashlib.sha256(IMAGE.read_bytes()).hexdigest() != review['patched_sha256']:
        raise RuntimeError('Inspected image is absent or changed')
    record = {'started_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'scope': 'Owner-authorized Magisk root and Readest-only firewall; owner nearby',
              'image_sha256': review['patched_sha256'], 'target_partition': 'boot_a',
              'slot_changed': False, 'data_erased': False, 'edl_used': False,
              'other_partitions_written': False, 'write_attempted': False,
              'write_completed': False, 'android_returned': False, 'commands': [],
              'flashing_mode': 'stock fastbootd' if use_fastbootd else 'native bootloader'}
    env = os.environ.copy()
    env.update(ADB_MDNS_AUTO_CONNECT='', ANDROID_ADB_LOG_PATH=str(ROOT / '.local/adb-server.log'))
    serial = None

    def save():
        output_file.write_text(json.dumps(record, indent=2) + '\n')

    def adb(*args, timeout=10):
        return subprocess.run([str(ADB), '-P', '5041', '-d', *args], env=env,
                              capture_output=True, text=True, timeout=timeout)

    def properties():
        p = adb('shell', 'getprop ro.product.model; getprop ro.build.display.id; '
                'getprop ro.boot.slot_suffix; getprop sys.boot_completed; getprop ro.boot.flash.locked')
        return p.stdout.strip().splitlines() if p.returncode == 0 else []

    def fastboot(*args, timeout=15):
        allowed = (args == ('devices',) or args == ('reboot',) or
                   len(args) == 2 and args[0] == 'getvar' or
                   args == ('flash', 'boot_a', str(IMAGE)))
        if not allowed:
            raise RuntimeError('Fastboot operation outside the single-boot-image scope')
        command = [str(FB)] + (['-s', serial] if serial and args != ('devices',) else []) + list(args)
        p = subprocess.run(command, env=env, capture_output=True, text=True, timeout=timeout)
        output = p.stdout + p.stderr
        if serial:
            output = output.replace(serial, '<device>')
        if args != ('devices',):
            record['commands'].append({'arguments': list(args), 'exit_code': p.returncode,
                                       'response': output.strip()})
            save()
        return p, output

    def devices():
        p, _ = fastboot('devices')
        ids = [line.split()[0] for line in p.stdout.splitlines() if len(line.split()) >= 2]
        if len(ids) > 1:
            raise RuntimeError('Multiple fastboot devices; stopped')
        return ids[0] if ids else None

    def variable(key):
        p, output = fastboot('getvar', key)
        values = [line.strip()[len(key) + 2:] for line in output.splitlines()
                  if line.strip().startswith(key + ': ')]
        if p.returncode or len(values) != 1:
            raise RuntimeError('Required native bootloader query failed: ' + key)
        return values[0]

    def check_native(require_successful=True):
        expected = {'product': 'GoColor7_2' if use_fastbootd else 'lito',
                    'is-userspace': 'yes' if use_fastbootd else 'no', 'current-slot': 'a',
                    'slot-successful:a': 'yes', 'slot-unbootable:a': 'no'}
        status = {key: variable(key) for key in expected}
        required = expected if require_successful else {k: v for k, v in expected.items()
                                                       if k != 'slot-successful:a'}
        if any(status[k] != v for k, v in required.items()) or status['slot-successful:a'] not in ('yes', 'no'):
            raise RuntimeError('Native bootloader / known-good A status changed')
        return status

    try:
        record['before_android'] = properties()
        if record['before_android'] != EXPECTED:
            raise RuntimeError('Exact original unlocked Android A is not running')
        if adb('shell', 'settings get global wifi_on').stdout.strip() != '0':
            raise RuntimeError('Keep BOOX offline until the firewall is configured')
        battery = adb('shell', 'dumpsys battery').stdout
        levels = [int(line.split(':', 1)[1]) for line in battery.splitlines() if line.strip().startswith('level:')]
        if len(levels) != 1 or levels[0] < 50:
            raise RuntimeError('Insufficient or unknown battery charge')
        record['battery_percent'] = levels[0]
        if devices():
            raise RuntimeError('A fastboot device was present before the BOOX transition')
        save()
        if adb('reboot', 'fastboot' if use_fastbootd else 'bootloader').returncode:
            raise RuntimeError('Flashing-mode entry request failed')
        print('Entering ' + record['flashing_mode'] + ' for the one verified boot_a image.', flush=True)
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            serial = devices()
            if serial:
                break
            time.sleep(2)
        if not serial:
            raise RuntimeError('Native USB interface unavailable; owner return to Android needed')
        record['before_native'] = check_native()
        if use_fastbootd:
            record['snapshot_update_status'] = variable('snapshot-update-status')
            record['unlocked'] = variable('unlocked')
            if record['snapshot_update_status'] != 'none' or record['unlocked'] != 'yes':
                raise RuntimeError('Stock fastbootd lock / snapshot state is unsuitable')
        capacity = int(variable('partition-size:boot_a'), 0)
        download = int(variable('max-download-size'), 0)
        if capacity != review['partition_capacity_bytes'] or min(capacity, download) < IMAGE.stat().st_size:
            raise RuntimeError('Native image-size bounds do not match the inspected image')
        if hashlib.sha256(IMAGE.read_bytes()).hexdigest() != review['patched_sha256']:
            raise RuntimeError('Image changed before flash')
        record['write_attempted'] = True
        save()
        p, output = fastboot('flash', 'boot_a', str(IMAGE), timeout=90)
        if p.returncode or 'FAILED' in output:
            raise RuntimeError('Boot-image write did not report success; inspect before any retry')
        record['write_completed'] = True
        record['after_native'] = check_native(require_successful=False)
        save()
        p, output = fastboot('reboot')
        if p.returncode or 'FAILED' in output:
            raise RuntimeError('Normal restart failed; owner screen check needed')
        print('Verified Magisk boot image written. Waiting for stock Android A to finish startup.', flush=True)
        deadline = time.monotonic() + 240
        while time.monotonic() < deadline:
            after = properties()
            if after == EXPECTED:
                record['after_android'] = after
                record['android_returned'] = True
                break
            time.sleep(3)
        if not record['android_returned']:
            raise RuntimeError('Android startup not confirmed; inspect screen and USB before recovery')
        record['root_binary_presence'] = adb('shell', 'command -v su; command -v magisk').stdout.strip()
        record['wifi_after'] = adb('shell', 'settings get global wifi_on').stdout.strip()
        record['finished_at_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save()
        print(json.dumps({'write_completed': True, 'android_returned': True,
                          'stock_build_and_slot_unchanged': True,
                          'root_binary_presence': record['root_binary_presence'],
                          'wifi_still_off': record['wifi_after'] == '0'}), flush=True)
    except BaseException as exc:
        record.update(stopped=True, reason=str(exc))
        save()
        print(json.dumps({'stopped': True, 'reason': str(exc),
                          'write_attempted': record['write_attempted'],
                          'write_completed': record['write_completed']}), flush=True)
        raise


if __name__ == '__main__':
    main()
