#!/usr/bin/env python3
"""Copy reviewed color target and verified inputs into its Linux build volume.

No device connection. Local key stays in this private local build workspace;
no credentials, private images or keys are uploaded to a repository.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        while chunk := f.read(4 * 1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def main():
    docker = shutil.which('docker')
    context = json.loads(subprocess.run([docker,'context','inspect'],capture_output=True,text=True,check=True,timeout=10).stdout)
    if not context[0]['Endpoints']['docker']['Host'].startswith('unix://'):
        raise RuntimeError('Local Docker context required')
    vendor = json.loads((ROOT/'work/vendor-derivative-build-2026-11-11.json').read_text())
    comparison = json.loads((ROOT/'work/vendor-full-inventory-comparison-2026-11-11.json').read_text())
    if not vendor['complete_vendor_inventory_comparison_passed'] or not comparison['passed']:
        raise RuntimeError('Complete vendor file comparison required')
    stock = json.loads((ROOT/'work/stock-firmware-validation-2026-11-11.json').read_text())
    base = Path(stock['archive_path']).parent/'images'
    sources = {name:base/(name+'.img') for name in ['boot','dtbo','odm']}
    hashes = {p['name']:p['expected_sha256'] for p in stock['payload']['partitions']}
    for name,path in sources.items():
        if sha(path)!=hashes[name]:raise RuntimeError('Matched stock input changed: '+name)
    if sha(ROOT/'.local/vendor-derivative/vendor.img')!=vendor['derivative_vendor_sha256']:
        raise RuntimeError('Vendor derivative changed')
    key = ROOT/'.private/build-signing/avb-development-key.pem'
    if key.stat().st_mode & 0o077:raise RuntimeError('Development key permissions are too broad')
    image = json.loads((ROOT/'work/lineage21-source-init-2026-11-11.json').read_text())['image']
    script = r'''set -eu
target=/work/device/onyx/GoColor7_2
mkdir -p "$target/prebuilts"
cp /config/AndroidProducts.mk /config/BoardConfig.mk /config/lineage_GoColor7_2.mk /config/README.md /config/.gitignore "$target/"
cp /stock/boot.img /stock/dtbo.img /stock/odm.img "$target/prebuilts/"
cp /derivative/vendor.img "$target/prebuilts/vendor.img"
cp /signing/avb-development-key.pem "$target/prebuilts/avb-development-key.pem"
chmod 600 "$target/prebuilts/avb-development-key.pem"
sha256sum "$target/prebuilts/boot.img" "$target/prebuilts/dtbo.img" "$target/prebuilts/odm.img" "$target/prebuilts/vendor.img"
'''
    args=[docker,'run','--rm','--platform','linux/amd64','--network','none','--cap-drop','ALL','--security-opt','no-new-privileges','--memory','1g','--mount','type=volume,src=booxos-lineage21-source-20261111,dst=/work','--mount','type=bind,src='+str(ROOT/'device/onyx/GoColor7_2')+',dst=/config,readonly','--mount','type=bind,src='+str(base)+',dst=/stock,readonly','--mount','type=bind,src='+str(ROOT/'.local/vendor-derivative')+',dst=/derivative,readonly','--mount','type=bind,src='+str(key.parent)+',dst=/signing,readonly',image,'/bin/bash','-c',script]
    p=subprocess.run(args,capture_output=True,text=True,check=True,timeout=120)
    actual={Path(line.split()[1]).stem:line.split()[0] for line in p.stdout.splitlines()}
    expected={name:hashes[name] for name in sources};expected['vendor']=vendor['derivative_vendor_sha256']
    if actual!=expected:raise RuntimeError('Provisioned Linux input hash mismatch')
    report={'target':'lineage_GoColor7_2-ap2a-userdebug','source_volume':'booxos-lineage21-source-20261111','images':actual,'source_files':{p.name:sha(p) for p in (ROOT/'device/onyx/GoColor7_2').iterdir() if p.is_file()},'key_copied_only_to_local_private_linux_volume':True,'boox_access':False,'image_built':False,'install_ready':False}
    (ROOT/'work/color-target-provisioned-2026-11-11.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
