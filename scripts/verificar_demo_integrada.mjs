// Chrome/CDP local: reutiliza el mecanismo de verificar_navegador_pilotos.mjs.
// Solo lee resultados; no analiza videos ni registra revisiones humanas.
import fs from 'node:fs';
const out = 'output/demo_integrada_v002';
const acceso = JSON.parse(fs.readFileSync('output/experimental_pilotos/acceso_local.json', 'utf8'));
const target = await (await fetch('http://127.0.0.1:9223/json/new?about:blank', {method:'PUT'})).json();
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=reject});
let id=0;const pendientes=new Map();
ws.onmessage=({data})=>{const r=JSON.parse(data);if(pendientes.has(r.id)){const p=pendientes.get(r.id);pendientes.delete(r.id);r.error?p.reject(new Error(JSON.stringify(r.error))):p.resolve(r.result)}};
function cdp(method,params={}){return new Promise((resolve,reject)=>{const n=++id;pendientes.set(n,{resolve,reject});ws.send(JSON.stringify({id:n,method,params}))})}
async function evaluar(expression){const r=await cdp('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(r.exceptionDetails)throw new Error(JSON.stringify(r.exceptionDetails));return r.result.value}
const pausa=ms=>new Promise(r=>setTimeout(r,ms));
async function abrir(path,selector='main'){
 await cdp('Page.navigate',{url:'http://127.0.0.1:8010'+path});
 for(let n=0;n<100;n++){await pausa(100);if(await evaluar(`location.pathname===${JSON.stringify(path.split('?')[0])}&&document.readyState==='complete'&&!!document.querySelector(${JSON.stringify(selector)})`))return}
 throw new Error('No cargó '+path);
}
async function captura(nombre){const s=await cdp('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});fs.writeFileSync(`${out}/${nombre}.png`,Buffer.from(s.data,'base64'))}
async function reproducir(){return evaluar(`(async()=>{const rows=[];for(const v of document.querySelectorAll('video')){v.preload='auto';v.load();const fin=Date.now()+12000;while(v.readyState<2&&!v.error&&Date.now()<fin)await new Promise(r=>setTimeout(r,100));v.muted=true;try{await v.play();await new Promise(r=>setTimeout(r,300));v.pause()}catch(e){}rows.push({url:v.getAttribute('src'),duracion:v.duration,tiempo:v.currentTime,error:v.error?.message||null})}return rows})()`)}
const resultado={paginas:[],videos:[],galerias:[],movil:[]};
try{
 await cdp('Network.clearBrowserCookies');
 await cdp('Page.enable');await cdp('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
 await abrir('/admin/login/?next=/', '#id_username').catch(async()=>{await abrir('/admin/login/','#id_username')});
 await evaluar(`document.querySelector('#id_username').value=${JSON.stringify(acceso.usuario)};document.querySelector('#id_password').value=${JSON.stringify(acceso.clave)};document.querySelector('input[type=submit]').click()`);
 await pausa(1000);
 for(const [path,nombre] of [['/','inicio'],['/demo/epp/','epp'],['/demo/calidad/','calidad'],['/demo/historial/','historial'],['/monitoreo/','monitoreo'],['/calidad/','visor_calidad']]){
  await abrir(path,path==='/calidad/'?'video':path==='/monitoreo/'?'h2':'main');
  const check=await evaluar(`({ruta:location.pathname,titulo:document.title,ancho:innerWidth,contenido:document.documentElement.scrollWidth,plantillas:/\{\{|\{%/.test(document.body.innerText),enlaces:[...document.querySelectorAll('main a')].map(a=>a.getAttribute('href'))})`);
  resultado.paginas.push(check);await captura(nombre);
  if(path==='/demo/epp/'||path==='/demo/calidad/')resultado.videos.push({pagina:path,videos:await reproducir()});
 }
 for(const rel of ['comparacion_videos_epp_v002_001','evaluacion_epp33_v002_001','auditoria_errores_epp33_v002_001','evaluacion_deteccion_v002_001']){
  const path='/artefactos/output/experimental_pilotos/'+rel+'/index.html';await abrir(path,'article');
  const check=await evaluar(`(async()=>{for(const i of document.images)i.loading='eager';const fin=Date.now()+20000;while([...document.images].some(i=>!i.complete)&&Date.now()<fin)await new Promise(r=>setTimeout(r,100));return {ruta:location.pathname,imagenes:document.images.length,rotas:[...document.images].filter(i=>!i.naturalWidth).map(i=>i.getAttribute('src')),casos:document.querySelectorAll('article').length}})()`);
  if(rel==='auditoria_errores_epp33_v002_001')check.filtro=await evaluar(`(()=>{const s=document.querySelector('select');s.value='CASCO';s.dispatchEvent(new Event('change'));return {seleccion:s.value,visibles:[...document.querySelectorAll('article')].filter(a=>!a.hidden).length}})()`);
  resultado.galerias.push(check);
 }
 await cdp('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
 for(const [path,nombre] of [['/','inicio_movil'],['/demo/epp/','epp_movil'],['/demo/calidad/','calidad_movil'],['/demo/historial/','historial_movil']]){
  await abrir(path);resultado.movil.push(await evaluar(`({ruta:location.pathname,ancho:innerWidth,contenido:document.documentElement.scrollWidth})`));await captura(nombre);
 }
 resultado.ok=resultado.paginas.every(p=>!p.plantillas)&&resultado.galerias.every(g=>g.rotas.length===0&&(!g.filtro||g.filtro.visibles===20))&&resultado.videos.every(g=>g.videos.every(v=>!v.error&&v.duracion>0&&v.tiempo>0))&&resultado.movil.every(p=>p.contenido<=p.ancho);
 fs.writeFileSync(`${out}/verificacion_chrome.json`,JSON.stringify(resultado,null,2));
 console.log(JSON.stringify({ok:resultado.ok,paginas:resultado.paginas.length,videos:resultado.videos,galerias:resultado.galerias.map(g=>({...g,rotas:g.rotas.length})),movil:resultado.movil}));
 if(!resultado.ok)process.exitCode=1;
}finally{ws.close()}
