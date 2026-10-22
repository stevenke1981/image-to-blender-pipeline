"""Run all three native checks, preserving a truthful NOT_RUN when Blender is absent."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser();p.add_argument('--blender',default='blender');p.add_argument('--out',default=str(ROOT/'gait-output'));p.add_argument('--skip-render',action='store_true')
    a=p.parse_args();out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True)
    executable=shutil.which(a.blender)
    if not executable:
        (out/'blender-status.json').write_text(json.dumps({'status':'NOT_RUN','reason':'Blender executable not found'},indent=2))
        print('NOT_RUN: Blender executable not found');return 2
    results=[]
    for name in ('biped_adult','biped_elder_tired','quadruped_walk'):
        dest=out/name;dest.mkdir(exist_ok=True)
        cmd=[executable,'--background','--factory-startup','--python-exit-code','1','--python',str(ROOT/'scripts/blender_gait.py'),'--','--config',str(ROOT/f'examples/gait/{name}.json'),'--out',str(dest)]
        if a.skip_render:cmd.append('--skip-render')
        # No shell; works with Windows paths containing spaces.
        report_path=dest/'validation.json'
        report_path.write_text(json.dumps({'status':'RUNNING'}))
        try:
            with (dest/'blender.log').open('w') as log:result=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=600)
            report=json.loads(report_path.read_text());passed=result.returncode==0 and report.get('status')=='PASS'
            required=['animation.blend','animation-data.json','rig-map.json']
            if not a.skip_render:required += [f'preview-{i}.png' for i in (1,2,3)]
            passed &= all((dest/f).is_file() and (dest/f).stat().st_size>0 for f in required)
            results.append({'name':name,'passed':passed,'returncode':result.returncode,'report':report})
        except (OSError,subprocess.TimeoutExpired,ValueError) as exc:
            results.append({'name':name,'passed':False,'error':str(exc)})
    passed=all(r['passed'] for r in results)
    (out/'blender-status.json').write_text(json.dumps({'status':'PASS' if passed else 'FAIL','results':results},indent=2))
    return 0 if passed else 1

if __name__=='__main__':sys.exit(main())
