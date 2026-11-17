#!/usr/bin/env python3
"""Review, or explicitly run, one untouched-stock native RAM-boot trial.

Default: validate the local stock asset and print/write the plan, no USB access.
Only --run-approved enters the bootloader, boots that exact asset once and
checks return to original Android. No partition flash, erase or slot command.
Normal Android execution can write normal persistent runtime state.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
BUILD = '2026-04-21_13-54_4.2-rel_0421_19324b3ea'
IMAGE = ROOT / '.local/firmware/GoColor7_2' / BUILD / 'images/boot.img'
HASH = 'ede53420966b3af1a3a7b02cae3fef8583a0e01d19271006287dc14b4457ba63'
SIZE = 100663296
ADB = ROOT / '.local/platform-tools/adb'
FASTBOOT = ROOT / '.local/platform-tools/fastboot'
EXPECTED = {'ro.product.model': 'GoColor7_2', 'ro.build.display.id': BUILD,
            'ro.boot.slot_suffix': '_a', 'sys.boot_completed': '1',
            'ro.boot.flash.locked': '0', 'ro.boot.vbmeta.device_state': 'unlocked'}


def validated_asset():
    if IMAGE.stat().st_size != SIZE:
        raise RuntimeError('Stock boot asset size mismatch')
    digest = hashlib.sha256(IMAGE.read_bytes()).hexdigest()
    if digest != HASH:
        raise RuntimeError('Stock boot asset hash mismatch')
    return {'path': str(IMAGE), 'bytes': SIZE, 'sha256': digest, 'modified': False}


def plan():
    record = {'model': 'GoColor7_2', 'build': BUILD, 'asset': validated_asset(),
              'scope': 'one unchanged stock boot image downloaded and executed from RAM',
              'entry': 'original Android A -> native bootloader',
              'required_status': 'product=lito, is-userspace=no, A successful and bootable, sufficient download size',
              'trial': 'exact validated stock image via fastboot boot, at most once',
              'success': 'command accepted and exact original Android A startup completed',
              'fallback': 'if command is rejected and native A remains bootable, one normal reboot; otherwise stop for owner',
              'no_commands_for': ['flash', 'erase', 'format', 'set_active', 'unlock', 'EDL', 'root'],
              'persistent_partition_image_write_requested': False,
              'runtime_storage_is_read_only': False,
              'owner_needed': 'stay nearby with USB connected for power-button fallback',
              'modified_image_support_proven_by_this_test': False,
              'lineage_install_or_restore_test': False, 'approval_required': True}
    (ROOT / 'work/stock-ram-boot-test-plan-2026-11-11.json').write_text(json.dumps(record, indent=2) + '\n')
    return record


def run(record):
    env = os.environ.copy()
    env.update(ADB_MDNS_AUTO_CONNECT='', ANDROID_ADB_LOG_PATH=str(ROOT / '.local/adb-server.log'))
    path = ROOT / 'work/stock-ram-boot-test-result-2026-11-11.json'
    serial = None
    boot_count = 0
    record.update(approval_required=False, run_scope='owner-approved unchanged-stock RAM trial',
                  commands=[], android_returned=False, boot_command_accepted=False,
                  edl_used=False, slot_change_requested=False)

    def save():
        path.write_text(json.dumps(record, indent=2) + '\n')

    def adb(args):
        return subprocess.run([str(ADB), '-P', '5041', '-d'] + args, env=env,
                              capture_output=True, text=True, timeout=10)

    def props():
        first = adb(['shell', 'getprop', 'ro.product.model'])
        if first.returncode:
            return {}
        values = {'ro.product.model': first.stdout.strip()}
        values.update({key: adb(['shell', 'getprop', key]).stdout.strip()
                       for key in EXPECTED if key != 'ro.product.model'})
        return values

    def fb(args):
        nonlocal boot_count
        if args == ['boot', str(IMAGE)]:
            if boot_count:
                raise RuntimeError('Only one RAM-boot command is permitted')
            validated_asset()
            boot_count += 1
            timeout = 60
        elif args in [['devices'], ['reboot']] or len(args) == 2 and args[0] == 'getvar':
            timeout = 10
        else:
            raise RuntimeError('Fastboot operation outside the exact stock RAM-test scope')
        command = [str(FASTBOOT)] + (['-s', serial] if serial and args != ['devices'] else []) + args
        p = subprocess.run(command, env=env, capture_output=True, text=True, timeout=timeout)
        response = (p.stdout + p.stderr).replace(serial, '<device>') if serial else p.stdout + p.stderr
        if args != ['devices']:
            record['commands'].append({'arguments': args, 'exit_code': p.returncode, 'response': response.strip()})
            save()
        return p, response

    def device():
        p, _ = fb(['devices'])
        found = [line.split()[0] for line in p.stdout.splitlines() if len(line.split()) >= 2]
        if len(found) > 1:
            raise RuntimeError('More than one fastboot device; stopped')
        return found[0] if found else None

    def variable(name):
        p, response = fb(['getvar', name])
        if p.returncode:
            raise RuntimeError('Required bootloader query failed: ' + name)
        prefix = name + ': '
        values = [line.strip()[len(prefix):] for line in response.splitlines() if line.strip().startswith(prefix)]
        if len(values) != 1:
            raise RuntimeError('Ambiguous bootloader response: ' + name)
        return values[0]

    def native_a_status():
        for name, value in {'product': 'lito', 'is-userspace': 'no', 'current-slot': 'a',
                            'slot-successful:a': 'yes', 'slot-unbootable:a': 'no'}.items():
            if variable(name) != value:
                raise RuntimeError('Native bootloader/A-slot state changed: ' + name)

    try:
        record['before'] = props()
        if record['before'] != EXPECTED:
            raise RuntimeError('Original unlocked Android A preflight changed')
        if device():
            raise RuntimeError('A fastboot device was already present before the BOOX transition')
        if adb(['reboot', 'bootloader']).returncode:
            raise RuntimeError('Native bootloader entry request failed')
        print('Native bootloader requested for the approved stock RAM trial.', flush=True)
        start = time.monotonic()
        while time.monotonic() - start < 60:
            serial = device()
            if serial:
                break
            time.sleep(2)
        if not serial:
            raise RuntimeError('No native USB interface; owner power-button return needed')
        native_a_status()
        if int(variable('max-download-size'), 0) < SIZE:
            raise RuntimeError('Stock boot image exceeds reported RAM download capacity')
        p, response = fb(['boot', str(IMAGE)])
        record['boot_command_accepted'] = p.returncode == 0 and 'FAILED' not in response
        if not record['boot_command_accepted']:
            print('Stock RAM-boot command rejected; checking A before one normal restart.', flush=True)
            if device() != serial:
                raise RuntimeError('Native USB connection changed after rejection')
            native_a_status()
            p, response = fb(['reboot'])
            if p.returncode or 'FAILED' in response:
                raise RuntimeError('Normal restart rejected; owner intervention needed')
        else:
            print('Stock RAM-boot command accepted; waiting for original Android A.', flush=True)
        start = time.monotonic()
        while time.monotonic() - start < 180:
            after = props()
            if after == EXPECTED:
                record.update(after=after, android_returned=True)
                break
            time.sleep(2)
        record['stock_ram_boot_path_qualified'] = record['boot_command_accepted'] and record['android_returned']
        if not record['android_returned']:
            record['owner_intervention_needed'] = True
        save()
        print(json.dumps({'boot_command_accepted': record['boot_command_accepted'],
                          'android_returned': record['android_returned'],
                          'stock_ram_boot_path_qualified': record['stock_ram_boot_path_qualified']}), flush=True)
    except BaseException as exc:
        record.update(stopped=True, reason=str(exc), owner_intervention_needed=True)
        save()
        print(json.dumps({'stopped': True, 'reason': str(exc)}), flush=True)
        raise


def main():
    if sys.argv[1:] not in [[], ['--run-approved']]:
        raise SystemExit('Only no arguments (review) or --run-approved is accepted')
    record = plan()
    if sys.argv[1:]:
        run(record)
    else:
        print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
