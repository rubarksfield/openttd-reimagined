#!/usr/bin/env python3
"""Reject empty generic archives, stale lesson resources or development QA file logging."""
from pathlib import Path
import argparse
import json
import plistlib
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('archive', type=Path)
parser.add_argument('--bundle-identifier', required=True)
args = parser.parse_args()
archive = plistlib.loads((args.archive / 'Info.plist').read_bytes())
relative = archive.get('ApplicationProperties', {}).get('ApplicationPath')
assert relative == 'Applications/OpenTTDPad.app', 'Expected a real application archive, not a generic CMake archive'
app = args.archive / 'Products' / relative
info = plistlib.loads((app / 'Info.plist').read_bytes())
assert info['CFBundleIdentifier'] == args.bundle_identifier
assert (app / 'PrivacyInfo.xcprivacy').is_file()
assert set(info['UISupportedInterfaceOrientations~ipad']) == {
    'UIInterfaceOrientationPortrait', 'UIInterfaceOrientationPortraitUpsideDown',
    'UIInterfaceOrientationLandscapeLeft', 'UIInterfaceOrientationLandscapeRight'}, 'iPad multitasking requires all four orientations'
for local, shipped in [('content/scenario/First Route.sav', 'GameData/scenario/First Route.sav'),
                       ('content/game/TouchFirstRoute/main.nut', 'GameData/game/TouchFirstRoute/main.nut')]:
    assert (ROOT / local).read_bytes() == (app / shipped).read_bytes(), shipped
assert b'native-session.json.tmp' not in (app / info['CFBundleExecutable']).read_bytes(), 'QA file logging must be disabled'
subprocess.run(['codesign', '--verify', '--strict', str(app)], check=True)
symbols = args.archive / 'dSYMs/OpenTTDPad.app.dSYM/Contents/Resources/DWARF/OpenTTDPad'
def uuids(path):
    return set(re.findall(r'UUID: ([A-F0-9-]+)', subprocess.check_output(['xcrun', 'dwarfdump', '--uuid', str(path)], text=True)))
binary_uuids = uuids(app / info['CFBundleExecutable'])
assert binary_uuids and binary_uuids == uuids(symbols), 'Archive must contain matching crash symbols'
print(json.dumps({'application_path': relative, 'identifier': info['CFBundleIdentifier'],
                  'version': info['CFBundleShortVersionString'], 'build': info['CFBundleVersion'],
                  'current_lesson': True, 'runtime_file_logging': False, 'codesign': 'passed',
                  'ipad_orientations': 'all four', 'crash_symbols': 'UUID matched'}, indent=2))
