#!/usr/bin/env python3
"""Pin the official OpenSFX set, preserving its licence inside the original tar."""
from pathlib import Path
import hashlib
import json
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://cdn.openttd.org/opensfx-releases/1.0.3/opensfx-1.0.3-all.zip'
# Official checksum: https://www.openttd.org/downloads/opensfx-releases/latest
SHA256 = 'e0a218b7dd9438e701503b0f84c25a97c1c11b7c2f025323fb19d6db16ef3759'
archive = ROOT / 'downloads/opensfx-1.0.3-all.zip'
archive.parent.mkdir(parents=True, exist_ok=True)
if not archive.exists():
    subprocess.run(['curl', '-fL', '--max-time', '60', URL, '-o', str(archive)], check=True)
if hashlib.sha256(archive.read_bytes()).hexdigest() != SHA256:
    raise RuntimeError('OpenSFX checksum mismatch')
with zipfile.ZipFile(archive) as package:
    names = [n for n in package.namelist() if Path(n).name == 'opensfx-1.0.3.tar']
    if len(names) != 1:
        raise RuntimeError('Unexpected OpenSFX package layout')
    data = package.read(names[0])
target = ROOT / 'build/ipad-resources/baseset/opensfx-1.0.3.tar'
target.parent.mkdir(parents=True, exist_ok=True)
target.write_bytes(data)
(ROOT / 'evidence/opensfx-checksum.json').write_text(json.dumps({
    'url': URL, 'sha256': SHA256, 'verified': True,
    'tar_sha256': hashlib.sha256(data).hexdigest(),
    'licence': 'See the unmodified licence and attribution files inside the tar',
}, indent=2))
print('Verified official OpenSFX 1.0.3 and installed native resource')
