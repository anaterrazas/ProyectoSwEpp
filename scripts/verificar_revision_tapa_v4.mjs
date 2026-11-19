// Reutiliza Chrome/CDP local del laboratorio. No guarda decisiones humanas.
import fs from 'node:fs';
const out='output/fase26_tapa_v002_001';
const browser=await (await fetch('http://127.0.0.1:9223/json/version')).json();
const ws=new WebSocket(browser.webSocketDebuggerUrl);
await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=reject;});
let seq=0;const waiting=new Map();
ws.onmessage=({data})=>{const r=JSON.parse(data);const p=waiting.get(r.id);if(p){waiting.delete(r.id);r.error?p.reject(Error(r.error.message)):p.resolve(r.result);}};
function command(method,params={},sessionId){return new Promise((resolve,reject)=>{const id=++seq;waiting.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params,...(sessionId?{sessionId}:{})}));});}
let context,session;const errors=[];
const pause=ms=>new Promise(r=>setTimeout(r,ms));
async function evaluate(expression){const r=await command('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true},session);if(r.exceptionDetails)throw Error('Falló una comprobación de página');return r.result.value;}
async function open(path,selector){await command('Page.navigate',{url:'http://127.0.0.1:8010'+path},session);for(let i=0;i<100;i++){await pause(100);if(await evaluate(`document.readyState==='complete'&&!!document.querySelector(${JSON.stringify(selector)})`))return;}throw Error('No cargó '+path);}
async function capture(name){const r=await command('Page.captureScreenshot',{format:'png'},session);fs.writeFileSync(`${out}/${name}.png`,Buffer.from(r.data,'base64'));}
try{
 const targets=(await command('Target.getTargets')).targetInfos;
 const existing=targets.find(t=>t.type==='page'&&t.url.startsWith('http://127.0.0.1:8010/'));
 if(!existing)throw Error('No hay sesión local de Chrome para comprobar la revisión');
 const existingSession=(await command('Target.attachToTarget',{targetId:existing.targetId,flatten:true})).sessionId;
 const localCookies=(await command('Network.getCookies',{urls:['http://127.0.0.1:8010/']},existingSession)).cookies;
 await command('Target.detachFromTarget',{sessionId:existingSession});
 context=(await command('Target.createBrowserContext')).browserContextId;
 await command('Storage.setCookies',{browserContextId:context,cookies:localCookies.map(c=>({name:c.name,value:c.value,domain:c.domain,path:c.path,secure:c.secure,httpOnly:c.httpOnly,sameSite:c.sameSite}))});
 const target=await command('Target.createTarget',{url:'about:blank',browserContextId:context});
 session=(await command('Target.attachToTarget',{targetId:target.targetId,flatten:true})).sessionId;
 await command('Page.enable',{},session);
 await command('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false},session);
 await open('/demo/calidad/tapa-v4/','#revision-datos');
 for(let i=0;i<100;i++){await pause(100);if(await evaluate(`location.pathname==='/demo/calidad/tapa-v4/'&&!!document.querySelector('#revision-datos')`))break;}
 if(!await evaluate(`!!document.querySelector('#revision-datos')`))throw Error('La cuenta local no pudo abrir la revisión');
 for(let i=0;i<100;i++){await pause(100);if(await evaluate(`document.querySelectorAll('#conflictos button').length===7&&document.querySelector('#lienzo').width>1`))break;}
 const images=[];
 for(const imageId of [9,38,60,165,42,95,223,24]){
  await evaluate(`navigate(${imageId})`);
  const ready=await evaluate(`(async()=>{const end=Date.now()+6000;while((!image.complete||!image.naturalWidth)&&Date.now()<end)await new Promise(r=>setTimeout(r,50));return {id:current.image_id,loaded:!!image.naturalWidth,width:canvas.width,height:canvas.height,originalBoxes:current.source_annotations_cap.length}})()`);
  images.push(ready);
 }
 await capture('revision_escritorio');
 const resources=await evaluate(`(async()=>{const js=await fetch('/static/laboratorio/revision_tapa_v4.js');const a=await fetch('imagen/24/original/');const c=await fetch('imagen/24/contexto/');const csrf=await fetch(location.pathname,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});const unknown=await fetch('imagen/999/original/');return {js:js.status,original:a.status,context:c.status,csrfMissing:csrf.status,unknown:unknown.status}})()`);
 // Probar dibujo real sin enviar formulario ni persistir referencias ficticias.
 await evaluate(`canvas.scrollIntoView({block:'start'})`);
 const before=await evaluate(`({count:additions.length,box:canvas.getBoundingClientRect().toJSON()})`);
 await evaluate(`$('dibujar').checked=true`);
 const x=before.box.x+before.box.width*.25,y=before.box.y+before.box.height*.25;
 for(const [type,px,py,button,buttons] of [['mousePressed',x,y,'left',1],['mouseMoved',x+30,y+20,'none',1],['mouseReleased',x+30,y+20,'left',0]]){
  await command('Input.dispatchMouseEvent',{type,x:px,y:py,button,buttons,clickCount:1},session);
 }
 const draw=await evaluate(`({added:additions.length-${before.count},classUnselected:additions.at(-1)?.clase==='',dirty,version:state.estado.revision_global})`);
 // Descartar solo el borrador local creado para verificar el lienzo.
 await evaluate(`dirty=false; navigate(24)`);
 await command('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true},session);
 await pause(200);const mobile=await evaluate(`({viewport:innerWidth,content:document.documentElement.scrollWidth})`);await capture('revision_movil');
 const checks=await evaluate(`({conflictButtons:document.querySelectorAll('#conflictos button').length,imagesInSelector:document.querySelector('#imagen-selector').options.length,rawTemplate:/\{\{|\{%/.test(document.body.innerText),absolutePath:document.body.innerText.includes('C:\\Users\\Usuario'),newHumanVersions:state.estado.revision_global})`);
 const result={method:'Chrome/CDP: CLI Playwright no disponible en caché local',images,resources,draw,mobile,checks,humanDecisionsSubmitted:0,errors};
 result.ok=images.every(i=>i.loaded)&&resources.js===200&&resources.original===200&&resources.context===200&&resources.csrfMissing===403&&resources.unknown===404&&draw.added===1&&draw.classUnselected&&mobile.content<=mobile.viewport&&checks.conflictButtons===7&&checks.imagesInSelector===262&&!checks.rawTemplate&&!checks.absolutePath;
 fs.writeFileSync(`${out}/verificacion_chrome.json`,JSON.stringify(result,null,2));console.log(JSON.stringify(result));if(!result.ok)process.exitCode=1;
}finally{if(context)await command('Target.disposeBrowserContext',{browserContextId:context});ws.close();}
