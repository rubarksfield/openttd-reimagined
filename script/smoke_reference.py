#!/usr/bin/env python3
"""Run the unmodified engine on a real save, step it, save, and load that save again."""
from pathlib import Path
import subprocess, json, shutil, hashlib, time
from inspect_save_date import inspect
ROOT=Path(__file__).resolve().parents[1]
BINARY=ROOT/'build/reference/openttd'
WORK=ROOT/'runtime/reference-smoke'
WORK.mkdir(parents=True, exist_ok=True)
(WORK/'baseset').mkdir(exist_ok=True)
shutil.copy2(ROOT/'runtime/reference/baseset/opengfx-8.0.tar', WORK/'baseset/opengfx-8.0.tar')
reference=Path(subprocess.check_output(['python3',str(ROOT/'script/prepare_upstream.py'),'--reference'],text=True).strip())
fixture=reference/'media/baseset/opntitle.dat'
source=WORK/'fixture.sav'
shutil.copy2(fixture,source)
config=WORK/'openttd.cfg'
config.write_text('[gui]\nautosave_on_exit = true\nautosave = off\n\n[misc]\nlanguage = english.lng\n')

def run(name,args):
    cmd=[str(BINARY),*map(str,args)]
    start=time.monotonic()
    r=subprocess.run(cmd,cwd=WORK,capture_output=True,text=True,timeout=60)
    record={'command':cmd,'exit_code':r.returncode,'elapsed_seconds':time.monotonic()-start,'stdout':r.stdout,'stderr':r.stderr}
    (ROOT/'evidence'/f'{name}.json').write_text(json.dumps(record,indent=2))
    if r.returncode:raise RuntimeError(f'{name}: {r.returncode}: {r.stderr}')
    return record
common=['-X','-x','-c',config,'-I','OpenGFX','-S','NoSound','-M','NoMusic','-snull','-mnull','-Q']
run('reference-step-save',[*common,'-g',source,'-vnull:ticks=1000'])
saves=list(WORK.rglob('exit.sav'))
assert len(saves)==1,f'Expected one sandbox exit save, found {saves}'
saved=saves[0]
first_saved=WORK/'first-exit.sav'
shutil.copy2(saved, first_saved)
info=run('reference-saved-info',['-X','-q',first_saved])
# Reload the actual engine-produced save and step it again; no simulation replacement.
run('reference-reload',[*common,'-g',first_saved,'-vnull:ticks=10'])
summary={'engine_version':'15.3','initial_fixture_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'saved_file':str(saved.relative_to(ROOT)),'saved_bytes':saved.stat().st_size,'saved_sha256_after_reload':hashlib.sha256(saved.read_bytes()).hexdigest(),'first_run_game_loop_iterations':1000,'reload_game_loop_iterations':10,'save_info':info['stdout'],'all_processes_exited_zero':True,'limitations':['Original macOS headless reference, not iPad runtime.','GameLoop iteration count is not asserted to equal authoritative simulation ticks.','No new earning route or native UI was demonstrated.']}
before=inspect(source); after=inspect(first_saved); reloaded=inspect(saved)
summary['date_before']=before
summary['date_after']=after
summary['date_after_reload']=reloaded
summary['observed_tick_advance']=after['date_fields']['tick_counter']-before['date_fields']['tick_counter']
summary['observed_reload_tick_advance']=reloaded['date_fields']['tick_counter']-after['date_fields']['tick_counter']
assert summary['observed_tick_advance']>0, 'Simulation did not step'
assert summary['observed_reload_tick_advance']>0, 'Reloaded simulation did not step'
(ROOT/'evidence/reference-smoke-summary.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2))
