'use strict';
// Lienzo y transformación de coordenadas reutilizan el patrón del anotador LAB.
const $=id=>document.getElementById(id);
const data=JSON.parse($('geometria-datos').textContent),canvas=$('canvas'),ctx=canvas.getContext('2d');
let record,image,box,view,dirty=false,edited=false,drag;
const msg=s=>$('mensaje').textContent=s;
const history=id=>data.historial.filter(r=>r.case_id===id);
function changed(){dirty=true;msg('Borrador sin guardar. Ninguna coordenada fuente se ha modificado.');}
function values(){['x1','y1','x2','y2'].forEach((id,i)=>$(id).value=box[i]);}
function render(){
 if(!image?.complete||!image.naturalWidth)return;
 ctx.clearRect(0,0,canvas.width,canvas.height);ctx.drawImage(image,view.x,view.y,view.w,view.h,0,0,canvas.width,canvas.height);
 for(const [b,color] of [[record.bbox_original_xyxy,'#ffc72f'],[box,'#2fe8b1']]){ctx.strokeStyle=color;ctx.lineWidth=Math.max(2,view.w/450);ctx.strokeRect(b[0]-view.x,b[1]-view.y,b[2]-b[0],b[3]-b[1]);}
 if(drag){ctx.strokeStyle='#fff';ctx.strokeRect(drag.start[0]-view.x,drag.start[1]-view.y,drag.end[0]-drag.start[0],drag.end[1]-drag.start[1]);}
}
function resize(){canvas.style.width=$('zoom').value==='fit'?'100%':`${canvas.width*Number($('zoom').value)}px`;}
function viewport(){
 if($('vista').value==='completa')view={x:0,y:0,w:record.width,h:record.height};
 else {const [x,y,xx,yy]=record.bbox_original_xyxy,w=xx-x,h=yy-y;const left=Math.max(0,Math.floor(x-w*.3)),top=Math.max(0,Math.floor(y-h*.4));view={x:left,y:top,w:Math.min(record.width,Math.ceil(xx+w*.3))-left,h:Math.min(record.height,Math.ceil(yy+h*.45))-top};}
 canvas.width=view.w;canvas.height=view.h;resize();render();
}
function options(){const previous=record?.case_id;const allowed=data.casos.filter(r=>$('filtro').value==='TODOS'||($('filtro').value==='SIN_DECISION'?!history(r.case_id).length:r.audit_status===$('filtro').value));$('caso').replaceChildren(...allowed.map(r=>{const o=document.createElement('option');o.value=r.case_id;o.textContent=`${r.case_id} · ${r.source} · ${r.audit_status}`;return o;}));if(allowed.some(r=>r.case_id===previous))$('caso').value=previous;return allowed;}
function load(id){
 if(dirty&&!confirm('Hay cambios sin guardar. ¿Descartarlos?')){$('caso').value=record.case_id;return;}
 record=data.casos.find(r=>r.case_id===id);if(!record)return;const saved=history(id).at(-1);box=[...(saved?.bbox_xyxy||record.bbox_original_xyxy)];dirty=false;edited=!!saved&&saved.decision==='AJUSTADA';drag=null;values();
 $('caso').value=id;$('identidad').textContent=`Caso ${id} · ${record.source_sample_id} · ${record.width}×${record.height} · ${record.group_id} · SHA-256 ${record.sha256}`;
 $('auditoria').textContent=`Criba técnica: ${record.audit_status}. ${record.audit_note}`;
 $('decision').value=saved?.decision||'';$('visibilidad').value=saved?.visibilidad||'';$('justificacion').value=saved?.justificacion||'';if(!$('autor').value)$('autor').value=saved?.autor||'';$('confirmar').checked=false;
 $('original').href=`imagen/${id}/`;image=new Image();image.onload=viewport;image.onerror=()=>msg('No se pudo abrir la imagen verificada.');image.src=`imagen/${id}/`;
 $('historial').replaceChildren(...history(id).map(r=>{const div=document.createElement('div');div.className='hist-item';const text=document.createElement('p');text.textContent=`Versión ${r.revision} · ${r.decision} · ${r.autor} · ${r.fecha_utc} · ${r.justificacion} · Caja: ${JSON.stringify(r.bbox_xyxy)}`;div.append(text);return div;}));
 $('progreso').textContent=`${new Set(data.historial.map(r=>r.case_id)).size}/284 casos con decisión humana; versión global ${data.version}. Entrenamiento bloqueado.`;
 msg(saved?'Revisión persistida cargada. Guardar crea otra versión.':'Sin decisión humana guardada. La caja verde inicial es solo una copia de trabajo del original.');location.hash=`caso-${id}`;
}
function point(e){const r=canvas.getBoundingClientRect();return [view.x+(e.clientX-r.left)*canvas.width/r.width,view.y+(e.clientY-r.top)*canvas.height/r.height];}
canvas.onpointerdown=e=>{if(e.button!==0||!$('dibujar').checked)return;const p=point(e);drag={start:p,end:p};canvas.setPointerCapture(e.pointerId);};
canvas.onpointermove=e=>{if(drag){drag.end=point(e);render();}};
canvas.onpointerup=e=>{if(!drag)return;drag.end=point(e);const a=drag.start,b=drag.end;box=[Math.min(a[0],b[0]),Math.min(a[1],b[1]),Math.max(a[0],b[0]),Math.max(a[1],b[1])];drag=null;edited=true;values();changed();render();};canvas.onpointercancel=()=>{drag=null;render();};
['x1','y1','x2','y2'].forEach((id,i)=>$(id).oninput=()=>{box[i]=Number($(id).value);edited=true;changed();render();});
$('restaurar').onclick=()=>{box=[...record.bbox_original_xyxy];edited=false;values();changed();render();};
$('vista').onchange=viewport;$('zoom').onchange=resize;$('caso').onchange=()=>load(Number($('caso').value));
$('filtro').onchange=()=>{if(dirty){msg('Guarde o cambie de caso antes de filtrar.');return;}const list=options();if(list.length)load(list[0].case_id);else msg('No hay casos para este filtro.');};
['decision','visibilidad','autor','justificacion','confirmar'].forEach(id=>$(id).addEventListener('input',changed));
$('formulario').onsubmit=async e=>{
 e.preventDefault();const choice=$('decision').value;const payload={case_id:record.case_id,version:data.version,source_sha256:record.sha256,protocolo_sha256:data.protocolo_sha256,confirma_protocolo:$('confirmar').checked,decision:choice,bbox_xyxy:['CONSERVAR','AJUSTADA'].includes(choice)?box:null,visibilidad:$('visibilidad').value,autor:$('autor').value,justificacion:$('justificacion').value,edicion_humana_explicita:edited};
 try{const response=await fetch(location.pathname,{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':document.querySelector('[name=csrfmiddlewaretoken]').value},body:JSON.stringify(payload)});const r=await response.json();if(!response.ok)throw Error(r.error||'No se pudo guardar');dirty=false;location.reload();}catch(err){msg(err.message);}
};
window.onbeforeunload=e=>{if(dirty){e.preventDefault();e.returnValue='';}};
options();const initial=Number(location.hash.match(/^#caso-(\d+)$/)?.[1]||0);load(data.casos.some(r=>r.case_id===initial)?initial:0);
