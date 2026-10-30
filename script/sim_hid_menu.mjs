// GPL-2.0. Real press-drag-release through a currently observed original menu.
import {readFileSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
import {createRequire} from 'node:module';
import {join,resolve} from 'node:path';
const [uid,statePath,widgetID,wanted,packageRoot]=process.argv.slice(2);
const root=resolve(packageRoot),devices=JSON.parse(execFileSync('xcrun',['simctl','list','devices','available','-j'],{encoding:'utf8'}));
if(!Object.values(devices.devices).flat().some(d=>d.udid===uid&&d.name.startsWith('OpenTTD ')&&d.state==='Booted'))throw Error('Owned simulator required');
if(JSON.parse(readFileSync(join(root,'package.json'))).version!=='0.1.48')throw Error('Audited driver required');
const get=()=>JSON.parse(readFileSync(statePath));const plain=s=>s.replace(/[\ue000-\uf8ff]/g,'');
const s=get(),w=s.widgets.find(w=>w.id===widgetID);if(s.suspended||!w||w.disabled)throw Error('Observe an enabled original widget');
const addon=createRequire(import.meta.url)(join(root,'dist/native/serve-sim-native.node')),hid=new addon.SimHID(uid,join(root,'dist/simduo/serve-sim-duo-hid'));
// This helper is scoped to the owned landscape iPad fixture, orientation 4.
const send=(kind,x,y)=>hid.touch(kind,y/820,1-x/1180,2360,1640,0);
const sleep=ms=>new Promise(r=>setTimeout(r,ms));let end=[w.x+w.w/2,w.y+w.h/2];
try{
 await send('begin',...end);await sleep(120);await send('move',end[0],end[1]+12);await sleep(450);
 const rows=get().widgets.filter(w=>w.id.startsWith('ottd.dropdown.'));console.log(JSON.stringify(rows.map(w=>({id:w.id,label:plain(w.label),x:w.x,y:w.y,w:w.w,h:w.h}))));
 const row=rows.find(w=>plain(w.label)===wanted);if(!row)throw Error('Requested menu item not visible');
 end=[row.x+row.w/2,row.y+row.h/2];await send('move',...end);await sleep(100);
}finally{await send('end',...end);await hid.close();}
