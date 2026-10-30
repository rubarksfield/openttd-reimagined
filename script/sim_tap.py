#!/usr/bin/env python3
"""Tap an observed 800x556 screenshot on the owned iPad fixture (interface orientation 4).
Uses explicit native HID down/up; never sends game commands.
"""
import argparse,json,pathlib,subprocess,os
root=pathlib.Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('x',type=float);p.add_argument('y',type=float);p.add_argument('--driver-root',type=pathlib.Path);a=p.parse_args()
assert 0<=a.x<800 and 0<=a.y<556
uid=json.loads((root/'evidence/ipad-simulator.json').read_text())['simulator_id']
container=pathlib.Path(subprocess.check_output(['xcrun','simctl','get_app_container',uid,'org.openttd.reimagined.dev','data'],text=True).strip())
state=json.loads((container/'Documents/OpenTTD/native-session.json').read_text())
assert state['surface'][0]>state['surface'][1], 'Use the owned landscape-left simulator fixture'
driver=a.driver_root or (pathlib.Path(os.environ['SERVE_SIM_PACKAGE']) if os.environ.get('SERVE_SIM_PACKAGE') else None)
if driver is None:
 candidates=[p.parent for p in (pathlib.Path.home()/'.npm/_npx').glob('*/node_modules/serve-sim/package.json') if json.loads(p.read_text()).get('version')=='0.1.48']
 if not candidates:raise RuntimeError('Install audited serve-sim 0.1.48 or pass --driver-root')
 driver=max(candidates,key=lambda p:(p/'package.json').stat().st_mtime)
subprocess.run(['node',str(root/'script/sim_hid_tap.mjs'),uid,'2360','1640','800','556',str(a.x),str(a.y),'4',str(driver)],check=True)
