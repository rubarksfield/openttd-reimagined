#!/usr/bin/env python3
"""Verify all pinned source bytes, allowing exactly the reviewed mobile patch series."""
from pathlib import Path
import argparse,hashlib,subprocess,tarfile,json,shutil,tempfile,re
ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/'downloads/openttd-15.3-source.tar.xz'
SHA256='5ea21eea7d59c78a42071924ac18c6bc0116088f2e96b14cfee9369175973be7'
parser=argparse.ArgumentParser();parser.add_argument('--reference',action='store_true');args=parser.parse_args()
ARCHIVE.parent.mkdir(exist_ok=True)
if not ARCHIVE.exists():
 cached=ROOT.parent/'openttd-investigation/downloads/openttd-15.3-source.tar.xz'
 if cached.exists():shutil.copy2(cached,ARCHIVE)
 else:subprocess.run(['curl','-fL','--max-time','60','https://cdn.openttd.org/openttd-releases/15.3/openttd-15.3-source.tar.xz','-o',str(ARCHIVE)],check=True)
if hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()!=SHA256:raise RuntimeError('Unverified source archive')
original=ROOT.parent/'openttd-investigation/source/openttd-15.3'
DEST=(original if original.exists() else ROOT/'vendor/openttd-reference') if args.reference else ROOT/'vendor/openttd-15.3'
mobile=not args.reference
patches=sorted((ROOT/'patches').glob('*.patch')) if mobile else []
with tarfile.open(ARCHIVE) as archive:
 expected={Path(m.name).relative_to('openttd-15.3'):archive.extractfile(m).read() for m in archive if m.isfile()}
# Reconstruct expected changes independently from the pinned archive and patch files.
changed=set()
for patch in patches:
 for name in re.findall(r'^--- a/(.+)$',patch.read_text(),re.M):
  rel=Path(name)
  if rel not in expected or '..' in rel.parts:raise RuntimeError('Patch modifies an unknown archive path')
  changed.add(rel)
with tempfile.TemporaryDirectory() as temp:
 stage=Path(temp)
 for rel in changed:
  (stage/rel).parent.mkdir(parents=True,exist_ok=True);(stage/rel).write_bytes(expected[rel])
 for patch in patches:subprocess.run(['patch','--batch','--fuzz=0','-p1','-i',str(patch)],cwd=stage,check=True,stdout=subprocess.DEVNULL)
 for rel in changed:expected[rel]=(stage/rel).read_bytes()
if not DEST.exists():
 DEST.parent.mkdir(exist_ok=True)
 with tempfile.TemporaryDirectory(dir=DEST.parent) as temp:
  with tarfile.open(ARCHIVE) as archive:archive.extractall(temp,filter='data')
  shutil.move(str(Path(temp)/'openttd-15.3'),DEST)
 for patch in patches:subprocess.run(['patch','--batch','--fuzz=0','-p1','-i',str(patch)],cwd=DEST,check=True,stdout=subprocess.DEVNULL)
for rel,data in expected.items():
 if (DEST/rel).read_bytes()!=data:raise RuntimeError(f'Engine tree changed unexpectedly: {rel}')
extra={f.relative_to(DEST) for f in DEST.rglob('*') if f.is_file()}-set(expected)
if extra:raise RuntimeError(f'Unexpected engine files: {sorted(map(str,extra))}')
(ROOT/'evidence').mkdir(exist_ok=True)
record={'archive_sha256':SHA256,'source':str(DEST),'files_verified':len(expected),'extra_files':0,'allowed_changes':sorted(map(str,changed)),'patches':[{'file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in patches],'result':'passed'}
(ROOT/'evidence'/('upstream-tree-verification-'+('mobile' if mobile else 'reference')+'.json')).write_text(json.dumps(record,indent=2))
print(DEST)
