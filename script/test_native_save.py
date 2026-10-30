#!/usr/bin/env python3
"""Load an actual simulator-created save in the unchanged reference engine."""
import argparse, hashlib, json, pathlib, shutil, subprocess, time, tempfile
from inspect_save_date import inspect
ROOT=pathlib.Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--simulator-record',type=pathlib.Path,default=ROOT/'evidence/ipad-simulator.json',help='Project-owned simulator evidence record')
parser.add_argument('--exit-save',action='store_true',help='Test the original engine background exit save')
parser.add_argument('--label',default='native-save',help='Evidence basename, preserving previous runs when testing imports')
parser.add_argument('--returned-name',default='Stock roundtrip.sav',help='Name of the QA save returned to the native app')
args=parser.parse_args()
sim=json.loads(args.simulator_record.read_text());udid=sim['simulator_id']
devices=json.loads(subprocess.check_output(['xcrun','simctl','list','devices','available','-j'],text=True))
if not any(d['udid']==udid and d['name'].startswith('OpenTTD ') for group in devices['devices'].values() for d in group):raise RuntimeError('Use a project-owned OpenTTD simulator')
container=pathlib.Path(subprocess.check_output(['xcrun','simctl','get_app_container',udid,'org.openttd.reimagined.dev','data'],text=True).strip())
if not args.label.replace('-','').isalnum() or pathlib.Path(args.returned_name).name!=args.returned_name or not args.returned_name.endswith('.sav'):
 raise RuntimeError('Use a plain evidence label and .sav filename')
save_root=container/'Documents/OpenTTD/save'
saves=list(save_root.rglob('exit.sav')) if args.exit_save else list(save_root.glob('*.sav'))
if not saves: raise RuntimeError('Save a real game through the native UI first')
source=max(saves,key=lambda p:p.stat().st_mtime)
# Every reference run starts without cached mods. A stale downloaded archive
# must not mask a missing asset in the native app's actual imported content.
work=pathlib.Path(tempfile.mkdtemp(prefix='native-save-roundtrip-',dir=ROOT/'runtime'))
(work/'baseset').mkdir(exist_ok=True)
shutil.copy2(ROOT/'runtime/reference/baseset/opengfx-8.0.tar',work/'baseset/opengfx-8.0.tar')
content=container/'Documents/OpenTTD/content_download'
if content.exists():shutil.copytree(content,work/'content_download',dirs_exist_ok=True)
installed=container/'Documents/OpenTTD/newgrf'
if installed.exists():shutil.copytree(installed,work/'newgrf')
assets=[{'file':str(f.relative_to(content)),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f in sorted(content.rglob('*.tar'))] if content.exists() else []
imported_assets=[{'file':str(f.relative_to(installed)),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f in sorted(installed.rglob('*')) if f.is_file()] if installed.exists() else []
fixture=work/'native-created.sav';shutil.copy2(source,fixture)
config=work/'openttd.cfg';config.write_text('[gui]\nautosave_on_exit = true\nautosave = off\n[misc]\nlanguage = english.lng\n')
cmd=[str(ROOT/'build/reference/openttd'),'-X','-x','-c',str(config),'-I','OpenGFX','-S','NoSound','-M','NoMusic','-snull','-mnull','-g',str(fixture),'-vnull:ticks=10']
start=time.monotonic();r=subprocess.run(cmd,cwd=work,capture_output=True,text=True,timeout=60)
record={'command':cmd,'exit_code':r.returncode,'elapsed_seconds':time.monotonic()-start,'stdout':r.stdout,'stderr':r.stderr}
(ROOT/'evidence'/f'{args.label}-reference-load.json').write_text(json.dumps(record,indent=2))
if r.returncode:raise RuntimeError(r.stderr)
results=list(work.rglob('exit.sav'))
if len(results)!=1:raise RuntimeError(f'Expected one reference exit save: {results}')
result=results[0];before=inspect(fixture);after=inspect(result)
advance=after['date_fields']['tick_counter']-before['date_fields']['tick_counter']
assert advance==10,advance
native_target=save_root/args.returned_name;shutil.copy2(result,native_target)
summary={'native_source':str(source.relative_to(save_root)),'native_bytes':fixture.stat().st_size,'native_sha256':hashlib.sha256(fixture.read_bytes()).hexdigest(),'community_archives':assets,'imported_assets':imported_assets,'fresh_reference_workdir':str(work),'native_date':before,'reference_date':after,'reference_tick_advance':advance,'reference_exit_code':r.returncode,'returned_file':native_target.name,'native_reload_verified':False,'scope':'One simulator-created save with the app’s actual downloaded/imported GRFs loaded, stepped and saved by unchanged OpenTTD 15.3 in a fresh directory. Native UI reload is a separate check.'}
(ROOT/'evidence'/f'{args.label}-roundtrip.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
