#!/usr/bin/env python3
"""Package a reviewed publication tree with the exact engine/dependency/asset sources."""
from pathlib import Path
import argparse
import hashlib
import io
import json
import plistlib
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-tree', type=Path, required=True)
parser.add_argument('--archive', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
source = args.source_tree.resolve()
assert not subprocess.check_output(['git', '-C', str(source), 'status', '--porcelain']), 'Commit the reviewed source tree first'
revision = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
manifest = json.loads((source / 'SOURCE_MANIFEST.json').read_text())
for relative, expected in manifest.items():
    item = source / relative
    assert item.is_file() and not item.is_symlink() and source in item.resolve().parents
    assert hashlib.sha256(item.read_bytes()).hexdigest() == expected, relative

archive_info = plistlib.loads((args.archive / 'Info.plist').read_bytes())
app = args.archive / 'Products' / archive_info['ApplicationProperties']['ApplicationPath']
info = plistlib.loads((app / 'Info.plist').read_bytes())
provenance = {
    'source_revision': revision,
    'bundle_identifier': info['CFBundleIdentifier'],
    'version': info['CFBundleShortVersionString'],
    'build': info['CFBundleVersion'],
    'archived_executable_sha256': hashlib.sha256((app / info['CFBundleExecutable']).read_bytes()).hexdigest(),
    'runtime_evidence': False,
    'note': 'Source provenance, not a claim of bit-for-bit reproducibility or legal clearance.',
}
assert b'native-session.json.tmp' not in (app / info['CFBundleExecutable']).read_bytes(), 'Use the distribution archive with QA file logging disabled'
downloads = [
    'openttd-15.3-source.tar.xz', 'native-deps/xz-5.8.1.tar.xz',
    'native-deps/libarchive-3.8.10.tar.xz', 'opengfx-8.0-all.zip',
    'opensfx-1.0.3-all.zip', 'opengfx-8.0-source.tar.gz',
    'opensfx-1.0.3-source.tar.gz',
]
root = 'openttd-reimagined'
files = [(source / name, f'{root}/{name}') for name in sorted([*manifest, 'SOURCE_MANIFEST.json'])]
files += [(ROOT / 'downloads' / name, f'{root}/downloads/{name}') for name in downloads]
bundle_manifest = {name: hashlib.sha256(path.read_bytes()).hexdigest() for path, name in files}
note = f'''# Build {info['CFBundleVersion']} source package

The application source, original OpenTTD 15.3 source, XZ 5.8.1 and libarchive
3.8.10 source, plus OpenGFX 8.0 and OpenSFX 1.0.3 source and release assets
are included. Original licences, credits and build instructions remain inside
each source archive and asset package. The OpenGFX source is commit
e68bd9b7cb60305aa98c687b6836e0e0b08e2847 (official 8.0 tag); OpenSFX is
4332d7f216eece2e6417f284b00afb832126433d (official 1.0.3 tag).

Start with README.md and THIRD_PARTY.md. The pinned engine/dependency and asset
downloads are already in downloads/. Build scripts still require the documented
Apple development tools and standard build-tool installation. To edit the base
graphics or sounds, extract their *-source.tar.gz archives and follow their
upstream README. NML/grfcodec and catcodec are upstream asset build tools.
The authored scenario, GameScript, first-steps text, icon PNGs and editable
opening save are included in content/ and native/.

This is a source package, not an installable app. TestFlight/App Store status is
listed on the project page. Source availability does not by itself resolve
compatibility between all upstream licences and distribution terms.
'''
args.output.parent.mkdir(parents=True, exist_ok=True)
with tarfile.open(args.output, 'w:gz') as package:
    for path, name in files:
        package.add(path, arcname=name, recursive=False)
    for name, value in [('SOURCE_PACKAGE.md', note), ('BUILD_PROVENANCE.json', json.dumps(provenance, indent=2)+'\n'), ('SOURCE_BUNDLE_MANIFEST.json', json.dumps(bundle_manifest, indent=2)+'\n')]:
        data = value.encode(); entry = tarfile.TarInfo(f'{root}/{name}')
        entry.size = len(data); entry.mode = 0o644
        package.addfile(entry, io.BytesIO(data))
with tarfile.open(args.output) as package:
    for name, expected in bundle_manifest.items():
        assert hashlib.sha256(package.extractfile(name).read()).hexdigest() == expected, name
print(json.dumps({'path': str(args.output), 'bytes': args.output.stat().st_size,
                  'sha256': hashlib.sha256(args.output.read_bytes()).hexdigest(),
                  'source_revision': revision, 'verified_files': len(bundle_manifest)}, indent=2))
