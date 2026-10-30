// Real, scoped Simulator HID. Coordinates refer to an observed landscape screenshot.
// Usage: node script/sim_hid_drag.mjs uid pixelW pixelH shotW shotH x1 y1 x2 y2 milliseconds interfaceOrientation /path/to/serve-sim
import {readFileSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
import {createRequire} from 'node:module';
import {resolve,join} from 'node:path';
const [uid,...args]=process.argv.slice(2);
const [pixelW,pixelH,shotW,shotH,x1,y1,x2,y2,duration]=args.slice(0,9).map(Number);
if(![pixelW,pixelH,shotW,shotH,x1,y1,x2,y2,duration].every(Number.isFinite)||duration<100||duration>10000)throw Error('Invalid gesture');
for(const [x,y] of [[x1,y1],[x2,y2]])if(x<0||x>=shotW||y<0||y>=shotH)throw Error('Contact outside observed screenshot');
const devices=JSON.parse(execFileSync('xcrun',['simctl','list','devices','available','-j'],{encoding:'utf8'}));
if(!Object.values(devices.devices).flat().some(d=>d.udid===uid&&d.name.startsWith('OpenTTD ')&&d.state==='Booted'))throw Error('Use a booted project-owned OpenTTD simulator');
const orientation=Number(args[9]);
if(![3,4].includes(orientation))throw Error('Pass the observed UIInterfaceOrientation: 3 or 4');
const packageRoot=resolve(args[10]);
if(JSON.parse(readFileSync(join(packageRoot,'package.json'))).version!=='0.1.48')throw Error('Use audited serve-sim 0.1.48');
const addon=createRequire(import.meta.url)(join(packageRoot,'dist/native/serve-sim-native.node'));
const hid=new addon.SimHID(uid,join(packageRoot,'dist/simduo/serve-sim-duo-hid'));
const sleep=ms=>new Promise(done=>setTimeout(done,ms));
const point=(x,y)=>orientation===3?[1-y/shotH,x/shotW]:[y/shotH,1-x/shotW];
const send=(type,t)=>hid.touch(type,...point(x1+(x2-x1)*t,y1+(y2-y1)*t),pixelW,pixelH,0);
let progress=0;
try{
 await send('begin',0);await sleep(100);
 const steps=Math.max(10,Math.ceil(duration/35));
 for(let i=1;i<=steps;i++){progress=i/steps;await send('move',progress);await sleep(duration/steps);}
}finally{await send('end',progress);await hid.close();}
