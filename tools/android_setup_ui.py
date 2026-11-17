#!/usr/bin/env python3
"""Inspect or tap a freshly observed Android setup control over authenticated ADB.

No firmware, root, reboot, shell-evaluation, or arbitrary-coordinate interface.
Private UI snapshots stay under .private rather than public work reports.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ADB = ROOT / '.local/platform-tools/adb'
REMOTE = '/data/local/tmp/boox-customization-ui.xml'


def adb(*args):
    env = os.environ.copy()
    env.update(ADB_MDNS_AUTO_CONNECT='',
               ANDROID_ADB_LOG_PATH=str(ROOT / '.local/adb-server.log'))
    result = subprocess.run([str(ADB), '-P', '5041', '-d', *args],
                            env=env, capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise RuntimeError(result.stderr + result.stdout)
    return result.stdout


def snapshot(label):
    if adb('shell', 'getprop', 'ro.product.model').strip() != 'GoColor7_2':
        raise RuntimeError('Exact BOOX model not present')
    adb('shell', 'uiautomator', 'dump', REMOTE)
    xml = adb('shell', 'cat', REMOTE)
    directory = ROOT / '.private/android-setup-ui-20261111'
    directory.mkdir(parents=True, exist_ok=True)
    name = re.sub(r'[^a-zA-Z0-9_-]', '_', label)
    (directory / (name + '.xml')).write_text(xml)
    return ET.fromstring(xml)


def display(tree):
    print('UI controls: [label, resource-id, bounds, checked-if-checkable]')
    for node in tree.iter('node'):
        a = node.attrib
        label = a.get('text') or a.get('content-desc')
        if label or a.get('checkable') == 'true' or a.get('clickable') == 'true' and a.get('resource-id'):
            print(json.dumps([label, a.get('resource-id'), a.get('bounds'),
                              a.get('checked') if a.get('checkable') == 'true' else None],
                             ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['dump', 'tap', 'back'])
    parser.add_argument('--label', required=True)
    selector = parser.add_mutually_exclusive_group()
    selector.add_argument('--resource-id')
    selector.add_argument('--text')
    selector.add_argument('--description')
    selector.add_argument('--bounds', help='Exact bounds of a control observed in a UI snapshot/screenshot')
    parser.add_argument('--index', type=int)
    args = parser.parse_args()
    tree = snapshot(args.label + '-before')
    if args.action == 'back':
        adb('shell', 'input', 'keyevent', 'KEYCODE_BACK')
        tree = snapshot(args.label + '-after')
    if args.action == 'tap':
        key, value = next(((k, v) for k, v in (
            ('resource-id', args.resource_id), ('text', args.text),
            ('content-desc', args.description), ('bounds', args.bounds)) if v is not None), (None, None))
        if key is None:
            raise RuntimeError('A previously observed selector is required')
        matches = [n for n in tree.iter('node') if n.get(key) == value
                   and n.get('enabled') == 'true'
                   and (key != 'bounds' or n.get('clickable') == 'true')]
        if args.index is None and len(matches) != 1:
            raise RuntimeError(f'Expected one exact match; found {len(matches)}')
        index = args.index if args.index is not None else 0
        if index < 0 or index >= len(matches):
            raise RuntimeError('Selected index is absent')
        node = matches[index]
        box = re.fullmatch(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', node.get('bounds', ''))
        if box is None:
            raise RuntimeError('Control has no observed bounds')
        x1, y1, x2, y2 = map(int, box.groups())
        if x2 <= x1 or y2 <= y1:
            raise RuntimeError('Control has no visible area')
        adb('shell', 'input', 'tap', str((x1 + x2) // 2), str((y1 + y2) // 2))
        tree = snapshot(args.label + '-after')
    display(tree)


if __name__ == '__main__':
    main()
