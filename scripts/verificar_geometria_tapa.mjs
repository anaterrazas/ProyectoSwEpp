// Verificación Chrome/CDP aislada. No guarda decisiones ni cajas de prueba.
import fs from 'node:fs';
const out='output/fase210_geometria_tapa_v003_001';
const b=await(await fetch('http://127.0.0.1:9223/json/version')).json();
const ws=new WebSocket(b.webSocketDebuggerUrl);await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j;});
let id=0,session,context;const pending=new Map();
ws.onmessage=({data})=>{const r=JSON.parse(data),p=pending.get(r.id);if(p){pending.delete(r.id);r.error?p.reject(Error(r.error.message)):p.resolve(r.result);}};
function call(method,params={},sid){return new Promise((resolve,reject)=>{const n=++id;pending.set(n,{resolve,reject});ws.send(JSON.stringify({id:n,method,params,...(sid?{sessionId:sid}:{})}));});}
async function evaluate(expression){const r=await call('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true},session);if(r.exceptionDetails)throw Error('Falló la comprobación de interfaz');return r.result.value;}
const pause=ms=>new Promise(r=>setTimeout(r,ms));
async function open(path,selector){await call('Page.navigate',{url:'http://127.0.0.1:8010'+path},session);for(let k=0;k<100;k++){await pause(100);if(await evaluate(`document.readyState==='complete'&&!!document.querySelector(${JSON.stringify(selector)})`))return;}throw Error('No cargó '+path);}
async function screenshot(n){const r=await call('Page.captureScreenshot',{format:'png'},session);fs.writeFileSync(`${out}/${n}.png`,Buffer.from(r.data,'base64'));}
try{
 const targets=(await call('Target.getTargets')).targetInfos;const local=targets.find(t=>t.type==='page'&&t.url.startsWith('http://127.0.0.1:8010/'));if(!local)throw Error('Sin sesión de laboratorio en Chrome');
 const s=(await call('Target.attachToTarget',{targetId:local.targetId,flatten:true})).sessionId;
 const cookies=(await call('Network.getCookies',{urls:['http://127.0.0.1:8010/']},s)).cookies;await call('Target.detachFromTarget',{sessionId:s});
 context=(await call('Target.createBrowserContext')).browserContextId;
 await call('Storage.setCookies',{browserContextId:context,cookies:cookies.map(c=>({name:c.name,value:c.value,domain:c.domain,path:c.path,secure:c.secure,httpOnly:c.httpOnly,sameSite:c.sameSite}))});
 const target=await call('Target.createTarget',{url:'about:blank',browserContextId:context});session=(await call('Target.attachToTarget',{targetId:target.targetId,flatten:true})).sessionId;
 await call('Page.enable',{},session);await call('Emulation.setDeviceMetricsOverride',{width:1440,height:1050,deviceScaleFactor:1,mobile:false},session);
 await open('/demo/calidad/tapa-geometria/','#geometria-datos');
 for(let k=0;k<80;k++){await pause(100);if(await evaluate(`!!document.querySelector('#caso option')&&!!image?.naturalWidth`))break;}
 const cases=[];
 for(const n of [0,54,147,224,238,271,272,283]){
  await evaluate(`load(${n})`);
  cases.push(await evaluate(`(async()=>{const end=Date.now()+5000;while(!image.naturalWidth&&Date.now()<end)await new Promise(r=>setTimeout(r,50));return {case:record.case_id,loaded:!!image.naturalWidth,originalUnchanged:JSON.stringify(box)===JSON.stringify(record.bbox_original_xyxy)}})()`));
 }
 await evaluate(`load(0)`);await pause(100);await screenshot('geometria_escritorio');
 const status=await evaluate(`(async()=>{const bad={case_id:0,version:data.version,source_sha256:record.sha256,protocolo_sha256:data.protocolo_sha256,confirma_protocolo:true,decision:'AJUSTADA',bbox_xyxy:[-1,0,100,100],visibilidad:'TOTAL',autor:'FIXTURE_INVALIDO_NO_GUARDAR',justificacion:'Solicitud inválida que debe ser rechazada',edicion_humana_explicita:true};return {js:(await fetch('/static/laboratorio/geometria_tapa.js')).status,image:(await fetch('imagen/0/')).status,outside:(await fetch('imagen/999/')).status,missingCsrf:(await fetch(location.pathname,{method:'POST',body:'{}'})).status,badGeometry:(await fetch(location.pathname,{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':document.querySelector('[name=csrfmiddlewaretoken]').value},body:JSON.stringify(bad)})).status}})()`);
 await evaluate(`canvas.scrollIntoView({block:'start'});$('dibujar').checked=true`);
 const rect=await evaluate(`canvas.getBoundingClientRect().toJSON()`);const x=rect.x+rect.width*.3,y=rect.y+Math.min(rect.height*.3,200);
 await call('Input.dispatchMouseEvent',{type:'mousePressed',x,y,button:'left',buttons:1,clickCount:1},session);
 await call('Input.dispatchMouseEvent',{type:'mouseMoved',x:x+40,y:y+40,button:'none',buttons:1},session);
 await call('Input.dispatchMouseEvent',{type:'mouseReleased',x:x+40,y:y+40,button:'left',buttons:0,clickCount:1},session);
 const draw=await evaluate(`({edited,dirty,changed:JSON.stringify(box)!==JSON.stringify(record.bbox_original_xyxy)})`);
 await evaluate(`dirty=false;load(0)`);
 await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true},session);await pause(100);
 const mobile=await evaluate(`({viewport:innerWidth,content:document.documentElement.scrollWidth,client:document.documentElement.clientWidth})`);await screenshot('geometria_movil');
 const result={method:'Chrome/CDP existente; no decisiones humanas de prueba persistidas',cases,status,draw,mobile,decisionesPruebaGuardadas:0};
 result.ok=cases.every(r=>r.loaded&&r.originalUnchanged)&&status.js===200&&status.image===200&&status.outside===404&&status.missingCsrf===403&&status.badGeometry===400&&draw.edited&&draw.changed&&mobile.content<=mobile.client;
 fs.writeFileSync(`${out}/verificacion_chrome.json`,JSON.stringify(result,null,2));console.log(JSON.stringify(result));if(!result.ok)process.exitCode=1;
}finally{if(context)await call('Target.disposeBrowserContext',{browserContextId:context});ws.close();}
