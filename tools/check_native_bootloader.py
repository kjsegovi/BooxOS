#!/usr/bin/env python3
"""One native-bootloader connection/query/return check. Never load an image.

Use only with the owner near the reader for the physical power-button fallback.
This does not use EDL, set_active, boot/download, flash, erase, unlock, or root.
"""
import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
ADB = ROOT / '.local/platform-tools/adb'
FASTBOOT = ROOT / '.local/platform-tools/fastboot'
EXPECTED = {'ro.product.model': 'GoColor7_2',
            'ro.build.display.id': '2026-04-21_13-54_4.2-rel_0421_19324b3ea',
            'ro.boot.slot_suffix': '_a', 'sys.boot_completed': '1'}


def main():
    if sys.argv[1:] != ['--run-owner-present']:
        print(json.dumps({'purpose': 'query native bootloader then return to Android',
                          'entry': 'adb reboot bootloader', 'image_downloaded': False,
                          'queries': ['product', 'is-userspace', 'current-slot',
                                      'slot-successful:a', 'slot-unbootable:a', 'max-download-size'],
                          'exit': 'one fastboot reboot; verify original Android',
                          'fallback': 'If USB is unavailable, stop for owner power-button restart',
                          'device_writes_or_slot_changes': False}, indent=2))
        return
    os.umask(0o077)
    env = os.environ.copy()
    env['ADB_MDNS_AUTO_CONNECT'] = ''
    env['ANDROID_ADB_LOG_PATH'] = str(ROOT / '.local/adb-server.log')
    record = {'scope': 'native bootloader queries and return only; owner present',
              'firmware_images_loaded_or_written': False, 'slot_changed': False,
              'edl_programmer_used': False, 'commands': [], 'android_returned': False}
    path = ROOT / 'work/native-bootloader-check-2026-11-11.json'
    serial = None

    def save():
        path.write_text(json.dumps(record, indent=2) + '\n')

    def adb(args):
        result = subprocess.run([str(ADB), '-P', '5041', '-d'] + args,
                                env=env, capture_output=True, text=True, timeout=8)
        return result

    def props():
        return {key: adb(['shell', 'getprop', key]).stdout.strip() for key in EXPECTED}

    def fastboot(args):
        if not (args == ['devices'] or args == ['reboot'] or len(args) == 2 and args[0] == 'getvar'):
            raise RuntimeError('Command outside query/restart scope')
        command = [str(FASTBOOT)] + (['-s', serial] if serial and args != ['devices'] else []) + args
        result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=8)
        output = result.stdout + result.stderr
        if serial:
            output = output.replace(serial, '<device>')
        if args != ['devices']:
            record['commands'].append({'arguments': args, 'rc': result.returncode, 'response': output.strip()})
            save()
        return result, output

    try:
        record['before'] = props()
        if record['before'] != EXPECTED:
            raise RuntimeError('Original Android preflight changed')
        preexisting, _ = fastboot(['devices'])
        if preexisting.stdout.strip():
            raise RuntimeError('A fastboot device was already present before the BOOX transition')
        record['entry_at_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save()
        if adb(['reboot', 'bootloader']).returncode:
            raise RuntimeError('Native bootloader request failed')
        print('Native bootloader requested; no image was sent.', flush=True)
        began = time.monotonic()
        while time.monotonic() - began < 60:
            result, _ = fastboot(['devices'])
            found = [line.split()[0] for line in result.stdout.splitlines() if len(line.split()) >= 2]
            if len(found) == 1:
                serial = found[0]
                break
            if len(found) > 1:
                raise RuntimeError('More than one fastboot device')
            time.sleep(2)
        if serial is None:
            record['physical_restart_needed'] = True
            raise RuntimeError('No native fastboot interface found; stop for physical restart')
        record['variables'] = {}
        for key in ['product', 'is-userspace', 'current-slot', 'slot-successful:a', 'slot-unbootable:a', 'max-download-size']:
            _, output = fastboot(['getvar', key])
            record['variables'][key] = output.strip()
        save()
        print(json.dumps({'variables': record['variables']}), flush=True)
        product_lines = {line.strip() for line in record['variables']['product'].splitlines()}
        # This exact device's native bootloader reports its Qualcomm board name;
        # fastbootd instead reports GoColor7_2. The exact Android preflight and
        # absence of any prior fastboot device establish this transition.
        product_ok = bool(product_lines & {'product: GoColor7_2', 'product: lito'})
        native_mode = any(line.strip() == 'is-userspace: no'
                          for line in record['variables']['is-userspace'].splitlines())
        record['native_bootloader_reachable'] = native_mode
        if not product_ok or not native_mode:
            raise RuntimeError('Fastboot model not verified; no restart command will be sent')
        result, output = fastboot(['reboot'])
        if result.returncode or 'FAILED' in output:
            raise RuntimeError('Normal restart command failed; inspect screen')
        began = time.monotonic()
        while time.monotonic() - began < 180:
            current = props()
            if current == EXPECTED:
                record['after'] = current
                record['android_returned'] = True
                break
            time.sleep(2)
        save()
        print(json.dumps({'android_returned': record['android_returned']}), flush=True)
    except BaseException as exc:
        record.update(stopped=True, reason=str(exc))
        save()
        print(json.dumps({'stopped': True, 'reason': str(exc)}), flush=True)
        raise


if __name__ == '__main__':
    main()
