#!/usr/bin/env python3
"""Acquire the pinned upstream archive reader used by native content import."""
from pathlib import Path
import hashlib
import json
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = '3.8.10'
URL = f'https://github.com/libarchive/libarchive/releases/download/v{VERSION}/libarchive-{VERSION}.tar.xz'
SHA256 = '56cad765459d5ee25a3b761f90c47d99379d28297fbfb72d908880d6b875fb96'
archive = ROOT / f'downloads/native-deps/libarchive-{VERSION}.tar.xz'
archive.parent.mkdir(parents=True, exist_ok=True)
if not archive.exists():
    subprocess.run(['curl', '-fL', '--max-time', '60', URL, '-o', str(archive)], check=True)
if hashlib.sha256(archive.read_bytes()).hexdigest() != SHA256:
    raise RuntimeError('Libarchive source checksum mismatch')
target = ROOT / f'vendor/native-deps/libarchive-{VERSION}'
if not target.exists():
    with tarfile.open(archive) as package:
        package.extractall(target.parent, filter='data')
(ROOT / 'evidence/native-dependency-libarchive.json').write_text(json.dumps({
    'version': VERSION, 'url': URL, 'sha256': SHA256,
    'digest_source': 'Official GitHub release API asset digest',
    'verified': True, 'licence': 'See unmodified COPYING in the source and app notices',
    'build': 'Static target build; no undeclared iOS system libarchive API',
}, indent=2))
print('Verified upstream libarchive', VERSION)
