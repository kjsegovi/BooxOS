#!/usr/bin/env python3
"""Finish only the selected Rust 1.75 Linux checkout after the broad sync stops.

Batch-fetch missing selected blobs instead of per-file lazy fetches. Leave other
host versions unmaterialized; this remains a host qualification, not full sync.
"""
import json
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
NAME = 'booxos-lineage21-rust-subset-20261111'
VOLUME = 'booxos-lineage21-source-20261111'
MIN_FREE = 100 * 1024**3

SCRIPT = r'''
import hashlib,json,pathlib,subprocess,time
repo=pathlib.Path('/work/prebuilts/rust')
def git(args,**kw):
    return subprocess.run(['git','-C',str(repo)]+args,check=True,text=True,**kw)
selected='linux-x86/1.75.0'
commit=git(['rev-parse','HEAD'],capture_output=True).stdout.strip()
tree=git(['ls-tree','-r','HEAD',selected],capture_output=True).stdout
ids=sorted(set(line.split()[2] for line in tree.splitlines() if line.split()[1]=='blob'))
if len(ids)<100: raise SystemExit('Expected the full selected compiler tree')
print(json.dumps(dict(stage='batch_fetch_rust_1_75_linux',commit=commit,selected_blobs=len(ids))),flush=True)
git(['-c','pack.threads=2','fetch','--no-tags','--no-write-fetch-head','--recurse-submodules=no','--filter=blob:none','aosp','--stdin'],input='\n'.join(ids)+'\n')
print('Selected Rust blobs fetched; enabling sparse checkout.',flush=True)
lock=pathlib.Path(git(['rev-parse','--git-path','index.lock'],capture_output=True).stdout.strip())
if not lock.is_absolute(): lock=repo/lock
if lock.exists():
    if lock.stat().st_size>1024*1024: raise SystemExit('Unexpected index lock size; inspect before removing')
    print('Removing only the interrupted checkout index lock from this isolated Rust repository.',flush=True)
    lock.unlink()
git(['sparse-checkout','init','--cone'])
git(['sparse-checkout','set',selected,'soong'])
git(['read-tree','--reset','-u','HEAD'])
rust=repo/selected/'bin/rustc'
subprocess.run([str(rust),'--version'],check=True)
paths=['build/blueprint','build/make','build/soong','prebuilts/build-tools','prebuilts/go/linux-x86','prebuilts/clang/host/linux-x86','prebuilts/rust','prebuilts/jdk/jdk17']
pins={p:subprocess.run(['git','-C','/work/'+p,'rev-parse','HEAD'],check=True,capture_output=True,text=True).stdout.strip() for p in paths}
print('FINAL_RESULT='+json.dumps(dict(passed=True,pins=pins,rust_sparse_path=selected,full_platform_sync=False,boox_access=False)),flush=True)
'''


def main():
    init = json.loads((ROOT/'work/lineage21-source-init-2026-11-11.json').read_text())
    docker = shutil.which('docker')
    context = json.loads(subprocess.run([docker,'context','inspect'],check=True,capture_output=True,text=True,timeout=10).stdout)
    if not context[0]['Endpoints']['docker']['Host'].startswith('unix://'):
        raise SystemExit('Local Docker context required')
    if shutil.disk_usage(ROOT).free < MIN_FREE:
        raise SystemExit('Physical Mac disk floor reached')
    cmd=[docker,'run','--rm','--name',NAME,'--platform','linux/amd64','--cap-drop','ALL',
         '--security-opt','no-new-privileges','--memory','6g','--cpus','4','--pids-limit','512',
         '--mount','type=volume,src='+VOLUME+',dst=/work',init['image'],'python3','-u','-c',SCRIPT]
    log=ROOT/'.local/mac-build-probe/lineage21-rust-subset.log'
    result=dict(passed=False,volume=VOLUME,image=init['image'],boox_access=False,full_platform_sync=False)
    with log.open('w') as stream:
        p=subprocess.Popen(cmd,stdout=stream,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL)
        began,last=time.monotonic(),0
        while p.poll() is None:
            free=shutil.disk_usage(ROOT).free
            if free<MIN_FREE or time.monotonic()-began>1200:
                subprocess.run([docker,'stop','--timeout','10',NAME],capture_output=True,timeout=20)
                result['stop_reason']='Physical disk floor or 20-minute subset deadline'
                break
            if time.monotonic()-last>25:
                lines=log.read_text(errors='replace').splitlines()
                print(json.dumps(dict(elapsed_seconds=round(time.monotonic()-began),physical_host_free_GB=round(free/10**9,2),stage=lines[-1][-180:] if lines else 'starting')),flush=True)
                last=time.monotonic()
            time.sleep(2)
        p.wait(timeout=30)
    for line in log.read_text(errors='replace').splitlines():
        if line.startswith('FINAL_RESULT='):
            result.update(json.loads(line.split('=',1)[1]))
    result.update(exit_code=p.returncode,elapsed_seconds=round(time.monotonic()-began,2),physical_host_free_bytes_after=shutil.disk_usage(ROOT).free)
    if not result['passed']:
        result['failure_tail']=log.read_text(errors='replace')[-4000:]
    (ROOT/'work/lineage21-toolchain-subset-final-2026-11-11.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2),flush=True)
    raise SystemExit(0 if result['passed'] else 1)


if __name__=='__main__':
    main()
