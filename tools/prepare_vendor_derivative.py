#!/usr/bin/env python3
"""Prepare a local vendor derivative for the experimental exact-model build.

Never uses ADB/fastboot or mounts a device filesystem. Patches copied files in
a copied ext4 image, retains permissions/labels, and validates changes offline.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.local/vendor-derivative'
STOCK = ROOT / '.local/firmware/GoColor7_2/2026-04-21_13-54_4.2-rel_0421_19324b3ea/images/vendor.img'
STOCK_HASH = '147fe58efadd4e444b1236704e3880f1da3bcee08d4016d839b7d4630f1c3372'
AVB = ROOT / '.local/preinstall-tools/avbtool-android13.py'

SCRIPT = r'''
import hashlib,json,pathlib,re,subprocess
out=pathlib.Path('/output'); image=out/'vendor.img'
composer='/bin/hw/vendor.qti.hardware.display.composer-service'
def run(args):
    p=subprocess.run(args,capture_output=True,text=True,timeout=120)
    if p.returncode: raise RuntimeError('Tool failed: '+str(args)+': '+(p.stdout+p.stderr)[-3000:])
    return p.stdout+p.stderr
def debug(command,write=False):
    text=run(['debugfs']+(['-w'] if write else [])+['-R',command,str(image)])
    for failure in ['File not found','Command not found','Usage:','No free space','Could not allocate']:
        if failure in text: raise RuntimeError(text)
    return text
def capture(path,name):
    stat=debug('stat '+path)
    mode=re.search(r'Mode:\s+0*([0-7]+)',stat).group(1)
    ids=re.search(r'User:\s+(\d+)\s+Group:\s+(\d+)',stat)
    if not re.search(r'Links:\s+1\b',stat): raise RuntimeError('Unexpected hardlink count')
    label=out/(name+'.selinux')
    debug('ea_get -f '+str(label)+' '+path+' security.selinux')
    if not label.is_file() or not label.read_bytes().startswith(b'u:object_r:'): raise RuntimeError('Missing original security label')
    target=out/name
    debug('dump '+path+' '+str(target))
    return dict(path=path,mode=int(mode,8)|0o100000,uid=int(ids[1]),gid=int(ids[2]),label=str(label),file=str(target),stat=stat)
def replace(meta):
    debug('rm '+meta['path'],True)
    debug('write '+meta['file']+' '+meta['path'],True)
    for field,value in [('mode',meta['mode']),('uid',meta['uid']),('gid',meta['gid']),('atime','20090101000000'),('mtime','20090101000000'),('ctime','20090101000000'),('crtime','20090101000000'),('atime_extra',0),('mtime_extra',0),('ctime_extra',0),('crtime_extra',0)]:
        debug('set_inode_field '+meta['path']+' '+field+' '+str(value),True)
    debug('ea_set -f '+meta['label']+' '+meta['path']+' security.selinux',True)

original=capture(composer,'composer')
before=pathlib.Path(original['file']).read_bytes()
run(['patchelf','--add-needed','libeink_shim.so',original['file']])
needed=run(['readelf','-d',original['file']])
libraries=re.findall(r'\(NEEDED\).*?\[(.*?)\]',needed)
if not libraries or libraries[0]!='libeink_shim.so' or libraries.count('libeink_shim.so')!=1:raise RuntimeError('Shim is not the first composer dependency')
replace(original)

libmeta=capture('/lib64/libdrm.so','reference-libdrm')
newlib=out/'libeink_shim.so';newlib.write_bytes(pathlib.Path('/component/libeink_shim.so').read_bytes())
meta=dict(path='/lib64/libeink_shim.so',file=str(newlib),mode=0o100644,uid=0,gid=0,label=libmeta['label'])
debug('write '+meta['file']+' '+meta['path'],True)
for field,value in [('mode',meta['mode']),('uid',0),('gid',0),('atime','20090101000000'),('mtime','20090101000000'),('ctime','20090101000000'),('crtime','20090101000000'),('atime_extra',0),('mtime_extra',0),('ctime_extra',0),('crtime_extra',0)]:
    debug('set_inode_field '+meta['path']+' '+field+' '+str(value),True)
debug('ea_set -f '+meta['label']+' '+meta['path']+' security.selinux',True)

props=capture('/build.prop','build.prop')
text=pathlib.Path(props['file']).read_text()
lines=[s for s in text.splitlines() if not s.startswith('vendor.display.primary_mixer_stages=')]
pathlib.Path(props['file']).write_text('\n'.join(lines)+'\nvendor.display.primary_mixer_stages=1\n')
replace(props)

contexts=capture('/etc/selinux/vendor_file_contexts','vendor_file_contexts')
context=pathlib.Path(contexts['file']).read_text()
label=pathlib.Path(libmeta['label']).read_bytes().rstrip(b'\0').decode()
pathlib.Path(contexts['file']).write_text(context.rstrip()+'\n/vendor/lib64/libeink_shim\\.so    '+label+'\n')
replace(contexts)

for meta in [original,props,contexts]:
    readback=out/('check-'+pathlib.Path(meta['file']).name)
    debug('dump '+meta['path']+' '+str(readback))
    if readback.read_bytes()!=pathlib.Path(meta['file']).read_bytes():raise RuntimeError('Image file readback mismatch')
    labelout=out/('check-'+pathlib.Path(meta['file']).name+'.selinux')
    debug('ea_get -f '+str(labelout)+' '+meta['path']+' security.selinux')
    if labelout.read_bytes()!=pathlib.Path(meta['label']).read_bytes():raise RuntimeError('Original file label changed')

fsck=run(['e2fsck','-f','-n',str(image)])
if any(word in fsck for word in ['Fix?', 'WARNING', 'likely pre-1970', 'UNEXPECTED INCONSISTENCY']):
    raise RuntimeError('Filesystem inspection reported a warning: '+fsck)
(out/'filesystem-check.txt').write_text(fsck)
(out/'patch-report.json').write_text(json.dumps(dict(modified_paths=[composer,'/build.prop','/etc/selinux/vendor_file_contexts'],added_paths=['/lib64/libeink_shim.so'],composer_first_needed=libraries[0],permissions_and_labels_preserved=True,new_library_label=label,filesystem_check_passed=True),indent=2)+'\n')
print('Vendor filesystem edited, files read back and filesystem check passed.',flush=True)
'''


def main():
    os.umask(0o077)
    OUT.mkdir(parents=True, exist_ok=True)
    component = json.loads((ROOT / 'work/eink-color-component-build-2026-11-11.json').read_text())
    if not component['passed'] or not component['color_profile_enabled']:
        raise RuntimeError('Passing color-profile build required')
    library = Path(component['android_library']['path'])
    if hashlib.sha256(library.read_bytes()).hexdigest() != component['android_library']['sha256']:
        raise RuntimeError('Compiled component changed')
    if hashlib.sha256(STOCK.read_bytes()).hexdigest() != STOCK_HASH:
        raise RuntimeError('Original vendor image changed')
    docker = shutil.which('docker')
    context = json.loads(subprocess.run([docker,'context','inspect'],check=True,capture_output=True,text=True,timeout=10).stdout)
    if not context[0]['Endpoints']['docker']['Host'].startswith('unix://'):
        raise RuntimeError('Local Docker context required')
    image = OUT / 'vendor.img'
    if image.exists():
        raise RuntimeError('Existing generated vendor image; inspect rather than overwrite')
    shutil.copyfile(STOCK,image)
    subprocess.run([sys.executable,str(AVB),'erase_footer','--image',str(image)],check=True,capture_output=True,text=True,timeout=30)
    base = json.loads((ROOT/'work/lineage21-source-init-2026-11-11.json').read_text())['image']
    cmd=[docker,'run','--rm','--name','booxos-vendor-derivative-20261111','--platform','linux/amd64','--network','none','--cap-drop','ALL','--security-opt','no-new-privileges','--memory','2g','--cpus','2','--mount','type=bind,src='+str(OUT)+',dst=/output','--mount','type=bind,src='+str(library.parent)+',dst=/component,readonly',base,'python3','-u','-c',SCRIPT]
    result=subprocess.run(cmd,capture_output=True,text=True,timeout=300)
    (OUT/'patch.log').write_text(result.stdout+result.stderr)
    if result.returncode:
        print((result.stdout+result.stderr)[-3500:]);raise RuntimeError('Vendor filesystem modification failed')
    fingerprint='Onyx/GoColor7_2/GoColor7_2:11/2026-04-21_13-54_4.2-rel_0421_19324b3ea/8525:user/release-keys'
    # Keep dm-verity integrity. This first derivative uses SHA256 and omits the
    # optional repair FEC rather than retaining incorrect original FEC bytes.
    subprocess.run([sys.executable,str(AVB),'add_hashtree_footer','--image',str(image),'--partition_name','vendor','--partition_size','594817024','--hash_algorithm','sha256','--algorithm','NONE','--salt','18cffabe0bd1bf22c4cc60c70c05678b8be8017fe2797de7f4ec306a38111da6','--do_not_generate_fec','--prop','com.android.build.vendor.fingerprint:'+fingerprint,'--prop','com.android.build.vendor.os_version:11','--prop','com.android.build.vendor.security_patch:2025-10-01'],check=True,capture_output=True,text=True,timeout=120)
    verify=subprocess.run([sys.executable,str(AVB),'verify_image','--image',str(image)],check=True,capture_output=True,text=True,timeout=120)
    (OUT/'avb-check.txt').write_text(verify.stdout+verify.stderr)
    report=json.loads((OUT/'patch-report.json').read_text())
    report.update(source_vendor_sha256=STOCK_HASH,derivative_vendor_sha256=hashlib.sha256(image.read_bytes()).hexdigest(),bytes=image.stat().st_size,component_sha256=component['android_library']['sha256'],dm_verity_hash='sha256',optional_fec_present=False,footer_and_full_hashtree_verified=True,boox_access=False,install_ready=False,complete_vendor_inventory_comparison_pending=True)
    (ROOT/'work/vendor-derivative-build-2026-11-11.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
