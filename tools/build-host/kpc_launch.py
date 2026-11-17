#!/usr/bin/env python3
"""Verify transferred inputs and launch only the isolated BOOX image build."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

BRINGUP = '--bringup' in sys.argv[1:]
ROOT = Path('/home/kjseg/booxos-lineage21-20261115')
IMAGE = 'sha256:b4ece63d16da55dab0405cd8a691454e30dfac308602ee2797e88f35d53cadb2'
NAME = 'booxos-lineage21-20261115'
EXPECTED = {
    'boot': 'ede53420966b3af1a3a7b02cae3fef8583a0e01d19271006287dc14b4457ba63',
    'dtbo': '7379d4fb7906fa3bdbb2b8048b7c868cb9fc584b1e26765ed9f4ee8941f54ab9',
    'odm': 'db101ba203846cc257b04a954c9330b9feb1ad8ab12d0a5cc7cddff0bd88c15b',
    'vendor': '0de3bbecd82076ace81c45e830acd7355587dc82184efe9a5aae3bb3913c474f',
}

for name, expected in EXPECTED.items():
    path = ROOT/'source/device/onyx/GoColor7_2/prebuilts'/(name+'.img')
    with path.open('rb') as stream:
        actual = hashlib.file_digest(stream, 'sha256').hexdigest()
    if actual != expected:
        raise RuntimeError('Input hash mismatch: '+name)
head = subprocess.check_output(['git', '-c', 'safe.directory=*', '-C', str(ROOT/'source/.repo/manifests'),
                                'rev-parse', 'HEAD'], text=True).strip()
if head != '121f4ec5f11dc98ff2c427bc9d23165e914c54bb':
    raise RuntimeError('Manifest revision mismatch')
if int(subprocess.check_output(['df', '-B1', '--output=avail', '/mnt/c'], text=True).splitlines()[-1]) < 80*1024**3:
    raise RuntimeError('Less than 80 GiB physical disk space remains before build')
old = subprocess.run(['docker', 'inspect', '--format', '{{.State.Running}}', NAME],
                     capture_output=True, text=True)
if old.returncode == 0:
    if old.stdout.strip() != 'false':
        raise RuntimeError('Previous build container is still running')
    subprocess.check_call(['docker', 'rm', NAME], stdout=subprocess.DEVNULL)
args = ['docker', 'run', '-d', '--name', NAME, '--label', 'project=BooxOS',
        '-e', 'BOOXOS_BRINGUP='+('1' if BRINGUP else '0'),
        '--init', '--network', 'none', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
        '--memory', '36g', '--memory-swap', '44g', '--cpus', '24', '--pids-limit', '8192',
        '--mount', 'type=bind,src='+str(ROOT/'source')+',dst=/work',
        '--mount', 'type=bind,src='+str(ROOT/'logs')+',dst=/logs',
        '--mount', 'type=bind,src='+str(ROOT/'kpc_build.sh')+',dst=/runner.sh,readonly',
        IMAGE, 'bash', '/runner.sh']
container_id = subprocess.check_output(args, text=True).strip()
with (ROOT/'logs/watch.log').open('a') as stream:
    subprocess.Popen(['python3', str(ROOT/'kpc_watch.py')], stdin=subprocess.DEVNULL,
                     stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
report = {'container_id': container_id, 'name': NAME, 'image': IMAGE,
          'input_hashes_verified': True, 'manifest_commit': head, 'wsl_limit_GB': 40,
          'container_memory_GB': 36, 'build_jobs': 8, 'boox_access': False,
          'flavor': 'bringup' if BRINGUP else 'standard'}
(ROOT/'logs/launch.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report), flush=True)
