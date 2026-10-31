#!/usr/bin/env python3
"""Resolve a current original widget, then send real Simulator HID, never a game command."""
import argparse,json,os,pathlib,subprocess,time
ROOT=pathlib.Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
g=p.add_mutually_exclusive_group(required=True);g.add_argument('--id');g.add_argument('--label')
p.add_argument('--simulator-record',type=pathlib.Path,default=ROOT/'evidence/ipad-simulator.json')
p.add_argument('--driver-root',type=pathlib.Path)
a=p.parse_args();fixture=json.loads(a.simulator_record.read_text());uid=fixture['simulator_id']
container=pathlib.Path(subprocess.check_output(['xcrun','simctl','get_app_container',uid,'org.openttd.reimagined.dev','data'],text=True).strip())
state_path=container/'Documents/OpenTTD/native-session.json'
def plain(text):return ''.join(c for c in text if not 0xE000<=ord(c)<=0xF8FF)
matches=[]
for _ in range(60):
 state=json.loads(state_path.read_text())
 if state.get('suspended'):raise RuntimeError('Foreground the owned app first')
 matches=[w for w in state.get('widgets',[]) if (w['id']==a.id if a.id else plain(w['label'])==a.label)]
 if matches and (len(matches)!=1 or not matches[0].get('disabled')):break
 time.sleep(.05)
if len(matches)!=1:raise RuntimeError(f'Expected one current original widget, found {len(matches)}')
w=matches[0]
if w.get('disabled'):raise RuntimeError('Original widget is disabled')
if time.time()-state_path.stat().st_mtime>2:raise RuntimeError('Runtime widget snapshot is stale')
if state['surface']!=fixture['surface_points']:raise RuntimeError('Observe and update the fixture geometry after resizing')
cx=w['x']+w['w']/2;cy=w['y']+w['h']/2
if not (0<=cx<state['surface'][0] and 0<=cy<state['surface'][1]):raise RuntimeError('Widget centre is outside the visible surface')
origin=fixture['surface_origin'];scene=fixture['screen_points'];pixels=fixture['pixel_size'];view=fixture.get('surface_view_points',state['surface'])
# Small phones can display the engine's 400-unit minimum height in a shorter
# safe-area view. Invert the native host's actual framebuffer-to-view transform.
point=(origin[0]+cx*view[0]/state['surface'][0],origin[1]+cy*view[1]/state['surface'][1])
driver=a.driver_root or (pathlib.Path(os.environ['SERVE_SIM_PACKAGE']) if os.environ.get('SERVE_SIM_PACKAGE') else None)
if driver is None:
 candidates=[p.parent for p in (pathlib.Path.home()/'.npm/_npx').glob('*/node_modules/serve-sim/package.json') if json.loads(p.read_text()).get('version')=='0.1.48']
 if not candidates:raise RuntimeError('Pass --driver-root for audited serve-sim 0.1.48')
 driver=max(candidates,key=lambda p:(p/'package.json').stat().st_mtime)
subprocess.run(['node',str(ROOT/'script/sim_hid_tap.mjs'),uid,*map(str,pixels),*map(str,scene),*map(str,point),str(fixture['observed_interface_orientation']),str(driver)],check=True)
print(json.dumps({'widget':w['id'],'label':plain(w['label']),'scene_point':point,'input':'Native Simulator HID down/up; verify resulting state separately'}))
