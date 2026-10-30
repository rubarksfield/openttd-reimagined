#!/usr/bin/env python3
from pathlib import Path
import subprocess,json,sys
ROOT=Path(__file__).resolve().parents[1]
uid=json.loads((ROOT/'evidence/ipad-simulator.json').read_text())['simulator_id']
container=Path(subprocess.check_output(['xcrun','simctl','get_app_container',uid,'org.openttd.reimagined.dev','data'],text=True).strip())
p=container/'Documents/OpenTTD/native-session.json';data=json.loads(p.read_text())
name=sys.argv[1] if len(sys.argv)>1 else 'current'
if not name.replace('-','').replace('_','').isalnum():raise ValueError('Use a simple evidence label')
(ROOT/'evidence'/f'native-{name}.json').write_text(json.dumps(data,indent=2))
print(json.dumps({k:v for k,v in data.items() if k!='widgets'},indent=2))
