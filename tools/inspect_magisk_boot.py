#!/usr/bin/env python3
"""Inspect a Magisk-patched copy of this exact BOOX stock boot image offline."""
import gzip
import hashlib
import json
import lzma
from pathlib import Path
import struct
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
STOCK = ROOT / '.local/firmware/GoColor7_2/2026-04-21_13-54_4.2-rel_0421_19324b3ea/images/boot.img'
STOCK_SHA = 'ede53420966b3af1a3a7b02cae3fef8583a0e01d19271006287dc14b4457ba63'
CAPACITY = 100663296


def sha(data):
    return hashlib.sha256(data).hexdigest()


def boot(data):
    if data[:8] != b'ANDROID!':
        raise RuntimeError('Not an Android boot image')
    page, version = struct.unpack_from('<II', data, 36)
    ks, rs, ss = (struct.unpack_from('<I', data, p)[0] for p in (8, 16, 24))
    recovery_size, recovery_offset, header_size, ds, dtb_addr = struct.unpack_from('<IQIIQ', data, 1632)
    if (page, version, ss, recovery_size, recovery_offset, header_size) != (4096, 2, 0, 0, 0, 1660):
        raise RuntimeError('Unexpected BOOX boot header geometry')
    aligned = lambda n: (n + page - 1) // page * page
    ramdisk_offset = page + aligned(ks)
    dtb_offset = ramdisk_offset + aligned(rs)
    if dtb_offset + ds > len(data):
        raise RuntimeError('Image components exceed file length')
    return {
        'kernel': data[page:page + ks],
        'ramdisk': data[ramdisk_offset:ramdisk_offset + rs],
        'dtb': data[dtb_offset:dtb_offset + ds],
        'stable_header': data[8:16] + data[20:40] + data[44:576] + data[608:1660],
        'os_version': struct.unpack_from('<I', data, 44)[0],
        'dtb_address': dtb_addr,
    }


def cpio(compressed):
    if compressed.startswith(b'\x1f\x8b'):
        data = gzip.decompress(compressed)
    elif compressed.startswith(b'\xfd7zXZ'):
        data = lzma.decompress(compressed)
    else:
        data = compressed
    entries, offset = {}, 0
    while data[offset:offset + 6] in (b'070701', b'070702'):
        vals = [int(data[offset + 6 + i * 8:offset + 14 + i * 8], 16) for i in range(13)]
        size, namesize = vals[6], vals[11]
        if not 0 < namesize < 4096:
            raise RuntimeError('Invalid ramdisk name length')
        name = data[offset + 110:offset + 110 + namesize - 1].decode().removeprefix('./')
        start = (offset + 110 + namesize + 3) // 4 * 4
        end = start + size
        if end > len(data):
            raise RuntimeError('Invalid ramdisk entry length')
        if name == 'TRAILER!!!':
            return entries
        entries[name] = {'content': data[start:end], 'metadata': vals[1:6]}
        offset = (end + 3) // 4 * 4
    raise RuntimeError('Ramdisk cpio trailer is absent')


def main():
    image = Path(sys.argv[1]).resolve()
    original, patched = STOCK.read_bytes(), image.read_bytes()
    if sha(original) != STOCK_SHA:
        raise RuntimeError('Stock boot hash changed')
    if not 0 < len(patched) <= CAPACITY or sha(patched) == STOCK_SHA:
        raise RuntimeError('Patched candidate is unchanged or exceeds partition capacity')
    a, b = boot(original), boot(patched)
    unchanged = {k: a[k] == b[k] for k in ('kernel', 'dtb', 'stable_header', 'os_version', 'dtb_address')}
    if not all(unchanged.values()):
        raise RuntimeError('Unexpected non-ramdisk change: ' + json.dumps(unchanged))
    old, new = cpio(a['ramdisk']), cpio(b['ramdisk'])
    changed = [name for name in old if name not in new or old[name] != new[name]]
    if changed != ['init']:
        raise RuntimeError('Unexpected original ramdisk entries changed: ' + repr(changed))
    apk = ROOT / '.local/android-apps/2026-11-11/Magisk-v31.1.apk'
    if sha(apk.read_bytes()) != '89cefac0a318afa39fb3880c45c87b036c05bc1ebf02a7a715b7f8d7c26ac6e7':
        raise RuntimeError('Official Magisk APK digest changed')
    with zipfile.ZipFile(apk) as z:
        expected_init = z.read('lib/arm64-v8a/libmagiskinit.so')
        for entry, library in (
            ('overlay.d/sbin/magisk.xz', 'lib/arm64-v8a/libmagisk.so'),
            ('overlay.d/sbin/init-ld.xz', 'lib/arm64-v8a/libinit-ld.so'),
        ):
            if lzma.decompress(new[entry]['content']) != z.read(library):
                raise RuntimeError('Embedded Magisk component differs from verified APK')
    if new['init']['content'] != expected_init:
        raise RuntimeError('Ramdisk init is not the verified release ARM64 Magisk init')
    config = new['.backup/.magisk']['content'].decode()
    values = dict(line.split('=', 1) for line in config.splitlines() if '=' in line)
    expected = {'KEEPVERITY': 'true', 'KEEPFORCEENCRYPT': 'true',
                'RECOVERYMODE': 'false', 'VENDORBOOT': 'false',
                'SHA1': hashlib.sha1(original).hexdigest()}
    if any(values.get(k) != v for k, v in expected.items()):
        raise RuntimeError('Unexpected Magisk configuration: ' + repr(values))
    backup_init = new.get('.backup/init')
    backup_compression = 'none'
    if backup_init is None and '.backup/init.xz' in new:
        backup_init = dict(new['.backup/init.xz'])
        backup_init['content'] = lzma.decompress(backup_init['content'])
        backup_compression = 'xz'
    if backup_init is None or backup_init != old['init']:
        raise RuntimeError('Original init backup is not byte-identical')
    report = {
        'model': 'GoColor7_2', 'stock_build': '2026-04-21_13-54_4.2-rel_0421_19324b3ea',
        'magisk_version': '31.1', 'image': str(image.relative_to(ROOT)),
        'stock_sha256': STOCK_SHA, 'patched_sha256': sha(patched),
        'image_bytes': len(patched), 'partition_capacity_bytes': CAPACITY,
        'unchanged_components': unchanged, 'original_ramdisk_changed': changed,
        'added_ramdisk_entries': sorted(set(new) - set(old)),
        'original_init_backup_matches': True,
        'original_init_backup_compression': backup_compression,
        'embedded_magisk_components_match_official_apk': True,
        'magisk_config': values,
        'manufacturer_parent_boot_hash_will_differ': True,
        'firmware_written': False, 'passed': True,
    }
    output = ROOT / 'work/magisk-boot-inspection-2026-11-11.json'
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
