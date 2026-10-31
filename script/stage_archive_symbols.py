#!/usr/bin/env python3
"""Stage CMake's externally located dSYM into its matching application archive."""
from pathlib import Path
import argparse
import plistlib
import re
import shutil
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('archive', type=Path)
parser.add_argument('symbols', type=Path)
args = parser.parse_args()
metadata = plistlib.loads((args.archive / 'Info.plist').read_bytes())
app = args.archive / 'Products' / metadata['ApplicationProperties']['ApplicationPath']
info = plistlib.loads((app / 'Info.plist').read_bytes())
def uuids(path):
    return set(re.findall(r'UUID: ([A-F0-9-]+)', subprocess.check_output(['xcrun', 'dwarfdump', '--uuid', str(path)], text=True)))
binary = uuids(app / info['CFBundleExecutable'])
assert binary and binary == uuids(args.symbols / 'Contents/Resources/DWARF' / info['CFBundleExecutable']), 'Refusing symbols from a different binary'
target = args.archive / 'dSYMs' / args.symbols.name
shutil.copytree(args.symbols, target, dirs_exist_ok=True)
assert binary == uuids(target / 'Contents/Resources/DWARF' / info['CFBundleExecutable'])
print('Staged UUID-matched crash symbols:', target)
