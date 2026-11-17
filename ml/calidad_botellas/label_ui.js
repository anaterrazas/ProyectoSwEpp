'use strict';
const el=id=>document.getElementById(id);
let state=null,selected=null,dirty=false,saving=false;
const defects=['RAYADURA','DEFORMACION','TAPA_DEFECTUOSA'];
// Respaldo para servidores que todavía no se han reiniciado; sin valores de etiquetas por defecto.
const reviewFields=[{control:'body',label:'Evaluabilidad del cuerpo'},{control:'cap',label:'Evaluabilidad de la tapa'},{control:'other',label:'Otros defectos visibles fuera de taxonomía'},{control:'CONFORME',label:'Conclusión CONFORME'},{control:'NO_EVALUABLE',label:'Conclusión NO_EVALUABLE'}];
for(const id of ['body','cap','other','CONFORME','NO_EVALUABLE',...defects]){
  const values=defects.includes(id)?[['','Desconocido'],['1','Presente'],['0','Ausente']]:[['','Desconocido'],['true','Sí'],['false','No']];
  for(const [value,text] of values){const option=document.createElement('option');option.value=value;option.textContent=text;el(id).append(option);}
}
const readTri=id=>el(id).value===''?null:el(id).value==='true';
const setTri=(id,value)=>{el(id).value=value==null?'':String(value);};
function values(){return {labels:Object.fromEntries(defects.map(id=>[id,el(id).value===''?null:Number(el(id).value)])),evaluable:{body:readTri('body'),cap:readTri('cap')},other_defect:readTri('other'),categories:{CONFORME:readTri('CONFORME'),NO_EVALUABLE:readTri('NO_EVALUABLE')},notes:el('notes').value};}
function message(text){el('message').textContent=text;}
function updateReadiness(){
  const missing=reviewFields.filter(field=>el(field.control).value==='');
  el('review-missing').replaceChildren();
  for(const field of reviewFields){el(field.control).classList.toggle('needs-decision',missing.includes(field));el(field.control).removeAttribute('aria-invalid');}
  for(const field of missing){const li=document.createElement('li');const button=document.createElement('button');button.type='button';button.textContent=field.label+' — sin decidir';button.onclick=()=>el(field.control).focus();li.append(button);el('review-missing').append(li);}
  el('review-summary').textContent=missing.length?`${missing.length} campo(s) sin decidir. Complete los señalados y guarde el borrador.`:'Los cinco campos requeridos tienen una decisión explícita. Todavía se comprobarán coherencia, autor y revisión independiente.';
  return missing;
}
function setBusy(on){
  saving=on;
  const closed=state?.rows.find(r=>r.sample_id===selected)?.annotation_status==='REVIEWED';
  for(const control of el('form').querySelectorAll('select,textarea'))control.disabled=on||closed;
  el('save').disabled=on||closed;el('review').disabled=on||closed;el('reopen').disabled=on||!closed;
  for(const id of ['actor','filter','reload'])el(id).disabled=on;
  for(const tile of el('gallery').querySelectorAll('button'))tile.disabled=on;
}
function drawGallery(){
  el('gallery').replaceChildren();
  for(const row of state.rows){
    if(el('filter').value!=='all'&&row.annotation_status!==el('filter').value)continue;
    const tile=document.createElement('button');tile.type='button';tile.className='tile'+(row.sample_id===selected?' active':'');
    const image=document.createElement('img');image.src='/image/'+row.sample_id;image.alt=`Botella ${row.track_id}, fotograma ${row.frame_index}`;image.loading='lazy';
    tile.append(image);
    for(const text of [`Botella ${row.track_id} · F${row.frame_index}`,row.annotation_status]){const span=document.createElement('span');span.textContent=text;tile.append(span);}
    tile.onclick=()=>choose(row.sample_id);el('gallery').append(tile);
  }
  const closed=state.rows.filter(r=>r.annotation_status==='REVIEWED').length;
  el('progress').textContent=`${state.rows.length} muestras · ${closed} cerradas · revisión ${state.revision}`;
}
function choose(id,force=false){
  if(saving&&!force)return;
  if(!force&&dirty&&!confirm('Hay cambios sin guardar. ¿Descartarlos y cambiar de muestra?'))return;
  selected=id;dirty=false;message('');const row=state.rows.find(r=>r.sample_id===id);
  el('identity').textContent=`Botella ${row.track_id} · Fotograma ${row.frame_index}`;
  el('provenance').textContent=`Análisis ${row.analysis_id} · ejecución ${row.run_id} · muestra ${row.sample_id}`;
  el('photo').src='/image/'+id;el('photo').alt=`Recorte original: botella ${row.track_id}, fotograma ${row.frame_index}`;
  el('technical').textContent=`${row.quality.width} × ${row.quality.height} · calidad técnica ${row.quality.status} · ${row.quality.flags.join(', ')||'sin avisos automáticos'}`;
  for(const id of defects)setTri(id,row.labels[id]);
  setTri('body',row.evaluable.body);setTri('cap',row.evaluable.cap);setTri('other',row.other_defect);
  setTri('CONFORME',row.categories?.CONFORME);setTri('NO_EVALUABLE',row.categories?.NO_EVALUABLE);el('notes').value=row.notes||'';
  el('review-identity').textContent=`Anotador inicial: ${row.annotator||'todavía sin asignar'} · Revisor: ${row.reviewer||'todavía sin asignar'}`;
  const closed=row.annotation_status==='REVIEWED';
  for(const control of el('form').querySelectorAll('select,textarea'))control.disabled=closed;
  el('save').disabled=closed;el('review').disabled=closed;el('reopen').disabled=!closed;
  el('history').replaceChildren();
  for(const event of row.annotation_history||[]){const li=document.createElement('li');li.textContent=`#${event.revision} · ${event.action} · ${event.actor} · ${event.at}`;el('history').append(li);}
  drawGallery();
  updateReadiness();
}
async function load(){
  if(saving)return;
  if(dirty&&!confirm('Hay cambios sin guardar. ¿Descartarlos y recargar?'))return;
  try{const response=await fetch('/api/state');const data=await response.json();if(!response.ok)throw Error(data.error);state=data;choose(selected||state.rows[0].sample_id,true);}catch(error){message(error.message);}
}
async function save(action){
  if(saving||!selected)return;
  if(action==='review'){
    const missing=updateReadiness();
    if(missing.length){message('No se puede cerrar: falta decidir '+missing.map(field=>field.label).join('; ')+'. Complete los campos y guarde el borrador.');el(missing[0].control).focus();return;}
    if(dirty){message('Guarde las correcciones como borrador antes de solicitar el cierre.');return;}
  }
  if(action==='review'&&!confirm('¿Confirma que revisó esta muestra y desea cerrarla?'))return;
  setBusy(true);message('Guardando…');
  try{
    const response=await fetch('/api/save',{method:'POST',headers:{'Content-Type':'application/json','X-Label-Token':state.token},body:JSON.stringify({sample_id:selected,revision:state.revision,actor:el('actor').value,action,values:values()})});
    const data=await response.json();if(!response.ok){if(data.missing_fields?.length){for(const field of data.missing_fields){if(el(field.control))el(field.control).setAttribute('aria-invalid','true');}el(data.missing_fields[0].control)?.focus();}throw Error(data.error);}
    state=data;choose(selected,true);message(`Guardado. Revisión ${state.revision}.`);
  }catch(error){message(error.message+' Los cambios del formulario permanecen aquí.');}finally{setBusy(false);}
}
el('form').addEventListener('input',()=>{dirty=true;updateReadiness();});el('form').onsubmit=e=>e.preventDefault();
el('save').onclick=()=>save('draft');el('review').onclick=()=>save('review');el('reopen').onclick=()=>save('reopen');
el('reload').onclick=load;el('filter').onchange=drawGallery;el('zoom').onclick=()=>el('photo').classList.toggle('zoomed');
window.addEventListener('beforeunload',event=>{if(dirty){event.preventDefault();event.returnValue='';}});
load();
