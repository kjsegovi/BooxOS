#!/usr/bin/env python3
"""Exercise checked-out Android 14 host tools, without building or accessing BOOX.

The source volume is mounted read-only. All compile/test outputs live in the
disposable container's Linux filesystem. This is not a full Android build.
"""
import json
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
VOLUME = 'booxos-lineage21-source-20261111'

SCRIPT = r'''
import json, os, pathlib, subprocess, time
root=pathlib.Path('/work')
out=pathlib.Path('/tmp/boox-tool-probe'); out.mkdir()
os.environ.update(GOMAXPROCS='2', GOCACHE=str(out/'go-cache'), GOWORK='off', GOPROXY='off')
clang=root/'prebuilts/clang/host/linux-x86/clang-r510928/bin/clang'
go=root/'prebuilts/go/linux-x86/bin/go'
ninja=root/'prebuilts/build-tools/linux-x86/bin/ninja'
java=root/'prebuilts/jdk/jdk17/linux-x86/bin/java'
rust=root/'prebuilts/rust/linux-x86/1.75.0/bin/rustc'
checks=[]
def run(name,args,cwd=out,timeout=180):
    started=time.monotonic()
    try:
        p=subprocess.run([str(x) for x in args],cwd=cwd,capture_output=True,text=True,timeout=timeout)
        r=dict(name=name,exit_code=p.returncode,passed=p.returncode==0,elapsed_seconds=round(time.monotonic()-started,2),output=(p.stdout+p.stderr)[-5000:])
    except (OSError,subprocess.TimeoutExpired) as exc:
        r=dict(name=name,passed=False,error=str(exc),elapsed_seconds=round(time.monotonic()-started,2))
    checks.append(r); print(json.dumps(r),flush=True)
    return r['passed']
for name,path,arg in [('go_version',go,'version'),('clang_version',clang,'--version'),('ninja_version',ninja,'--version'),('java_version',java,'-version'),('rust_version',rust,'--version')]:
    run(name,[path,arg],timeout=30)
run('blueprint_build_library_tests',[go,'test','./pathtools','./parser','./proptools'],root/'build/blueprint',timeout=240)
(out/'probe.c').write_text('unsigned int boox_probe_sum(unsigned int n) { return n * (n + 1) / 2; }\n')
(out/'host.c').write_text('#include <stdio.h>\nunsigned int boox_probe_sum(unsigned int);\nint main(void) { unsigned int n=boox_probe_sum(100); printf("%u\\n",n); return n==5050 ? 0 : 1; }\n')
if run('clang_host_link',[clang,'host.c','probe.c','-o','host-probe']):
    run('clang_host_execution',[out/'host-probe'])
run('android_arm64_shared_library',[clang,'--target=aarch64-linux-android30','-ffreestanding','-nostdlib','-shared','-fPIC','-fuse-ld=lld','-Wl,-soname,libboox_tool_probe.so','probe.c','-o','libboox_tool_probe.so'])
run('android_arm64_elf_headers',['readelf','-h','-d',out/'libboox_tool_probe.so'])
(out/'Hello.java').write_text('class Hello { public static void main(String[] args) { System.out.println("BOOX JDK probe"); } }\n')
if run('java_compile',[java.parent/'javac','Hello.java']):
    run('java_execution',[java,'-cp',out,'Hello'])
if rust.exists():
    (out/'probe.rs').write_text('fn main() { assert_eq!((1..=100).sum::<u32>(),5050); println!("5050"); }\n')
    if run('rust_compile',[rust,'probe.rs','-o','rust-probe']):
        run('rust_execution',[out/'rust-probe'])
result=dict(checks=checks,all_passed=all(x['passed'] for x in checks),source_read_only=True,network=False,full_android_build=False,boox_access=False)
print('FINAL_RESULT='+json.dumps(result),flush=True)
'''


def main():
    init = json.loads((ROOT / 'work/lineage21-source-init-2026-11-11.json').read_text())
    docker = shutil.which('docker')
    context = subprocess.run([docker, 'context', 'inspect'], capture_output=True,
                             text=True, check=True, timeout=10)
    if not json.loads(context.stdout)[0]['Endpoints']['docker']['Host'].startswith('unix://'):
        raise SystemExit('Only the local Docker context is allowed')
    command = [docker, 'run', '--rm', '--name', 'booxos-lineage21-tools-probe-20261111',
               '--platform', 'linux/amd64', '--network', 'none', '--cap-drop', 'ALL',
               '--security-opt', 'no-new-privileges', '--memory', '6g', '--cpus', '4',
               '--pids-limit', '512', '--mount', 'type=volume,src=' + VOLUME + ',dst=/work,readonly',
               init['image'], 'python3', '-u', '-c', SCRIPT]
    began = time.monotonic()
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, stdin=subprocess.DEVNULL)
    lines = []
    for line in process.stdout:
        lines.append(line)
        print(line, end='', flush=True)
    process.wait()
    report = {'container_exit_code': process.returncode,
              'elapsed_seconds': round(time.monotonic() - began, 2), 'image': init['image'],
              'volume': VOLUME, 'full_android_build': False, 'boox_access': False,
              'docker_settings_changed': False, 'all_passed': False}
    for line in lines:
        if line.startswith('FINAL_RESULT='):
            report.update(json.loads(line.split('=', 1)[1]))
    if not report['all_passed']:
        report['failure_tail'] = ''.join(lines)[-6000:]
    path = ROOT / 'work/lineage21-actual-tool-probe-2026-11-11.json'
    path.write_text(json.dumps(report, indent=2) + '\n')
    raise SystemExit(0 if report['all_passed'] else 1)


if __name__ == '__main__':
    main()
