#!/usr/bin/env python3
"""Exercise the real shared importer with valid files and hostile archive fixtures."""
from pathlib import Path
import hashlib
import io
import json
import os
import subprocess
import tarfile
import tempfile
import zipfile
import struct
import gzip

ROOT = Path(__file__).resolve().parents[1]
BINARY = ROOT / 'build/content-import-tests/content_import_cli'
results = []

with tempfile.TemporaryDirectory(prefix='openttd-import-qa-') as temporary:
    work = Path(temporary)
    game = work / 'game'
    game.mkdir()
    (game / 'save').mkdir()
    original = game / 'save/player.sav'
    original.write_bytes(b'Existing player save must survive every failure')
    original_sha = hashlib.sha256(original.read_bytes()).hexdigest()
    sentinel = work / 'outside.grf'
    sentinel.write_bytes(b'Outside sandbox sentinel')

    def run(name, source, succeeds, options=None, contains=None):
        args = [str(BINARY), str(source), str(game)]
        if options is not None:
            args.append(json.dumps(options))
        process = subprocess.run(args, capture_output=True, text=True, timeout=30,
                                 env={**os.environ, 'ASAN_OPTIONS': 'detect_leaks=0:halt_on_error=1'})
        assert process.returncode == (0 if succeeds else 2), (name, process.returncode, process.stdout, process.stderr)
        assert 'AddressSanitizer' not in process.stderr and 'runtime error:' not in process.stderr, (name, process.stderr)
        value = json.loads(process.stdout)
        if contains:
            assert contains.lower() in value.get('error', '').lower(), (name, value)
        assert hashlib.sha256(original.read_bytes()).hexdigest() == original_sha, name
        assert sentinel.read_bytes() == b'Outside sandbox sentinel', name
        assert not list((game / '.native-imports').glob('stage-*')), name
        results.append({'test': name, 'passed': True, 'result': value})
        return value

    def zipped(name, entries, compression=zipfile.ZIP_DEFLATED):
        path = work / name
        with zipfile.ZipFile(path, 'w', compression=compression) as archive:
            for filename, data in entries:
                archive.writestr(filename, data)
        return path

    package = ROOT / 'runtime/native-save-roundtrip/content_download/newgrf/4f472b31-OpenGFX_Trains-0.3.0.tar'
    imported = run('real-community-tar', package, True)
    assert imported['kinds'] == 8 and len(imported['paths']) == 1
    with tarfile.open(package) as archive:
        actual_grf = next(item for item in archive if item.name.endswith('.grf'))
        grf = archive.extractfile(actual_grf).read()
    assert next((game / imported['paths'][0]).rglob('*.grf')).read_bytes() == grf
    raw = work / 'international-é.grf'
    raw.write_bytes(grf)
    run('raw-newgrf-unicode-filename', raw, True)
    native_save = ROOT / 'runtime/native-save-roundtrip/native-created.sav'
    raw_save = work / 'player.sav'
    raw_save.write_bytes(native_save.read_bytes())
    imported_save = run('real-save-name-collision', raw_save, True)
    assert imported_save['paths'] == ['save/player (2).sav']
    assert (game / imported_save['paths'][0]).read_bytes() == native_save.read_bytes()
    imported_zip = run('real-grf-and-save-zip', zipped('valid.zip', [('Train/ogfx.grf', grf), ('player.sav', native_save.read_bytes())]), True)
    assert imported_zip['kinds'] == 9
    run('zip-wrapped-community-tar', zipped('wrapped.zip', [('package.tar', package.read_bytes())]), True)
    gzip_package = work / 'community.tar.gz'
    gzip_package.write_bytes(gzip.compress(package.read_bytes()))
    run('real-community-tar-gzip', gzip_package, True)
    run('unicode-archive-paths', zipped('unicode.zip', [('日本語/été.grf', grf)]), True)
    for path in ['../outside.grf', '/absolute.grf', 'C:/drive.grf', '..\\outside.grf', 'folder/../../outside.grf', 'name. /track.grf']:
        run('unsafe-path-' + path, zipped('unsafe.zip', [(path, grf)]), False)
    for entries in [ [('same.grf', grf), ('same.grf', grf)],
                     [('A.grf', grf), ('a.grf', grf)],
                     [('Folder/a.grf', grf), ('folder/b.grf', grf)],
                     # Canonically equivalent directories with distinct children
                     # may be normalized by libarchive. Competing file paths
                     # must be rejected regardless of that normalization.
                     [('café/a.grf', grf), ('cafe\u0301/a.grf', grf)],
                     [('Straße/a.grf', grf), ('STRASSE/b.grf', grf)]]:
        run('duplicate-or-unicode-alias-' + repr([entry[0] for entry in entries]), zipped('collision.zip', entries), False, contains='collid' if entries[0][0] != 'same.grf' else 'duplicate')
    symlink = work / 'link.zip'
    with zipfile.ZipFile(symlink, 'w') as archive:
        entry = zipfile.ZipInfo('outside.grf')
        entry.create_system = 3
        entry.external_attr = (0o120777 << 16)
        archive.writestr(entry, '../outside.grf')
    run('zip-symlink', symlink, False, contains='links')
    for kind in [tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.CHRTYPE, tarfile.FIFOTYPE]:
        path = work / 'special.tar'
        with tarfile.open(path, 'w') as archive:
            entry = tarfile.TarInfo('link.grf')
            entry.type = kind
            entry.linkname = '../outside.grf'
            archive.addfile(entry)
        run('tar-special-entry-' + repr(kind), path, False)
    run('native-executable-extension', zipped('executable.zip', [('package/main.exe', b'MZ' + b'x' * 100), ('package/a.grf', grf)]), False, contains='executable')
    executable = work / 'hidden.grf'
    executable.write_bytes(b'\x7fELF' + b'x' * 100)
    run('disguised-native-executable', executable, False, contains='executable')
    linked_source = work / 'linked.grf'
    linked_source.symlink_to(raw)
    run('symlink-source-not-followed', linked_source, False)
    kept = game / 'newgrf-kept'
    (game / 'newgrf').rename(kept)
    escape = work / 'escape'
    escape.mkdir()
    (game / 'newgrf').symlink_to(escape, target_is_directory=True)
    try:
        run('symlink-destination-not-followed', raw, False, contains='symbolic link')
        assert not list(escape.iterdir())
    finally:
        (game / 'newgrf').unlink()
        kept.rename(game / 'newgrf')
    encrypted = zipped('encrypted.zip', [('a.grf', grf)], compression=zipfile.ZIP_STORED)
    encrypted_bytes = bytearray(encrypted.read_bytes())
    struct.pack_into('<H', encrypted_bytes, 6, struct.unpack_from('<H', encrypted_bytes, 6)[0] | 1)
    central = encrypted_bytes.index(b'PK\x01\x02')
    struct.pack_into('<H', encrypted_bytes, central + 8, struct.unpack_from('<H', encrypted_bytes, central + 8)[0] | 1)
    encrypted.write_bytes(encrypted_bytes)
    run('encrypted-zip-not-accepted', encrypted, False)
    run('archive-entry-budget', zipped('count.zip', [('a.grf', grf), ('b.grf', grf)]), False, {'entries': 1}, 'too many')
    run('compressed-input-budget', package, False, {'input': 20}, 'size limit')
    run('expanded-byte-budget', zipped('large.zip', [('a.grf', grf)]), False, {'expanded': 20}, 'size limit')
    run('zip-expansion-bomb', zipped('bomb.zip', [('a.grf', b'0' * 1024 * 1024)]), False, contains='expansion ratio')
    run('cancel-before-import', package, False, {'cancelled': True}, 'cancelled')
    nested = zipped('too-deep.zip', [('wrapped.zip', zipped('inner.zip', [('archive.tar', package.read_bytes())]).read_bytes())])
    run('nested-archive-limit', nested, False, contains='nested')
    broken = zipped('bad-crc.zip', [('a.grf', grf)], compression=zipfile.ZIP_STORED)
    data = bytearray(broken.read_bytes())
    name_len, extra_len = struct.unpack_from('<HH', data, 26)
    data[30 + name_len + extra_len + 100] ^= 255
    broken.write_bytes(data)
    run('zip-crc-failure', broken, False, contains='CRC')
    truncated = work / 'truncated.tar'
    truncated.write_bytes(package.read_bytes()[:800])
    run('truncated-tar', truncated, False)
    # The completed transaction owns only its recorded inode. Recovery must not
    # move an unrelated file that later occupied a planned destination.
    stage = game / '.native-imports/stage-Abc123'
    stage.mkdir()
    published = game / 'save/interrupted.sav'
    published.write_bytes(native_save.read_bytes())
    stat = published.stat()
    (stage / 'journal.json').write_text(json.dumps({'state': 'publishing', 'destinations': [
        {'path': 'save/interrupted.sav', 'inode': stat.st_ino, 'device': stat.st_dev},
        {'path': 'save/player.sav', 'inode': stat.st_ino + 1000, 'device': stat.st_dev}]}))
    process = subprocess.run([str(BINARY), '--recover', str(game)], capture_output=True, text=True, timeout=30)
    assert process.returncode == 0, process.stderr + process.stdout
    assert not published.exists()
    assert (game / '.native-imports/quarantine/stage-Abc123/save/interrupted.sav').read_bytes() == native_save.read_bytes()
    assert hashlib.sha256(original.read_bytes()).hexdigest() == original_sha
    results.append({'test': 'interrupted-publication-quarantine-and-original-inode-preserved', 'passed': True})

(ROOT / 'evidence/native-content-import-tests.json').write_text(json.dumps({
    'binary': str(BINARY), 'sanitizers': ['AddressSanitizer', 'UndefinedBehaviorSanitizer'],
    'passed': len(results), 'tests': results,
    'scope': 'Shared importer on macOS; native Files-picker and actual engine reload require separate simulator verification.',
}, indent=2, ensure_ascii=False))
print('Passed', len(results), 'real importer checks under ASan/UBSan')
