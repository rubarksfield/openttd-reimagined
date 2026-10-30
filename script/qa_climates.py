#!/usr/bin/env python3
"""Generate disposable worlds through original UI/HID on the owned iPad fixture."""
from pathlib import Path
import subprocess,json,time,argparse
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('climates',type=int,nargs='+',choices=range(4));args=parser.parse_args()
uid=json.loads((ROOT/'evidence/ipad-simulator.json').read_text())['simulator_id']
container=Path(subprocess.check_output(['xcrun','simctl','get_app_container',uid,'org.openttd.reimagined.dev','data'],text=True).strip());state=container/'Documents/OpenTTD/native-session.json'
def read():return json.loads(state.read_text())
def tap(identifier):subprocess.run(['python3',str(ROOT/'script/tap_native_widget.py'),'--id',identifier],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
def wait(predicate):
 deadline=time.monotonic()+40
 while time.monotonic()<deadline:
  try:d=read()
  except(ValueError,OSError):time.sleep(.2);continue
  if predicate(d):return d
  time.sleep(.2)
 raise RuntimeError('Original game did not reach the expected UI/state')
names=['temperate','subarctic','subtropical','toyland']
for climate in args.climates:
 if read().get('mode')=='normal':
  tap('ottd.1.0.3');tap('ottd.dropdown.2')
  d=wait(lambda d:d.get('mode')=='menu' or any(w['id']=='ottd.12.0.3' for w in d.get('widgets',[])))
  if d['mode']!='menu':tap('ottd.12.0.3')
 wait(lambda d:d.get('mode')=='menu');tap('ottd.63.0.0');tap(f'ottd.65.0.{climate}');tap('ottd.65.0.9')
 d=wait(lambda d:d.get('mode')=='normal' and d.get('landscape')==climate)
 if not(d['towns']>0 and d['industries']>0 and d['map_width']==d['map_height']==128):raise RuntimeError('Unexpected generated world')
 tap('ottd.1.0.0');d=wait(lambda d:any(w['id']=='ottd.1.0.0' and w.get('selected') for w in d['widgets']))
 (ROOT/'evidence'/f'native-qa-{names[climate]}-world.json').write_text(json.dumps(d,indent=2))
 subprocess.run(['xcrun','simctl','io',uid,'screenshot',str(ROOT/'evidence'/f'native-qa-{names[climate]}-world.png')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 print(names[climate],': original generation, populated world, pause and screenshot passed',flush=True)
