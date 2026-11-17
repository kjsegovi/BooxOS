#!/usr/bin/env python3
"""Read-only, offline screening for a modern AOSP/LineageOS build host.

Usage: python3 preflight.py /existing/build/directory --mode experimental
Prints JSON to stdout. Does not install, download, create files, start services,
connect to a device, inspect credentials, or initialize an Android checkout.
Passing is a host screening result, not proof that a device port builds.
"""

import argparse
import datetime
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys


def read_text(path):
    try:
        return Path(path).read_text().strip()
    except (OSError, UnicodeError):
        return None


def memory_bytes():
    values = {}
    for line in (read_text('/proc/meminfo') or '').splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0] in ('MemTotal:', 'MemAvailable:', 'SwapTotal:'):
            values[parts[0].rstrip(':')] = int(parts[1]) * 1024
    # Container memory ceilings can be smaller than /proc/meminfo reports.
    limits = []
    candidates = {
        Path('/sys/fs/cgroup/memory.max'),
        Path('/sys/fs/cgroup/memory/memory.limit_in_bytes'),
    }
    for line in (read_text('/proc/self/cgroup') or '').splitlines():
        hierarchy, _, rel = line.partition(':')
        controllers, _, rel = rel.partition(':')
        if hierarchy == '0' and not controllers:
            base = Path('/sys/fs/cgroup')
            current = base / rel.lstrip('/')
            if current == base or base in current.parents:
                candidates.update(p / 'memory.max' for p in [current, *current.parents]
                                  if p == base or base in p.parents)
    for path in candidates:
        value = read_text(path)
        if value and value.isdigit() and 0 < int(value) < 2**60:
            limits.append(int(value))
    total = values.get('MemTotal')
    effective = min([total, *limits]) if total else None
    return {'physical_or_guest_total_bytes': total,
            'available_bytes': values.get('MemAvailable'),
            'swap_bytes': values.get('SwapTotal'),
            'cgroup_limit_bytes': min(limits) if limits else None,
            'effective_ceiling_bytes': effective}


def case_probe(directory):
    # Use existing entries only: an empty directory produces an honest unknown.
    try:
        for index, entry in enumerate(directory.iterdir()):
            if index >= 128:
                break
            alternate_name = entry.name.swapcase()
            if alternate_name == entry.name or not any(c.isascii() and c.isalpha() for c in entry.name):
                continue
            alternate = directory / alternate_name
            try:
                original_stat = entry.stat(follow_symlinks=False)
                try:
                    alternate_stat = alternate.stat(follow_symlinks=False)
                except FileNotFoundError:
                    return True
                if os.path.samestat(original_stat, alternate_stat):
                    return False
                return True
            except OSError:
                continue
    except OSError:
        pass
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path, help='Existing intended build directory; no directory is created.')
    parser.add_argument('--mode', choices=['documented', 'experimental'], default='documented',
                        help='Experimental permits a Linux ARM/x86 toolchain probe despite full-build resource shortfalls.')
    args = parser.parse_args()
    directory = args.directory.resolve()
    if not directory.is_dir():
        parser.error('The build directory must already exist.')
    system, arch = platform.system(), platform.machine()
    mem = memory_bytes() if system == 'Linux' else {}
    free = shutil.disk_usage(directory).free
    libc = None
    if system == 'Linux':
        try:
            libc = os.confstr('CS_GNU_LIBC_VERSION')
        except (OSError, ValueError):
            pass
    libc_parts = libc.split()[-1].split('.') if libc else []
    glibc_ok = bool(libc and libc.startswith('glibc ') and
                    tuple(int(x) for x in libc_parts[:2]) >= (2, 17))
    case_sensitive = case_probe(directory)
    commands = ['git', 'git-lfs', 'python3', 'curl', 'gcc', 'g++', 'make',
                'bison', 'flex', 'bc', 'gperf', 'zip', 'unzip', 'rsync',
                'ccache', 'protoc', 'repo']
    tools = {name: shutil.which(name) is not None for name in commands}
    checks = {
        'linux': system == 'Linux',
        'documented_x86_64_host_architecture': arch in ('x86_64', 'amd64'),
        'glibc_at_least_2_17': glibc_ok,
        'ram_at_least_64_decimal_gb': (mem.get('effective_ceiling_bytes') or 0) >= 64_000_000_000,
        'free_space_at_least_400_decimal_gb': free >= 400_000_000_000,
        'case_sensitive_workspace': case_sensitive,
        'screened_commands_present': all(tools.values()),
    }
    filesystem = None
    if system == 'Linux' and shutil.which('findmnt'):
        result = subprocess.run(['findmnt', '-T', str(directory), '-n', '-o', 'FSTYPE'],
                                capture_output=True, text=True, timeout=10, check=False)
        if result.returncode == 0:
            filesystem = result.stdout.strip()
    wsl = system == 'Linux' and 'microsoft' in platform.release().lower()
    warnings = [
        'Command presence does not verify all required distribution development packages or versions.',
        'A passing host screen does not validate the BOOX device tree, blobs, kernel, signing, or installability.',
        'Swap is reported but does not replace the documented RAM baseline.',
    ]
    if case_sensitive is None:
        warnings.append('Case sensitivity is unverified: no usable existing entry was found in the build directory.')
    if wsl:
        warnings.append('WSL detected: also check Windows physical free space behind the virtual disk and Linux guest RAM allocation.')
    if filesystem in ('9p', 'drvfs', 'virtiofs', 'fuse.osxfs'):
        warnings.append('Shared filesystem detected: use guest-native Linux storage for the source and output tree.')
    documented_passed = all(value is True for value in checks.values())
    experimental_candidate = (system == 'Linux' and glibc_ok and
                              arch in ('x86_64', 'amd64', 'aarch64', 'arm64'))
    if args.mode == 'experimental':
        warnings.append('Experimental mode permits only bounded toolchain investigation; resource shortfalls remain visible and no full build is certified.')
    report = {
        'schema_version': 1,
        'checked_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'scope': 'read_only_offline_host_screen', 'mode': args.mode,
        'system': system, 'architecture': arch, 'glibc': libc, 'wsl_detected': wsl,
        'memory': mem, 'workspace_free_bytes': free,
        'workspace_filesystem': filesystem, 'workspace_case_sensitive': case_sensitive,
        'commands_present': tools, 'checks': checks,
        'documented_baseline_screen_passed': documented_passed,
        'platform_allows_experimental_toolchain_probe': experimental_candidate,
        'selected_screen_passed': documented_passed if args.mode == 'documented' else experimental_candidate,
        'warnings': warnings,
        'requirements_sources': [
            'https://source.android.com/docs/setup/start/requirements',
            'https://github.com/LineageOS/lineage_wiki/blob/main/_includes/templates/device_build_before_init.md',
        ],
    }
    print(json.dumps(report, indent=2))
    return 0 if report['selected_screen_passed'] else 2


if __name__ == '__main__':
    sys.exit(main())
