// Real two-contact Simulator input through the Simulator Browser skill's native driver.
// Usage: node script/test_sim_pinch.mjs /path/to/serve-sim
import { readFileSync, writeFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { resolve, join } from 'node:path';
import { createRequire } from 'node:module';
const root = resolve(import.meta.dirname, '..');
const simulator = JSON.parse(readFileSync(join(root, 'evidence/ipad-simulator.json'))).simulator_id;
const container = execFileSync('xcrun', ['simctl', 'get_app_container', simulator, 'org.openttd.reimagined.dev', 'data'], { encoding: 'utf8' }).trim();
const statePath = join(container, 'Documents/OpenTTD/native-session.json');
const state = () => JSON.parse(readFileSync(statePath));
const before = state();
if (before.mode !== 'normal' || before.surface[0] < before.surface[1]) throw new Error('Open a real landscape game first');
const packageRoot = resolve(process.argv[2]);
// The argument order is documented by serve-sim/src/native.ts's SimHIDHandle.
const addon = createRequire(import.meta.url)(join(packageRoot, 'dist/native/serve-sim-native.node'));
const hid = new addon.SimHID(simulator, join(packageRoot, 'dist/simduo/serve-sim-duo-hid'));
const sleep = ms => new Promise(done => setTimeout(done, ms));
let separation = 0.05;
try {
  await hid.multiTouch('begin', 0.5 - separation, 0.45, 0.5 + separation, 0.45, 2360, 1640);
  for (let i = 1; i <= 20; i++) {
    separation = 0.05 + i * 0.006;
    await hid.multiTouch('move', 0.5 - separation, 0.45, 0.5 + separation, 0.45, 2360, 1640);
    await sleep(35);
  }
} finally {
  await hid.multiTouch('end', 0.5 - separation, 0.45, 0.5 + separation, 0.45, 2360, 1640);
  await hid.close();
}
let after;
for (let i = 0; i < 20; i++) {
  await sleep(100); after = state();
  if (after.camera[2] < before.camera[2]) break;
}
const result = { simulator, driver: 'serve-sim NativeHid two-contact API', packageVersion: JSON.parse(readFileSync(join(packageRoot, 'package.json'))).version, before, after, passed: after.camera[2] < before.camera[2], scope: 'Actual UIKit pinch recognizer and original integer zoom. Continuous fractional zoom remains unimplemented.' };
writeFileSync(join(root, 'evidence/native-pinch-test.json'), JSON.stringify(result, null, 2));
console.log(JSON.stringify({ beforeZoom: before.camera[2], afterZoom: after.camera[2], passed: result.passed }));
if (!result.passed) process.exitCode = 1;
