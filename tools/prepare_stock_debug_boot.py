#!/usr/bin/env python3
"""Build and inspect a local stock-based debug-boot experiment; never use USB.

This artifact enables authenticated ADB root on request. Its su domain is
permissive, as in an AOSP userdebug design. It is not a read-only OS, a release,
or authorized for flashing. The manufacturer's parent boot hash will differ.
"""
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.private/stock-debug-boot-development-20261111'
STOCK = ROOT / '.local/firmware/GoColor7_2/2026-04-21_13-54_4.2-rel_0421_19324b3ea/images/boot.img'
STOCK_HASH = 'ede53420966b3af1a3a7b02cae3fef8583a0e01d19271006287dc14b4457ba63'
POLICY = ROOT / '.local/stock-return-analysis/debug-ramdisk/policy-inputs'
AVB = ROOT / '.local/preinstall-tools/avbtool-android13.py'
DEBUG_RULES = b'''\n; Local authenticated ADB-root experiment, not a release policy.\n(allow adbd self (process (setcurrent)))\n(allow adbd su (process (dyntransition)))\n(typepermissive su)\n'''
DEBUG_PROPERTIES = b'ro.debuggable=1\nro.force.debuggable=1\nro.adb.secure=1\nro.secure=1\n'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def cpio_entries(data):
    entries = []
    position = 0
    while data[position:position + 6] == b'070701':
        start = position
        values = [int(data[position + 6 + n * 8:position + 14 + n * 8], 16) for n in range(13)]
        size, name_size = values[6], values[11]
        if not 0 < name_size < 4096:
            raise RuntimeError('Unexpected cpio name size')
        name = data[position + 110:position + 110 + name_size - 1].decode()
        content_start = (position + 110 + name_size + 3) // 4 * 4
        end = (content_start + size + 3) // 4 * 4
        if end > len(data):
            raise RuntimeError('Cpio entry outside ramdisk')
        entry = dict(name=name, values=values, start=start, end=end,
                     content=data[content_start:content_start + size])
        entries.append(entry)
        if name == 'TRAILER!!!':
            return entries, start
        position = end
    raise RuntimeError('Missing newc cpio trailer')


def new_file(name, content, inode):
    name = name.encode() + b'\0'
    fields = [inode, 0o100400, 0, 0, 1, 1776751543, len(content), 0, 0, 0, 0, len(name), 0]
    head = b'070701' + b''.join(f'{v:08x}'.encode() for v in fields) + name
    head += b'\0' * (-len(head) % 4)
    return head + content + b'\0' * (-len(content) % 4)


def main():
    os.umask(0o077)
    OUT.mkdir(parents=True, exist_ok=True)
    stock = STOCK.read_bytes()
    if sha(stock) != STOCK_HASH:
        raise RuntimeError('Exact stock boot hash changed')
    baseline = json.loads((ROOT / 'work/stock-policy-baseline-2026-11-11.json').read_text())
    for item in baseline['policy_inputs']:
        if sha((POLICY / item['path']).read_bytes()) != item['sha256']:
            raise RuntimeError('Saved policy input changed')
    platform = (POLICY / 'system/plat_sepolicy.cil').read_bytes()
    if b'(typepermissive ' in platform:
        raise RuntimeError('Unexpected permissive type in original platform CIL')
    debug_cil = platform + DEBUG_RULES
    (OUT / 'userdebug_plat_sepolicy.cil').write_bytes(debug_cil)
    docker = shutil.which('docker')
    context = json.loads(subprocess.run([docker, 'context', 'inspect'], check=True,
                                        capture_output=True, text=True, timeout=10).stdout)
    if not context[0]['Endpoints']['docker']['Host'].startswith('unix://'):
        raise RuntimeError('Local Docker context required')
    compiler_image = baseline['compiler_image']
    files = ['/candidate/userdebug_plat_sepolicy.cil'] + ['/inputs/' + x['path'] for x in baseline['policy_inputs'][1:]]
    base_command = [docker, 'run', '--rm', '--platform', 'linux/amd64', '--network', 'none',
                    '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--memory', '2g',
                    '--cpus', '2', '--mount', 'type=bind,src=' + str(POLICY) + ',dst=/inputs,readonly',
                    '--mount', 'type=bind,src=' + str(OUT) + ',dst=/candidate', compiler_image]
    args = ['secilc', files[0], '-m', '-M', 'true', '-G', '-N', '-c', '30', *files[1:],
            '-o', '/candidate/combined-debug.policy', '-f', '/dev/null']
    compiled = subprocess.run(base_command + args, capture_output=True, text=True, timeout=120)
    (OUT / 'policy-compile.log').write_text(compiled.stdout + compiled.stderr)
    if compiled.returncode:
        raise RuntimeError('Debug split policy did not compile')
    info = subprocess.run(base_command + ['seinfo', '--permissive', '-x', '/candidate/combined-debug.policy'],
                          check=True, capture_output=True, text=True, timeout=30).stdout
    (OUT / 'permissive-types.txt').write_text(info)
    lines = [line.strip() for line in info.splitlines() if line.strip()]
    if not lines or not re.fullmatch(r'Permissive Types:\s+1', lines[0]) or lines[1:] != ['type su, domain;']:
        raise RuntimeError('Expected only su to be permissive; inspect policy output')
    print('Local debug policy compiled; only su is permissive.', flush=True)

    page = struct.unpack_from('<I', stock, 36)[0]
    version = struct.unpack_from('<I', stock, 40)[0]
    ks, rs, ss = [struct.unpack_from('<I', stock, o)[0] for o in (8, 16, 24)]
    recovery_size, recovery_offset, header_size, ds, dtb_addr = struct.unpack_from('<IQIIQ', stock, 1632)
    if (page, version, ss, recovery_size, recovery_offset, header_size) != (4096, 2, 0, 0, 0, 1660):
        raise RuntimeError('Unexpected boot header geometry')
    aligned = lambda n: (n + page - 1) // page * page
    ro = page + aligned(ks)
    do = ro + aligned(rs)
    kernel = stock[page:page + ks]
    ramdisk = stock[ro:ro + rs]
    dtb = stock[do:do + ds]
    original_size = do + aligned(ds)

    def repack(ramdisk):
        header = bytearray(stock[:page])
        struct.pack_into('<I', header, 16, len(ramdisk))
        h = hashlib.sha1()
        for content in (kernel, ramdisk, b'', b'', dtb):
            h.update(content)
            h.update(struct.pack('<I', len(content)))
        header[576:608] = h.digest() + b'\0' * 12
        return bytes(header) + stock[page:ro] + ramdisk + b'\0' * (-len(ramdisk) % page) + dtb + b'\0' * (-len(dtb) % page)

    if repack(ramdisk) != stock[:original_size]:
        raise RuntimeError('Unmodified control repack is not byte-identical')
    raw = gzip.decompress(ramdisk)
    entries, trailer = cpio_entries(raw)
    additions = {'force_debuggable': b'', 'adb_debug.prop': DEBUG_PROPERTIES,
                 'userdebug_plat_sepolicy.cil': debug_cil}
    if {x['name'].removeprefix('./') for x in entries} & additions.keys():
        raise RuntimeError('Debug files already exist in original ramdisk')
    inode = max(x['values'][0] for x in entries) + 1
    added = b''.join(new_file(name, content, inode + i) for i, (name, content) in enumerate(additions.items()))
    modified_raw = raw[:trailer] + added + raw[trailer:]
    new_entries, _ = cpio_entries(modified_raw)
    old_by_name = {x['name']: x for x in entries}
    new_by_name = {x['name']: x for x in new_entries}
    for name, entry in old_by_name.items():
        if entry['values'] != new_by_name[name]['values'] or entry['content'] != new_by_name[name]['content']:
            raise RuntimeError('An original ramdisk entry changed')
    modified_ramdisk = gzip.compress(modified_raw, compresslevel=9, mtime=0)
    payload = repack(modified_ramdisk)
    # avbtool resolves the embedded partition descriptor as sibling boot.img.
    image = OUT / 'boot.img'
    if image.exists():
        raise RuntimeError('Prior candidate exists; inspect rather than overwrite')
    image.write_bytes(payload)
    fingerprint = 'Onyx/GoColor7_2/GoColor7_2:11/2026-04-21_13-54_4.2-rel_0421_19324b3ea/8525:user/release-keys'
    command = [sys.executable, str(AVB), 'add_hash_footer', '--image', str(image), '--partition_name', 'boot',
               '--partition_size', str(len(stock)), '--algorithm', 'NONE',
               '--salt', '8724154b78a699245cf5733bf3386c7016cb9e619f8e25688df5e2e260dd92aa',
               '--prop', 'com.android.build.boot.fingerprint:' + fingerprint,
               '--prop', 'com.android.build.boot.os_version:11',
               '--prop', 'com.android.build.boot.security_patch:2025-10-01',
               '--prop', 'com.android.build.boot.security_patch:2025-10-01']
    subprocess.run(command, check=True, capture_output=True, text=True, timeout=30)
    verify = subprocess.run([sys.executable, str(AVB), 'verify_image', '--image', str(image)],
                            check=True, capture_output=True, text=True, timeout=30)
    (OUT / 'avb-internal-check.txt').write_text(verify.stdout + verify.stderr)
    candidate = image.read_bytes()
    new_rs = struct.unpack_from('<I', candidate, 16)[0]
    new_do = ro + aligned(new_rs)
    if candidate[page:page + ks] != kernel or candidate[new_do:new_do + ds] != dtb:
        raise RuntimeError('Kernel or DTB changed')
    report = {'status': 'OFFLINE EXPERIMENT ONLY — NOT FLASH AUTHORIZATION',
              'artifact': str(image), 'artifact_bytes': len(candidate), 'artifact_sha256': sha(candidate),
              'original_stock_sha256': STOCK_HASH, 'unmodified_control_repack_byte_identical': True,
              'original_ramdisk_entries_preserved': len(entries), 'added_ramdisk_files': list(additions),
              'kernel_unchanged': True, 'dtb_unchanged': True, 'external_dtbo_not_modified': True,
              'header_addresses_and_cmdline_preserved': True, 'internal_avb_footer_hash_verified': True,
              'manufacturer_parent_vbmeta_boot_hash_matches': False,
              'debug_policy_compiled_with_stock_init_flags': True,
              'permissive_domain': 'su only; global enforcing setting unchanged',
              'adb_authentication_required': True, 'root_default': 'privileges dropped until explicit authenticated adb root',
              'additional_root_capability_is_read_only': False,
              'new_software_installed_or_booted_on_reader': False, 'device_access_performed': False,
              'runtime_or_modified_image_acceptance_tested': False, 'lineage_image': False,
              'future_write_scope_for_review': 'boot_a only, followed by restoring exact stock boot_a; never automatic',
              'remaining_risks': ['unlocked OEM bootloader acceptance of modified image untested',
                                  'debug property and root-domain runtime untested',
                                  'failed boot could need native fastboot restoration and A-slot repair',
                                  'su can write raw storage; any trial needs a strict command scope and authentication',
                                  'manufacturer parent hash differs; do not disable verification or modify vbmeta as a fallback']}
    (OUT / 'candidate-report.json').write_text(json.dumps(report, indent=2) + '\n')
    (ROOT / 'work/stock-debug-boot-offline-candidate-2026-11-11.json').write_text(json.dumps(report, indent=2) + '\n')
    image.chmod(0o400)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
