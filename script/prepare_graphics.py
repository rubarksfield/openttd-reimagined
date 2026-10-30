#!/usr/bin/env python3
"""Acquire the exact free base-graphics fixture for reference tests, not a mod."""
from pathlib import Path
import hashlib, json, subprocess, zipfile
ROOT=Path(__file__).resolve().parents[1]
archive=ROOT/'downloads/opengfx-8.0-all.zip';archive.parent.mkdir(exist_ok=True)
url='https://cdn.openttd.org/opengfx-releases/8.0/opengfx-8.0-all.zip'
sha='43a0c1dabf39cb865394f3a6cc36d4da5c10ecfaaf55652043104806810903be'
if not archive.exists():subprocess.run(['curl','-fL','--max-time','60',url,'-o',str(archive)],check=True)
if hashlib.sha256(archive.read_bytes()).hexdigest()!=sha:raise RuntimeError('Base-graphics checksum mismatch')
with zipfile.ZipFile(archive) as package:
    names=[name for name in package.namelist() if name.endswith('/opengfx-8.0.tar') or name=='opengfx-8.0.tar']
    if len(names)!=1:raise RuntimeError('Unexpected graphics package layout')
    data=package.read(names[0])
for base in ['runtime/reference/baseset','build/reference/baseset']:
    target=ROOT/base;target.mkdir(parents=True,exist_ok=True);(target/'opengfx-8.0.tar').write_bytes(data)
(ROOT/'evidence/opengfx-checksum.json').write_text(json.dumps({'url':url,'sha256':sha,'verified':True,'license':'GPL v2; see the included OpenGFX license/readme'},indent=2))
print('Verified OpenGFX 8.0 and installed project-owned test fixture')
