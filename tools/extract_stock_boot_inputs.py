#!/usr/bin/env python3
"""Extract and describe exact stock boot inputs locally; never access a device.

These files are porting inputs, not a newly built or installable boot image.
Android boot-image v2 and DTBO formats are checked before extraction.
"""
import hashlib
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
FIRMWARE = ROOT / '.local/firmware/GoColor7_2/2026-04-21_13-54_4.2-rel_0421_19324b3ea/images'
OUTPUT = ROOT / '.local/porting-inputs/stock-boot'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def aligned(value, page):
    return (value + page - 1) // page * page


def read_fdt(data):
    if len(data) < 40:
        raise ValueError('FDT header truncated')
    magic, total, structs, strings, reserves, version, compat, cpu, string_size, struct_size = struct.unpack_from('>10I', data)
    if magic != 0xd00dfeed or total > len(data) or total < 40 or strings + string_size > total or structs + struct_size > total or version < 16:
        raise ValueError('Invalid FDT bounds')
    table = data[strings:strings + string_size]
    position = structs
    stack, result = [], []
    while position < structs + struct_size:
        token = struct.unpack_from('>I', data, position)[0]
        position += 4
        if token == 1:
            end = data.index(b'\0', position, total)
            stack.append(data[position:end].decode(errors='replace'))
            position = aligned(end + 1, 4)
        elif token == 2:
            if not stack:
                raise ValueError('Unbalanced FDT node')
            stack.pop()
        elif token == 3:
            length, name_offset = struct.unpack_from('>II', data, position)
            position += 8
            if name_offset >= len(table) or position + length > structs + struct_size:
                raise ValueError('Invalid FDT property')
            name = table[name_offset:table.index(b'\0', name_offset)].decode(errors='replace')
            value = data[position:position + length]
            position = aligned(position + length, 4)
            path = '/' + '/'.join(x for x in stack if x)
            if path == '/' and name in ['model', 'compatible'] or any(s in (path + '/' + name).lower() for s in ['ebc', 'eink', 'backlight', 'frontlight', 'i2c', 'color', 'waveform']):
                if value and value[-1:] == b'\0' and all(32 <= c < 127 or c == 0 for c in value):
                    decoded = value.rstrip(b'\0').decode(errors='replace').replace('\0', ' | ')
                elif len(value) <= 64 and len(value) % 4 == 0:
                    decoded = [hex(x) for x in struct.unpack('>' + 'I' * (len(value) // 4), value)]
                else:
                    decoded = {'bytes': len(value), 'sha256': sha(value)}
                result.append({'node': path, 'property': name, 'value': decoded})
        elif token == 4:
            continue
        elif token == 9:
            break
        else:
            raise ValueError('Unknown FDT token')
    return {'total_bytes': total, 'version': version, 'selected_properties': result}


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    validation = json.loads((ROOT / 'work/stock-firmware-validation-2026-11-11.json').read_text())
    expected = {x['name']: x for x in validation['payload']['partitions']}
    boot = (FIRMWARE / 'boot.img').read_bytes()
    dtbo = (FIRMWARE / 'dtbo.img').read_bytes()
    for name, data in [('boot', boot), ('dtbo', dtbo)]:
        if sha(data) != expected[name]['expected_sha256'] or len(data) != expected[name]['size']:
            raise ValueError('Source image differs from validated full OTA: ' + name)
    if boot[:8] != b'ANDROID!':
        raise ValueError('Unsupported boot image magic')
    kernel_size, kernel_addr, ramdisk_size, ramdisk_addr, second_size, second_addr, tags_addr, page, version, os_version = struct.unpack_from('<10I', boot, 8)
    if version != 2 or page != 4096 or second_size != 0:
        raise ValueError('Unexpected boot v2 geometry')
    recovery_dtbo_size, recovery_dtbo_offset, header_size, dtb_size, dtb_addr = struct.unpack_from('<IQIIQ', boot, 1632)
    kernel_offset = page
    ramdisk_offset = kernel_offset + aligned(kernel_size, page)
    dtb_offset = ramdisk_offset + aligned(ramdisk_size, page) + aligned(second_size, page) + aligned(recovery_dtbo_size, page)
    pieces = [('kernel', kernel_offset, kernel_size), ('ramdisk.gz', ramdisk_offset, ramdisk_size), ('dtb.img', dtb_offset, dtb_size)]
    files = []
    for name, offset, length in pieces:
        if not 0 < length <= len(boot) - offset:
            raise ValueError('Component outside stock boot image')
        content = boot[offset:offset + length]
        (OUTPUT / name).write_bytes(content)
        files.append({'path': str((OUTPUT / name).relative_to(ROOT)), 'offset': offset, 'bytes': length, 'sha256': sha(content)})
    (OUTPUT / 'dtbo.img').write_bytes(dtbo)
    files.append({'path': str((OUTPUT / 'dtbo.img').relative_to(ROOT)), 'bytes': len(dtbo), 'sha256': sha(dtbo)})
    dtb = boot[dtb_offset:dtb_offset + dtb_size]
    base_fdt = []
    cursor = 0
    while cursor < len(dtb) and dtb[cursor:cursor + 4] == b'\xd0\x0d\xfe\xed':
        parsed = read_fdt(dtb[cursor:])
        base_fdt.append(parsed)
        cursor += aligned(parsed['total_bytes'], 4)
    if not base_fdt:
        raise ValueError('Stock DTB component has no valid FDT')
    magic, total_size, dtbo_header, entry_size, entry_count, entries_offset, dtbo_page, dtbo_version = struct.unpack_from('>8I', dtbo)
    if magic != 0xd7b7ab1e or total_size > len(dtbo) or entry_size < 32 or entries_offset + entry_count * entry_size > total_size:
        raise ValueError('Invalid Android DTBO table')
    overlays = []
    for index in range(entry_count):
        size, offset, ident, rev, *custom = struct.unpack_from('>8I', dtbo, entries_offset + index * entry_size)
        if offset + size > total_size:
            raise ValueError('DTBO overlay outside image')
        data = dtbo[offset:offset + size]
        target = OUTPUT / ('overlay-%02d.dtb' % index)
        target.write_bytes(data)
        overlays.append({'index': index, 'id': ident, 'revision': rev, 'custom': custom, 'bytes': size, 'sha256': sha(data), 'fdt': read_fdt(data)})
    report = {'model': 'GoColor7_2', 'source': 'matched full stock OTA', 'installable_candidate': False,
              'boot_header': {'version': version, 'page_size': page, 'kernel_size': kernel_size,
                              'ramdisk_size': ramdisk_size, 'dtb_size': dtb_size, 'dtb_offset': dtb_offset},
              'files': files, 'base_device_trees': base_fdt, 'dtbo_table': {'entries': entry_count, 'page_size': dtbo_page, 'version': dtbo_version},
              'overlays': overlays}
    path = ROOT / 'work/stock-boot-porting-inputs-2026-11-11.json'
    path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'report': str(path), 'stock_components_extracted': len(files), 'base_trees': len(base_fdt), 'overlays': len(overlays), 'installable_candidate': False}))


if __name__ == '__main__':
    main()
