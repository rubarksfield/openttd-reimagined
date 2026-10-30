#!/usr/bin/env python3
"""Validate the real training save with unmodified OpenTTD; optionally capture an owned simulator's prepared intro."""
from pathlib import Path
import argparse, hashlib, json, shutil, subprocess, tempfile
from inspect_save_date import inspect
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--capture-owned-simulator',action='store_true',help='Capture its suspended real exit save; prepare the disposable world through original UI first')
args=p.parse_args()
target=ROOT/'content/scenario/First Route.sav'
work=Path(tempfile.mkdtemp(prefix='tutorial-validation-',dir=ROOT/'runtime'))
source=target
if args.capture_owned_simulator:
    uid=json.loads((ROOT/'evidence/ipad-simulator.json').read_text())['simulator_id']
    devices=json.loads(subprocess.check_output(['xcrun','simctl','list','devices','available','-j'],text=True))
    assert any(d['udid']==uid and d['name'].startswith('OpenTTD ') for group in devices['devices'].values() for d in group),'Use an owned test simulator'
    container=Path(subprocess.check_output(['xcrun','simctl','get_app_container',uid,'org.openttd.reimagined.dev','data'],text=True).strip())
    state=json.loads((container/'Documents/OpenTTD/native-session.json').read_text())
    assert state.get('suspended') and state.get('mode')=='normal','Background the prepared intro to complete its original exit save first'
    source=container/'Documents/OpenTTD/save/autosave/exit.sav'
fixture=work/'intro.sav';shutil.copyfile(source,fixture)
(work/'baseset').mkdir();shutil.copyfile(ROOT/'runtime/reference/baseset/opengfx-8.0.tar',work/'baseset/opengfx-8.0.tar')
shutil.copytree(ROOT/'content/game/TouchFirstRoute',work/'game/TouchFirstRoute')
config=work/'openttd.cfg';config.write_text('[misc]\nlanguage = english.lng\n[gui]\nautosave_on_exit = true\nautosave = off\n')
command=[str(ROOT/'build/reference/openttd'),'-X','-x','-c',str(config),'-g',str(fixture),'-I','OpenGFX','-S','NoSound','-M','NoMusic','-snull','-mnull','-vnull:ticks=100','-d','script=4']
r=subprocess.run(command,cwd=work,text=True,capture_output=True,timeout=45);log=r.stdout+'\n'+r.stderr
(ROOT/'runtime/tutorial-template-validation.log').write_text(log)
if r.returncode or 'TOUCH_TUTORIAL_STEP 0' not in log or 'error:' in log.lower() or '[E]' in log or 'died' in log.lower() or ('grf:' in log and 'not found' in log):
    raise RuntimeError(log[-5000:])
validated=work/'save/autosave/exit.sav'
if inspect(validated)['date_fields']['pause_mode'] & 8:
    raise RuntimeError('The original engine saved an error pause; do not ship this lesson')
if args.capture_owned_simulator:shutil.copyfile(validated,target)
record={'engine':'Unmodified upstream OpenTTD 15.3','exit_code':r.returncode,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'bytes':target.stat().st_size,'source':'Real native prepared intro; original commands and serialized GameScript state','scope':'Original engine loads/resumes the intro script and translations, then saves without script errors. Full player-input lesson acceptance is separate; the intro intentionally pauses simulation.'}
(ROOT/'evidence/tutorial-template-validation.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
