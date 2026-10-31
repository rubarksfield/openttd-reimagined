#!/usr/bin/env python3
"""Play the bundled lesson with real HID in the recorded project-owned iPad simulator."""
from pathlib import Path
import argparse, json, subprocess, time
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--stop-after-step',type=int,choices=range(18));parser.add_argument('--exercise-placement-errors',action='store_true');parser.add_argument('--simulator-record',type=Path,default=ROOT/'evidence/ipad-simulator.json');args=parser.parse_args()
fixture=json.loads(args.simulator_record.read_text());uid=fixture['simulator_id']
assert fixture['screen_points'][0]>=1000 and fixture['screen_points'][1]>=700 and fixture['observed_interface_orientation'] in [3,4], 'Use an observed landscape iPad fixture'
c=Path(subprocess.check_output(['xcrun','simctl','get_app_container',uid,'org.openttd.reimagined.dev','data'],text=True).strip());state_path=c/'Documents/OpenTTD/native-session.json'
record_file=ROOT/'evidence'/('guided-lesson-hid-stages.json' if args.stop_after_step is None else f'guided-lesson-hid-checkpoint-{args.stop_after_step}.json')
records=[]
def read():
    s=json.loads(state_path.read_text());assert not s.get('suspended') and time.time()-state_path.stat().st_mtime<2
    # WC_ERRMSG is 9 in pinned 15.3. Engine load/content errors are separate
    # from the GameScript log; never accept a paused error as playable progress.
    assert not any(w['class']==9 for w in s['windows']), 'Unexpected original game error window'
    return s
def plain(s):return ''.join(x for x in s if not 0xe000<=ord(x)<=0xf8ff)
def current(s):
    logs=s.get('tutorial',{}).get('log',[])
    assert not any(r['type']<=1 for r in logs),logs
    steps=[int(r['text'].split()[-1]) for r in logs if r['text'].startswith('TOUCH_TUTORIAL_STEP ')]
    return steps[-1] if steps else -1
def step(n,timeout=25):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        s=read()
        if current(s)>=n:break
        time.sleep(.1)
    else:raise RuntimeError(s.get('tutorial'))
    records.append({'expected_step':n,'observed_step':current(s),'tick':s['tick'],'tutorial':s['tutorial']})
    record_file.write_text(json.dumps(records,indent=2))
    print('Verified original lesson step',n,'(observed',current(s),')',flush=True)
    if args.stop_after_step==n:raise SystemExit(0)
    return s
def action(*values):subprocess.run(['python3',str(ROOT/'script/qa_native_action.py'),*map(str,values),'--simulator-record',str(args.simulator_record)],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
def tap(id):action('tap',id)
def label(text):subprocess.run(['python3',str(ROOT/'script/tap_native_widget.py'),'--label',text,'--simulator-record',str(args.simulator_record)],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
placement_records=[]
def placement_help(expected_step,phrase):
    deadline=time.monotonic()+20
    while time.monotonic()<deadline:
        s=read()
        if phrase in s.get('tutorial',{}).get('text',''):break
        time.sleep(.1)
    else:raise RuntimeError(s.get('tutorial'))
    assert current(s)==expected_step,'A misplaced build must not advance the lesson'
    assert s['tutorial']['target']['label']=='Show build tile'
    assert s['camera'][2]<=1,'Placement targets need a usable close-up'
    placement_records.append(s)
    (ROOT/'evidence/tutorial-placement-recovery-hid.json').write_text(json.dumps(placement_records,indent=2))
    label('Show build tile');close_story()
    shot=ROOT/'evidence'/f'tutorial-placement-{expected_step}-{len(placement_records)}.png'
    subprocess.run(['xcrun','simctl','io',uid,'screenshot',str(shot)],check=True,stdout=subprocess.DEVNULL)
    print('Verified placement recovery:',phrase,flush=True)
def close_story():
    if any(w['id']=='ottd.close.39.0' for w in read()['widgets']):tap('ottd.close.39.0')
def selected(id):return next(w['selected'] for w in read()['widgets'] if w['id']==id)
def pan():
    packages=[p.parent for p in (Path.home()/'.npm/_npx').glob('*/node_modules/serve-sim/package.json') if json.loads(p.read_text()).get('version')=='0.1.48'];assert packages
    subprocess.run(['node',str(ROOT/'script/sim_two_finger_drag.mjs'),uid,*map(str,fixture['pixel_size']),*map(str,fixture['screen_points']),'700','430','750','480','150','0','700',str(fixture['observed_interface_orientation']),str(packages[-1])],cwd=ROOT,check=True)
s=read();assert s['mode']=='menu','Start at the owned fixture main menu; never replace an active game'
label('Help & Manuals');label('First steps tutorial');label('Play first-route lesson');step(0)
assert not read()['newgrfs'],'The starter level must not inherit optional content'
label('Begin lesson');step(1);close_story();tap('ottd.1.0.22');label('Road construction');step(2)
tap('ottd.3.1.7');step(3);close_story();tap('ottd.57.1.5');action('move','ottd.57.1.0',210,155)
if args.exercise_placement_errors:
    action('tile',35,64);placement_help(3,'THAT BUILD IS OUTSIDE');close_story()
action('tile',34,64)
step(4);close_story();assert selected('ottd.57.1.5');action('tile',78,64)
step(5);close_story();tap('ottd.3.1.5');step(6);close_story();tap('ottd.59.1.4');action('move','ottd.59.1.0',210,155)
if args.exercise_placement_errors:
    action('tile',49,65);placement_help(6,'THAT BUILD IS OUTSIDE');close_story()
    tap('ottd.59.1.3');action('tile',48,65);placement_help(6,'RIGHT TILE, WRONG');close_story()
    tap('ottd.3.1.4');action('tile',48,65)
    tap('ottd.3.1.5');tap('ottd.59.1.4')
action('tile',48,65)
step(7);close_story();tap('ottd.close.3.1');action('tile',48,65)
step(8);close_story();tap('ottd.48.8368.10');step(9);close_story();tap('ottd.54.8368.9');step(10);step(11);close_story()
for id in ['ottd.close.54.8368','ottd.close.48.8368']:
    if any(w['id']==id for w in read()['widgets']):tap(id)
tap('ottd.46.0.8');step(12);assert selected('ottd.25.0.9'),'Story Book must preserve original quick Go To'
close_story();action('move','ottd.25.0.0',210,155);pan();assert selected('ottd.25.0.9'),'Two-finger navigation must preserve Go To'
action('tile',34,64);step(13);assert selected('ottd.25.0.9'),'The next Story Book step must preserve Go To'
close_story();pan();action('tile',78,64);step(14);close_story();tap('ottd.close.25.0');tap('ottd.46.0.2');step(15)
tap('ottd.1.0.1');step(16,60);step(17,60);tap('ottd.1.0.1')
s=read();assert s['tick']>12 and s['graphics_set']=='OpenGFX' and s['sound_set']=='OpenSFX' and not s['newgrfs']
(ROOT/'evidence/native-guided-lesson-final.json').write_text(json.dumps(s,indent=2))
subprocess.run(['xcrun','simctl','io',uid,'screenshot',str(ROOT/'evidence/native-guided-lesson-final.png')],check=True)
print('PASS: real original controls, construction, orders, motion, passengers and fare; no injected game commands',flush=True)
