#!/usr/bin/env python3
"""Observe or send real HID to the recorded, project-owned native simulator."""
from pathlib import Path
import argparse, json, subprocess, time
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['inspect','tap','tile','drag','move','wait-step']);p.add_argument('values',nargs='*');a=p.parse_args()
fixture=json.loads((ROOT/'evidence/ipad-simulator.json').read_text());uid=fixture['simulator_id']
devices=json.loads(subprocess.check_output(['xcrun','simctl','list','devices','available','-j'],text=True))
assert any(d['udid']==uid and d['name'].startswith('OpenTTD ') for group in devices['devices'].values() for d in group),'Use an owned fixture'
container=Path(subprocess.check_output(['xcrun','simctl','get_app_container',uid,'org.openttd.reimagined.dev','data'],text=True).strip());state=container/'Documents/OpenTTD/native-session.json'
def read():return json.loads(state.read_text())
def plain(s):return ''.join(c for c in s if not 0xe000<=ord(c)<=0xf8ff)
if a.action=='tap':subprocess.run(['python3',str(ROOT/'script/tap_native_widget.py'),'--id',a.values[0]],cwd=ROOT,check=True)
elif a.action in ['tile','drag','move']:
    d=read();assert not d.get('suspended') and time.time()-state.stat().st_mtime<2
    points=[]
    origin=fixture['surface_origin']
    if a.action=='move':
        matches=[w for w in d['widgets'] if w['id']==a.values[0]];assert len(matches)==1
        w=matches[0];points=[w['x']+w['w']/2+origin[0],w['y']+w['h']/2+origin[1],*map(int,a.values[1:])];assert len(points)==4
    else:
        numbers=list(map(int,a.values));assert len(numbers)==(2 if a.action=='tile' else 4)
        for i in range(0,len(numbers),2):
            matches=[t for t in d.get('qa_tiles',[]) if t['tile']==numbers[i:i+2]];assert len(matches)==1 and matches[0]['visible'],'Observe unobstructed tiles first'
            x,y=matches[0]['point'];points.extend([x+origin[0],y+origin[1]])
    drivers=[f.parent for f in (Path.home()/'.npm/_npx').glob('*/node_modules/serve-sim/package.json') if json.loads(f.read_text()).get('version')=='0.1.48'];assert drivers
    driver=max(drivers,key=lambda x:(x/'package.json').stat().st_mtime)
    helper='sim_hid_tap.mjs' if a.action=='tile' else 'sim_hid_drag.mjs'
    gesture=points if a.action=='tile' else [*points,800]
    subprocess.run(['node',str(ROOT/'script'/helper),uid,*map(str,fixture['pixel_size']),*map(str,fixture['screen_points']),*map(str,gesture),str(fixture['observed_interface_orientation']),str(driver)],check=True)
elif a.action=='wait-step':
    expected=int(a.values[0]);deadline=time.monotonic()+20
    while time.monotonic()<deadline:
        d=read();logs=d.get('tutorial',{}).get('log',[])
        if any(row['type']<=1 for row in logs):raise RuntimeError(logs)
        steps=[int(row['text'].split()[-1]) for row in logs if row['text'].startswith('TOUCH_TUTORIAL_STEP ')]
        if steps and steps[-1]==expected:break
        time.sleep(.1)
    else:raise RuntimeError(d.get('tutorial'))
else:
    d=read();print(json.dumps({'mode':d.get('mode'),'tick':d.get('tick'),'towns':d.get('towns'),'tutorial':d.get('tutorial'),'targets':d.get('qa_tiles'),'widgets':[(w['id'],plain(w['label']),w.get('highlighted',False)) for w in d.get('widgets',[]) if not w['id'].startswith('ottd.1.') or w.get('highlighted')]},indent=2))
