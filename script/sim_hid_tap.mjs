// Actual HID down/up on a booted, project-owned simulator. No game commands.
// Usage: node script/sim_hid_tap.mjs uid pixelW pixelH shotW shotH x y orientation /path/to/serve-sim
import {readFileSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
import {createRequire} from 'node:module';
import {resolve,join} from 'node:path';
const [uid,...args]=process.argv.slice(2);
const [pixelW,pixelH,shotW,shotH,x,y,orientation]=args.slice(0,7).map(Number);
if(![pixelW,pixelH,shotW,shotH,x,y].every(Number.isFinite)||x<0||x>=shotW||y<0||y>=shotH||![1,2,3,4].includes(orientation))throw Error('Use observed coordinates and UIInterfaceOrientation 1/2/3/4');
const devices=JSON.parse(execFileSync('xcrun',['simctl','list','devices','available','-j'],{encoding:'utf8'}));
if(!Object.values(devices.devices).flat().some(d=>d.udid===uid&&d.name.startsWith('OpenTTD ')&&d.state==='Booted'))throw Error('Use a booted project-owned OpenTTD simulator');
const packageRoot=resolve(args[7]);
if(JSON.parse(readFileSync(join(packageRoot,'package.json'))).version!=='0.1.48')throw Error('Use audited serve-sim 0.1.48');
const addon=createRequire(import.meta.url)(join(packageRoot,'dist/native/serve-sim-native.node'));
const hid=new addon.SimHID(uid,join(packageRoot,'dist/simduo/serve-sim-duo-hid'));
const [rawX,rawY]=orientation===1?[x/shotW,y/shotH]:orientation===2?[1-x/shotW,1-y/shotH]:orientation===3?[1-y/shotH,x/shotW]:[y/shotH,1-x/shotW];
try{await hid.touch('begin',rawX,rawY,pixelW,pixelH,0);await new Promise(done=>setTimeout(done,150));}
finally{await hid.touch('end',rawX,rawY,pixelW,pixelH,0);await hid.close();}
