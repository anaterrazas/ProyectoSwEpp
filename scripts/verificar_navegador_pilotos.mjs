// Verificación con Chrome/CDP local cuando Playwright CLI no está disponible.
// Requiere Chrome headless en 127.0.0.1:9223 y el laboratorio en :8010.
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const root = process.cwd();
const out = path.join(root, 'output/playwright');
fs.mkdirSync(out, { recursive: true });
const acceso = JSON.parse(fs.readFileSync(path.join(root, 'output/experimental_pilotos/acceso_local.json'), 'utf8'));
const target = await (await fetch('http://127.0.0.1:9223/json/new?about:blank', { method: 'PUT' })).json();
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = reject; });
let secuencia = 0;
const pendientes = new Map();
ws.onmessage = ({ data }) => {
  const msg = JSON.parse(data);
  if (pendientes.has(msg.id)) {
    const { resolve, reject } = pendientes.get(msg.id); pendientes.delete(msg.id);
    msg.error ? reject(new Error(JSON.stringify(msg.error))) : resolve(msg.result);
  }
};
function cdp(method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = ++secuencia; pendientes.set(id, { resolve, reject }); ws.send(JSON.stringify({ id, method, params }));
  });
}
async function evaluar(expression) {
  const r = await cdp('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true });
  if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
  return r.result.value;
}
const pausa = ms => new Promise(r => setTimeout(r, ms));
async function abrir(url, selector) {
  await cdp('Page.navigate', { url });
  for (let i = 0; i < 100; i++) {
    await pausa(100);
    if (await evaluar(`location.href === ${JSON.stringify(url)} && document.readyState === 'complete' && !!document.querySelector(${JSON.stringify(selector)})`)) return;
  }
  throw new Error('La página no cargó: ' + url);
}
async function videos() {
  return evaluar(`(async () => {
    const resultados = [];
    for (const video of document.querySelectorAll('video')) {
      const limite = Date.now() + 15000;
      while (video.readyState < 2 && !video.error && Date.now() < limite) await new Promise(r => setTimeout(r, 100));
      if (video.readyState >= 2) {
        video.muted = true; video.currentTime = Math.min(.3, video.duration / 2);
        try { await video.play(); await new Promise(r => setTimeout(r, 400)); video.pause(); } catch {}
      }
      resultados.push({url: video.currentSrc, duracion: video.duration, readyState: video.readyState,
        tiempoReproducido: video.currentTime, error: video.error?.message || null});
    }
    return resultados;
  })()`);
}
try {
  await cdp('Network.clearBrowserCookies');
  await cdp('Page.enable');
  await cdp('Emulation.setDeviceMetricsOverride', { width: 1200, height: 1000, deviceScaleFactor: 1, mobile: false });
  await abrir(pathToFileURL(path.join(root, 'monitoreo/templates/monitoreo/piloto.html')).href, 'a');
  const plantillaDirecta = await evaluar('document.body.innerText');
  await abrir('http://127.0.0.1:8010/admin/login/?next=/monitoreo/', '#id_username');
  await evaluar(`document.querySelector('#id_username').value=${JSON.stringify(acceso.usuario)}; document.querySelector('#id_password').value=${JSON.stringify(acceso.clave)}; document.querySelector('input[type=submit]').click();`);
  for (let i = 0; i < 100; i++) { await pausa(100); if (await evaluar("location.pathname === '/monitoreo/'")) break; }
  const listado = await evaluar("({url:location.href,texto:document.body.innerText})");
  const listaVideos = await videos();
  const reporte = 'http://127.0.0.1:8010/monitoreo/piloto/1/89dea6db-38f9-40e5-a538-f9e3f7e4c471/';
  await abrir(reporte, 'video');
  const texto = await evaluar('document.body.innerText');
  const revisionVideos = await videos();
  const imagenes = await evaluar("Array.from(document.images, i => ({src:i.src,completa:i.complete,ancho:i.naturalWidth}))");
  const screenshot = await cdp('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true });
  fs.writeFileSync(path.join(out, 'monitoreo_corregido.png'), Buffer.from(screenshot.data, 'base64'));
  await abrir('http://127.0.0.1:8010/calidad/', 'video');
  const calidadVideos = await videos();
  const resultados = {metodo:'Chrome headless/CDP local; sin dependencias nuevas',
    plantillaDirectaBloqueada:plantillaDirecta.includes('plantilla Django'),
    listadoRenderizado:!listado.texto.includes('{{') && listado.url.endsWith('/monitoreo/'),
    reporteRenderizado:!texto.includes('{{') && !texto.includes('{%'),
    coberturaMostrada:texto.includes('36,45'), imagenes, listaVideos, revisionVideos, calidadVideos};
  const todos = [...listaVideos,...revisionVideos,...calidadVideos];
  resultados.todosReproducidos = todos.every(v => v.readyState >= 2 && v.duracion > 0 && v.tiempoReproducido > .3 && !v.error);
  fs.writeFileSync(path.join(out, 'monitoreo_navegador.json'), JSON.stringify(resultados, null, 2));
  console.log(JSON.stringify(resultados, null, 2));
  if (!resultados.todosReproducidos || !resultados.reporteRenderizado || !resultados.listadoRenderizado) process.exitCode = 1;
} finally { ws.close(); }
