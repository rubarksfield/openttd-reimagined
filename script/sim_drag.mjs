// Scoped, real HID drag on the owned iPad fixture (interface orientation 4). No game commands.
// Usage: node script/sim_drag.mjs x1 y1 x2 y2 milliseconds /path/to/serve-sim
// Coordinates are from an observed 800 x 556 simulator screenshot.
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { resolve, join } from 'node:path';
const root = resolve(import.meta.dirname, '..');
const [x1,y1,x2,y2,duration=900] = process.argv.slice(2,7).map(Number);
if (![x1,y1,x2,y2,duration].every(Number.isFinite) || duration < 100 || duration > 10000 ||
    [x1,x2].some(x => x < 0 || x >= 800) || [y1,y2].some(y => y < 0 || y >= 556)) throw new Error('Invalid observed screenshot drag');
const simulator = JSON.parse(readFileSync(join(root,'evidence/ipad-simulator.json'))).simulator_id;
const driverRoot = process.argv[7] || process.env.SERVE_SIM_PACKAGE;
if(!driverRoot)throw new Error('Pass the pinned serve-sim package directory or set SERVE_SIM_PACKAGE');
const packageRoot = resolve(driverRoot);
if(JSON.parse(readFileSync(join(packageRoot,'package.json'))).version !== '0.1.48')throw new Error('Use the audited serve-sim 0.1.48 driver');
const addon = createRequire(import.meta.url)(join(packageRoot,'dist/native/serve-sim-native.node'));
const hid = new addon.SimHID(simulator,join(packageRoot,'dist/simduo/serve-sim-duo-hid'));
const sleep = ms => new Promise(done => setTimeout(done,ms));
const send = (type,x,y) => hid.touch(type,y/556,1-x/800,2360,1640,0);
try {
 await send('begin',x1,y1);
 await sleep(100);
 const steps = Math.max(10,Math.ceil(duration/35));
 for(let step=1;step<=steps;step++){
  await send('move',x1+(x2-x1)*step/steps,y1+(y2-y1)*step/steps);
  await sleep(duration/steps);
 }
} finally {
 await send('end',x2,y2);
 await hid.close();
}
