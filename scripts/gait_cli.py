"""Generate/editable JSON profiles and Blender-independent trajectory evidence."""
import argparse
import csv
from html import escape
import json
from pathlib import Path
from gait.core import plan, validate, trajectory, measure, limbs


def preview(c,rows,path):
    # Exact trajectory chart, explicitly not a Blender render.
    parts=['<svg xmlns="http://www.w3.org/2000/svg" width="900" height="420" viewBox="0 0 900 420">',
           '<rect width="900" height="420" fill="#101924"/>',
           '<g fill="#eff5ff" font-family="sans-serif"><text x="30" y="35" font-size="22">'+escape(c['name'])+'</text>',
           '<text x="30" y="60">PLANNED FOOT HEIGHTS — mathematical preview, Blender NOT RUN</text>',
           '<text x="30" y="395">One cycle / seconds →     Stance height = 0 m; vertical scale is per profile</text></g>']
    colors=['#51d4b2','#ffbb65','#8aabff','#f68cbd']
    for idx,n in enumerate(limbs(c)):
        base=120+idx*60
        points=' '.join(f"{120+row['time_s']/c['cycle_s']*730:.2f},{base-row['feet'][n]['position'][2]/c['foot_clearance_m']*40:.2f}" for row in rows)
        parts += [f'<text x="15" y="{base}" fill="white" font-family="sans-serif" font-size="12">{n}</text>',f'<path d="M120 {base}H850" stroke="#56616c"/>',f'<polyline points="{points}" fill="none" stroke="{colors[idx]}" stroke-width="2"/>']
    parts.append('</svg>');path.write_text('\n'.join(parts))


def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('plan');a.add_argument('--type',choices=['biped','quadruped'],default='biped')
    for flag,default in [('age-years',25.),('maturity-years',18.),('leg-length-m',.9),('body-length-m',.8),('hip-width-m',.3),('upper-leg-ratio',.5),('speed-mps',.65)]:
        a.add_argument('--'+flag,type=float,default=default)
    a.add_argument('--state',choices=['neutral','tired','energetic'],default='neutral');a.add_argument('--fps',type=int,default=30);a.add_argument('--out',required=True)
    a=sub.add_parser('inspect');a.add_argument('--config',required=True);a.add_argument('--out',required=True)
    args=p.parse_args()
    if args.command=='plan':
        opts=vars(args).copy();opts['kind']=opts.pop('type');opts.pop('command');out=Path(opts.pop('out'))
        c=plan(**opts);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(c,indent=2)+'\n')
    else:
        c=validate(json.loads(Path(args.config).read_text()));out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
        rows=trajectory(c);report=measure(c,rows)
        report.update(source='mathematical trajectory only',blender_status='NOT_RUN')
        (out/'planned-validation.json').write_text(json.dumps(report,indent=2)+'\n')
        with (out/'planned-trajectory.csv').open('w',newline='') as f:
            w=csv.writer(f);w.writerow(['time_s','limb','x_m','y_m','z_m','stance'])
            for row in rows:
                for n,foot in row['feet'].items():w.writerow([row['time_s'],n,*foot['position'],int(foot['stance'])])
        preview(c,rows,out/'planned-preview.svg')
        if not report['passed']:raise SystemExit('planned trajectory validation failed')

if __name__=='__main__':main()
