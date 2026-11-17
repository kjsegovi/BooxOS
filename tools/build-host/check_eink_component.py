#!/usr/bin/env python3
"""Test the local legacy-compiler adaptation; never access the BOOX.

Run only pinned compiler/libc/NDK inputs in a network-isolated Linux container.
An Android shared library is not a packaged or hardware-qualified OS image.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time
import tomllib

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = r'''set -eu
cp -a /component /tmp/eink-shim
cd /tmp/eink-shim
printf '\n[patch.crates-io]\nlibc = { path = "/dependency" }\n' >> Cargo.toml
export PATH=/work/prebuilts/rust/linux-x86/1.75.0/bin:$PATH
export CARGO_HOME=/tmp/cargo
export CARGO_TARGET_DIR=/tmp/eink-target
export CARGO_NET_OFFLINE=true
cargo test --offline
cargo check --offline --release --target aarch64-linux-android
cat > /tmp/android-linker <<'LINKER'
#!/bin/sh
exec /work/prebuilts/clang/host/linux-x86/clang-r510928/bin/clang --target=aarch64-linux-android30 --sysroot=/ndk -fuse-ld=lld "$@"
LINKER
chmod 700 /tmp/android-linker
export CARGO_TARGET_AARCH64_LINUX_ANDROID_LINKER=/tmp/android-linker
export RUSTFLAGS='-C link-arg=-Wl,--no-undefined -C link-arg=-Wl,-soname,libeink_shim.so'
cargo build --offline --release --target aarch64-linux-android
cp /tmp/eink-target/aarch64-linux-android/release/libeink_shim.so /output/libeink_shim.so
readelf -h -d -Ws /output/libeink_shim.so > /output/elf-inspection.txt
echo ANDROID_SHARED_LIBRARY_LINKED
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--color-panel', action='store_true')
    opts = parser.parse_args()
    docker = shutil.which('docker')
    context = json.loads(subprocess.run([docker, 'context', 'inspect'], capture_output=True,
                                        text=True, check=True, timeout=10).stdout)
    if not context[0]['Endpoints']['docker']['Host'].startswith('unix://'):
        raise SystemExit('Local Docker context required')
    init = json.loads((ROOT / 'work/lineage21-source-init-2026-11-11.json').read_text())
    lock = tomllib.loads((ROOT / 'components/eink-shim/Cargo.lock').read_text())
    expected = next(p['checksum'] for p in lock['package'] if p['name'] == 'libc')
    crate = ROOT / '.local/component-tests/cargo-home/registry/cache/index.crates.io-1949cf8c6b5b557f/libc-0.2.161.crate'
    if hashlib.sha256(crate.read_bytes()).hexdigest() != expected:
        raise SystemExit('Pinned dependency archive changed')
    source = ROOT / '.local/component-tests/verified-dependency/libc-0.2.161'
    ndk = ROOT / '.local/ndk-link-inputs'
    manifest = json.loads((ndk / 'source-manifest.json').read_text())
    if not manifest['published_sha1_matches']:
        raise SystemExit('Verified NDK archive required')
    for entry in manifest['selected_files']:
        if hashlib.sha256((ndk / 'sysroot' / entry['path']).read_bytes()).hexdigest() != entry['sha256']:
            raise SystemExit('NDK link input changed')
    output_dir = ROOT / '.local/component-builds' / ('lineage21-color' if opts.color_panel else 'lineage21')
    output_dir.mkdir(parents=True, exist_ok=True)
    command = [docker, 'run', '--rm', '--name', 'booxos-eink-rust175-check-20261111',
               '--platform', 'linux/amd64', '--network', 'none', '--cap-drop', 'ALL',
               '--security-opt', 'no-new-privileges', '--memory', '4g', '--cpus', '4',
               '--pids-limit', '256', '--mount',
               'type=volume,src=booxos-lineage21-source-20261111,dst=/work,readonly',
               '--mount', 'type=bind,src=' + str(ROOT / 'components/eink-shim') + ',dst=/component,readonly',
               '--mount', 'type=bind,src=' + str(source) + ',dst=/dependency,readonly',
               '--mount', 'type=bind,src=' + str(ndk / 'sysroot') + ',dst=/ndk,readonly',
               '--mount', 'type=bind,src=' + str(output_dir) + ',dst=/output',
               init['image'], '/bin/bash', '-c',
               SCRIPT.replace('cargo test --offline', 'cargo test --offline --features color-panel')
               .replace('cargo check --offline', 'cargo check --offline --features color-panel')
               .replace('cargo build --offline', 'cargo build --offline --features color-panel')
               if opts.color_panel else SCRIPT]
    began = time.monotonic()
    process = subprocess.run(command, capture_output=True, text=True, timeout=240)
    output = process.stdout + process.stderr
    (ROOT / '.local/component-tests/rust175-check.log').write_text(output)
    report = {'compiler': 'Lineage21 Android Rust 1.75.0', 'exit_code': process.returncode,
              'passed': process.returncode == 0, 'elapsed_seconds': round(time.monotonic() - began, 2),
              'output': output[-12000:], 'android_shared_library_linked':
                  process.returncode == 0 and 'ANDROID_SHARED_LIBRARY_LINKED' in output,
              'color_hardware_validated': False, 'color_profile_enabled': opts.color_panel,
              'device_access': False, 'source_sha256': {
                  str(p.relative_to(ROOT / 'components/eink-shim')): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in (ROOT / 'components/eink-shim/src').glob('*.rs')}}
    if report['android_shared_library_linked']:
        artifact = output_dir / 'libeink_shim.so'
        report['android_library'] = {'path': str(artifact), 'bytes': artifact.stat().st_size,
                                     'sha256': hashlib.sha256(artifact.read_bytes()).hexdigest(),
                                     'target_api': 30, 'architecture': 'aarch64',
                                     'ndk_archive_sha256': manifest['archive_sha256']}
    report_name = 'eink-color-component-build-2026-11-11.json' if opts.color_panel else 'eink-rust175-compatibility-2026-11-11.json'
    (ROOT / 'work' / report_name).write_text(json.dumps(report, indent=2) + '\n')
    print(output[-6000:])
    print(json.dumps({k: v for k, v in report.items() if k not in ['output', 'source_sha256']}))
    raise SystemExit(process.returncode)


if __name__ == '__main__':
    main()
