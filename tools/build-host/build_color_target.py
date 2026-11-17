#!/usr/bin/env python3
"""Run a bounded local Lineage configure or image-build phase; no BOOX access."""
import argparse
import datetime
import json
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
MIN_FREE = 80 * 1024**3


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', choices=['configure','images'], default='configure')
    opts = parser.parse_args()
    source = json.loads((ROOT/'work/lineage21-platform-sync-2026-11-11.json').read_text())
    if not source['passed']:
        raise SystemExit('Complete platform checkout required before configuration')
    target = json.loads((ROOT/'work/color-target-provisioned-2026-11-11.json').read_text())
    if target['target']!='lineage_GoColor7_2-ap2a-userdebug':
        raise SystemExit('Wrong release/target provisioning')
    if opts.phase=='images':
        previous = json.loads((ROOT/'work/lineage21-configure-build-2026-11-11.json').read_text())
        if not previous['passed']:
            raise SystemExit('Configuration must pass before the image build')
    docker = shutil.which('docker')
    context = json.loads(subprocess.run([docker,'context','inspect'],capture_output=True,text=True,check=True,timeout=10).stdout)
    if not context[0]['Endpoints']['docker']['Host'].startswith('unix://'):
        raise RuntimeError('Local Docker context required')
    if shutil.disk_usage(ROOT).free<MIN_FREE:
        raise RuntimeError('Physical Mac disk floor reached')
    name='booxos-lineage21-'+opts.phase+'-20261111'
    exists=subprocess.run([docker,'container','inspect',name],capture_output=True,text=True,timeout=10)
    if exists.returncode==0:
        raise RuntimeError('Build container already exists; inspect before reusing its name')
    goals='nothing' if opts.phase=='configure' else 'systemimage productimage systemextimage vbmetaimage'
    script=('set -eu\n'
            'export TARGET_PRODUCT=lineage_GoColor7_2 TARGET_RELEASE=ap2a TARGET_BUILD_VARIANT=userdebug TARGET_BUILD_TYPE=release LINEAGE_BUILD=GoColor7_2\n'
            'export WITH_AVB=true GOMAXPROCS=2 GOGC=20\n'
            'build/soong/soong_ui.bash --make-mode -j1 '+goals+'\n'
            'echo COLOR_BUILD_PHASE_COMPLETE\n')
    args=[docker,'run','--name',name,'--label','project=BooxOS','--platform','linux/amd64',
          '--network','none','--cap-drop','ALL','--security-opt','no-new-privileges',
          '--memory','6g','--cpus','4','--pids-limit','1024','--env','JAVA_TOOL_OPTIONS=-Xmx2g',
          '--mount','type=volume,src=booxos-lineage21-source-20261111,dst=/work',source['image'],
          '/bin/bash','-c',script]
    record={'phase':opts.phase,'started_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'target':target['target'],'goals':goals,'passed':False,'boox_access':False,
            'parallel_build_jobs':1,'container_memory_bytes':6*1024**3,
            'network_enabled':False,'other_containers_modified':False}
    log=ROOT/'.local/mac-build-probe'/('lineage21-'+opts.phase+'-build.log')
    deadline=2700 if opts.phase=='configure' else 21600
    try:
        with log.open('w') as stream:
            p=subprocess.Popen(args,stdout=stream,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL)
            began,last=time.monotonic(),0
            while p.poll() is None:
                free=shutil.disk_usage(ROOT).free
                if free<MIN_FREE or time.monotonic()-began>deadline:
                    subprocess.run([docker,'stop','--timeout','15',name],capture_output=True,timeout=30)
                    record['stop_reason']='Physical disk floor or phase deadline reached'
                    break
                if time.monotonic()-last>25:
                    lines=log.read_text(errors='replace').splitlines()
                    print(json.dumps({'phase':opts.phase,'elapsed_seconds':round(time.monotonic()-began),
                                      'physical_free_GB':round(free/10**9,2),
                                      'stage':lines[-1][-220:] if lines else 'starting'}),flush=True)
                    last=time.monotonic()
                time.sleep(2)
            p.wait(timeout=30)
        record.update(exit_code=p.returncode,elapsed_seconds=round(time.monotonic()-began,2))
        lines=log.read_text(errors='replace').splitlines()
        record['passed']=p.returncode==0 and 'COLOR_BUILD_PHASE_COMPLETE' in lines
        if not record['passed']:record['failure_tail']=lines[-45:]
    finally:
        inspected=subprocess.run([docker,'inspect','--format','{{json .State}}',name],capture_output=True,text=True,timeout=10)
        if inspected.returncode==0:
            state=json.loads(inspected.stdout)
            record['container_state']={k:state[k] for k in ['Status','ExitCode','OOMKilled','Error']}
            if state['Status'] in ['exited','dead','created']:
                subprocess.run([docker,'rm',name],capture_output=True,timeout=15)
        record['physical_host_free_bytes_after']=shutil.disk_usage(ROOT).free
        report=ROOT/'work'/('lineage21-'+opts.phase+'-build-2026-11-11.json')
        report.write_text(json.dumps(record,indent=2)+'\n')
        print(json.dumps(record,indent=2),flush=True)


if __name__=='__main__':
    main()
