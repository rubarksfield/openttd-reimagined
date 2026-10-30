#!/usr/bin/env python3
"""Check real native audio telemetry and a captured original mixer buffer.

Run after interacting with the actual app, not as a synthetic tone test.
Optional --pid verifies that the diagnostic WAV belongs to the current process.
"""
import argparse
import datetime
import hashlib
import json
import math
from pathlib import Path
import shutil
import struct
import subprocess
import wave

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--pid', type=int)
args = parser.parse_args()
uid = json.loads((ROOT / 'evidence/ipad-simulator.json').read_text())['simulator_id']
container = Path(subprocess.check_output([
    'xcrun', 'simctl', 'get_app_container', uid, 'org.openttd.reimagined.dev', 'data'
], text=True).strip()) / 'Documents/OpenTTD'
state = json.loads((container / 'native-session.json').read_text())
audio = state['audio']
assert state['sound_set'] == 'OpenSFX', state.get('sound_set')
assert audio['available'] and audio['running'] and not audio['background']
assert not audio['interrupted'] and audio['last_error'] == 0, audio
assert audio['callbacks'] > 0 and audio['non_silent_buffers'] > 0 and audio['peak'] > 0
source = container / 'native-first-sound.wav'
if args.pid is not None:
    started = subprocess.check_output(['ps', '-p', str(args.pid), '-o', 'lstart='], text=True).strip()
    started_epoch = datetime.datetime.strptime(started, '%a %b %d %H:%M:%S %Y').timestamp()
    assert source.stat().st_mtime >= started_epoch, 'Stale PCM capture from an earlier process'
with wave.open(str(source)) as reader:
    channels = reader.getnchannels()
    rate = reader.getframerate()
    frames = reader.getnframes()
    width = reader.getsampwidth()
    raw = reader.readframes(frames)
samples = struct.unpack('<' + 'h' * (len(raw) // 2), raw)
peak = max(abs(s) for s in samples)
assert channels == 2 and rate == 44100 and frames == 1024 and width == 2 and peak > 0
shutil.copy2(source, ROOT / 'evidence/native-original-sound.wav')
record = {
    'passed': True, 'process_id': args.pid, 'audio': audio,
    'channels': channels, 'sample_rate': rate, 'sample_width': width,
    'captured_frames': frames, 'captured_peak': peak,
    'captured_rms': math.sqrt(sum(s * s for s in samples) / len(samples)),
    'captured_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
    'scope': 'Real original OpenTTD mixer PCM and native AudioQueue callback progress. '
             'Does not establish hardware-speaker audibility or real phone-call/Bluetooth behaviour.',
}
(ROOT / 'evidence/native-sound-pcm-check.json').write_text(json.dumps(record, indent=2))
print(json.dumps(record, indent=2))
