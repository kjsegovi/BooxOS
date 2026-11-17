#!/usr/bin/env python3
"""Materialize pinned Rust Soong definitions omitted by compiler-only sparse setup."""
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = r'''
import hashlib,json,pathlib,subprocess
repo=pathlib.Path('/work/prebuilts/rust')
def git(args,**kwargs):return subprocess.run(['git','-C',str(repo)]+args,check=True,text=True,**kwargs)
expected='4ebcd0d4c717e312c2773f4019e0874b994ac2b8'
if git(['rev-parse','HEAD'],capture_output=True).stdout.strip()!=expected:raise RuntimeError('Pinned Rust revision changed')
tree=git(['ls-tree','-r','HEAD','soong'],capture_output=True).stdout
objects=sorted({line.split()[2] for line in tree.splitlines() if line.split()[1]=='blob'})
if len(objects)!=3:raise RuntimeError('Unexpected support-file tree')
git(['fetch','--no-tags','--no-write-fetch-head','--recurse-submodules=no','--filter=blob:none','aosp','--stdin'],input='\n'.join(objects)+'\n')
git(['sparse-checkout','set','linux-x86/1.75.0','soong'])
files={str(p.relative_to(repo)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (repo/'soong').iterdir() if p.is_file()}
if 'soong/rustprebuilts.go' not in files:raise RuntimeError('Rust build plugin still absent')
print('RESULT='+json.dumps(dict(revision=expected,files=files,sparse_paths=['linux-x86/1.75.0','soong'],device_access=False)))
'''


def main():
    docker=shutil.which('docker')
    context=json.loads(subprocess.run([docker,'context','inspect'],capture_output=True,text=True,check=True,timeout=10).stdout)
    if not context[0]['Endpoints']['docker']['Host'].startswith('unix://'):raise RuntimeError('Local Docker context required')
    image=json.loads((ROOT/'work/lineage21-source-init-2026-11-11.json').read_text())['image']
    p=subprocess.run([docker,'run','--rm','--platform','linux/amd64','--cap-drop','ALL','--security-opt','no-new-privileges','--memory','1g','--mount','type=volume,src=booxos-lineage21-source-20261111,dst=/work',image,'python3','-u','-c',SCRIPT],capture_output=True,text=True,timeout=120)
    if p.returncode:print(p.stdout+p.stderr);raise SystemExit(p.returncode)
    result=next(json.loads(x.split('=',1)[1]) for x in p.stdout.splitlines() if x.startswith('RESULT='))
    (ROOT/'work/rust-soong-support-restored-2026-11-11.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
