#!/usr/bin/env python3
"""Derive a full engine manifest from the audited upstream build, retaining all game UI."""
from pathlib import Path
import json,hashlib,tarfile,subprocess,shutil
ROOT=Path(__file__).resolve().parents[1]
subprocess.run(['python3',str(ROOT/'script/prepare_upstream.py')],check=True)
rows=json.loads((ROOT/'build/reference/compile_commands.json').read_text());files=[];excluded=[]
for row in rows:
 if 'openttd_lib.dir/' not in row['command'] or not row['file'].endswith(('.cpp','.cc','.c')):continue
 f=Path(row['file'])
 if 'generated' in f.parts:
  files.append(str(ROOT/'build/reference/generated'/f.name));continue
 rel=Path('src')/f.relative_to(next(a for a in f.parents if a.name=='src'))
 if '/os/macosx/' in str(rel) or str(rel) in ['src/os/unix/unix.cpp','src/network/core/http_curl.cpp','src/screenshot_png.cpp']:
  excluded.append(str(rel));continue
 files.append(str(ROOT/'vendor/openttd-15.3'/rel))
for name in ['8bpp_base.cpp','8bpp_simple.cpp','8bpp_optimized.cpp','32bpp_base.cpp','32bpp_simple.cpp','32bpp_optimized.cpp','32bpp_anim.cpp']:
 files.append(str(ROOT/'vendor/openttd-15.3/src/blitter'/name))
files.append(str(ROOT/'vendor/openttd-15.3/src/network/core/http_none.cpp'))
(ROOT/'build').mkdir(exist_ok=True)
(ROOT/'build/ipad-engine-sources.cmake').write_text('set(OPENTTD_ENGINE_SOURCES\n'+''.join('  "'+f+'"\n' for f in files)+')\n')
(ROOT/'evidence/ipad-source-manifest.json').write_text(json.dumps({'engine_translation_units':len(files),'excluded_platform_or_optional_units':excluded,'added':'original CPU blitters and upstream no-HTTP backend','gameplay_sources_modified':False},indent=2))
archive=ROOT/'downloads/native-deps/xz-5.8.1.tar.xz'
archive.parent.mkdir(parents=True,exist_ok=True)
url='https://github.com/tukaani-project/xz/releases/download/v5.8.1/xz-5.8.1.tar.xz'
sha='0b54f79df85912504de0b14aec7971e3f964491af1812d83447005807513cd9e'
if not archive.exists():subprocess.run(['curl','-fL','--max-time','60',url,'-o',str(archive)],check=True)
actual=hashlib.sha256(archive.read_bytes()).hexdigest()
if actual!=sha:raise RuntimeError('XZ source checksum mismatch')
if not (ROOT/'vendor/native-deps/xz-5.8.1/CMakeLists.txt').exists():
 with tarfile.open(archive) as package:package.extractall(ROOT/'vendor/native-deps',filter='data')
(ROOT/'evidence/native-dependency-xz.json').write_text(json.dumps({'url':'https://github.com/tukaani-project/xz/releases/download/v5.8.1/xz-5.8.1.tar.xz','sha256':actual,'version':'5.8.1','build':'static, target SDK; no host library linkage'},indent=2))
resources=ROOT/'build/ipad-resources';resources.mkdir(exist_ok=True)
shutil.copytree(ROOT/'build/reference/baseset',resources/'baseset',dirs_exist_ok=True)
shutil.copy2(ROOT/'runtime/reference/baseset/opengfx-8.0.tar',resources/'baseset/opengfx-8.0.tar')
classic=ROOT/'native/apple/ClassicMenu/classic-menu.dat'
if hashlib.sha256(classic.read_bytes()).hexdigest()!='1645d6bd627df06986b1884c57f1e328f3ab606aa32549ed88a9220b1b1230fa':raise RuntimeError('Classic menu checksum mismatch')
shutil.copy2(classic,resources/'baseset/classic-menu.dat')
(resources/'lang').mkdir(exist_ok=True);shutil.copy2(ROOT/'build/reference/lang/english.lng',resources/'lang/english.lng')
for name in ['ai','game']:shutil.copytree(ROOT/'vendor/openttd-15.3/bin'/name,resources/name,dirs_exist_ok=True)
shutil.copytree(ROOT/'content/game/TouchFirstRoute',resources/'game/TouchFirstRoute',dirs_exist_ok=True)
lesson=ROOT/'content/scenario/First Route.sav'
if not lesson.exists():raise RuntimeError('Prepare and verify the real first-route training save before packaging')
(resources/'scenario').mkdir(exist_ok=True);shutil.copy2(lesson,resources/'scenario/First Route.sav')
shutil.copy2(ROOT/'vendor/openttd-15.3/COPYING.md',resources/'COPYING-OpenTTD.md')
for name in ['README.md','changelog.md','known-bugs.md','COPYING.md']:shutil.copy2(ROOT/'vendor/openttd-15.3'/name,resources/name)
(resources/'docs').mkdir(exist_ok=True)
shutil.copy2(ROOT/'vendor/openttd-15.3/docs/fonts.md',resources/'docs/fonts.md')
subprocess.run(['python3',str(ROOT/'script/prepare_sound.py')],check=True)
subprocess.run(['python3',str(ROOT/'script/prepare_archive.py')],check=True)
(resources/'licenses').mkdir(exist_ok=True)
shutil.copy2(ROOT/'vendor/native-deps/libarchive-3.8.10/COPYING',resources/'licenses/libarchive-COPYING.txt')
print('Full engine units:',len(files),'Resources:',resources)
