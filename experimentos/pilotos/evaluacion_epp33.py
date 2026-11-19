"""Primera comparación EPP con anotaciones humanas ANNOTATED, revisión 2 pendiente.

No importa Django, no usa SQLite, no entrena y no reutiliza predicciones anteriores.
"""
import argparse
from collections import Counter
import copy
import csv
from datetime import datetime, timezone
import hashlib
import html
from importlib.metadata import version
import json
import math
from pathlib import Path
import shutil
import subprocess
import unicodedata

import cv2
from seguridad.piloto import asociar
from .referencia_epp import validar_documento

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'output/experimental_pilotos/seguridad_epp_v002_001'
CLASES = ('PERSONA', 'CASCO', 'CHALECO')
PESOS = {'personas': ROOT/'yolo11n.pt', 'epp': ROOT/'Modelos/best.pt'}


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()


def leer(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def guardar(path, data):
    with Path(path).open('x',encoding='utf-8') as f:
        json.dump(data,f,ensure_ascii=False,indent=2)


def normalizar_autor(nombre):
    return unicodedata.normalize('NFKC',nombre).strip().casefold() if isinstance(nombre,str) else nombre


def iou(a,b):
    inter=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    union=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-inter
    return inter/union if union else 0.


def auditar(entrada,salida):
    raw=leer(entrada);base=leer(BASE/'referencia_pendiente.json')
    estructura=validar_documento(raw,base)
    if len(raw['frames'])!=33 or sum(len(f['objects']) for f in raw['frames'])!=203:
        raise ValueError('No coincide con los 33 frames y 203 cajas declaradas.')
    if any(f['status'] not in ('ANNOTATED','REVIEWED') or not f.get('exhaustive') for f in raw['frames']):
        raise ValueError('Esta evaluación requiere anotación exhaustiva, no borradores.')
    protegidos={str(entrada.relative_to(ROOT)):sha(entrada)}
    for p in [ROOT/'db.sqlite3',*PESOS.values(),BASE/'referencia_pendiente.json']:
        protegidos[str(p.relative_to(ROOT))]=sha(p)
    for carpeta in [ROOT/'produccion',ROOT/'config',ROOT/'datasets/calidad_botellas/v002/experiments/detection_manual_v001/dataset',
                    ROOT/'output/experimental_pilotos/evaluacion_deteccion_v002_001']:
        for p in carpeta.rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts:
                protegidos[str(p.relative_to(ROOT))]=sha(p)
    clases,visibilidad,estados=Counter(),Counter(),Counter()
    autores=Counter();avisos=[];muestras=[];box_ids=[]
    for video in raw['videos']:
        path=(ROOT/video['path']).resolve()
        if not path.is_relative_to(ROOT) or sha(path)!=video['video_sha256']:
            raise ValueError('Video fuente distinto al declarado.')
        protegidos[str(path.relative_to(ROOT))]=sha(path)
    for frame in raw['frames']:
        path=(BASE/frame['image']).resolve()
        if not path.is_relative_to(BASE) or sha(path)!=frame['image_sha256']:
            raise ValueError('Hash de imagen inválido: '+frame['sample_id'])
        imagen=cv2.imread(str(path))
        if imagen is None or list(imagen.shape[1::-1])!=[frame['width'],frame['height']]:
            raise ValueError('Imagen ilegible o dimensiones distintas.')
        protegidos[str(path.relative_to(ROOT))]=sha(path)
        autores[frame['author']]+=1
        for obj in frame['objects']:
            clases[obj['clase']]+=1;visibilidad[obj['clase']+'_'+obj['visibilidad']]+=1
            box_ids.append(obj['id'])
        for persona in frame['personas']:
            for equipo in ('casco','chaleco'):
                estados[equipo+'_'+persona[equipo+'_estado']]+=1
                if persona[equipo+'_estado']=='PRESENTE' and persona.get(equipo+'_region_visible') is False:
                    avisos.append({'sample_id':frame['sample_id'],'persona_id':persona['id'],'equipo':equipo,
                        'motivo':'PRESENTE con caja visible pero región visible=false; valores conservados'})
        muestras.append({'sample_id':frame['sample_id'],'sha256':sha(path),'width':frame['width'],'height':frame['height'],
                         'cajas':len(frame['objects']),'estado':frame['status']})
    trabajo=copy.deepcopy(raw)
    for f in trabajo['frames']: f['author']=normalizar_autor(f['author'])
    salida.mkdir(parents=True,exist_ok=False)
    (salida/'entrada_original').mkdir()
    shutil.copyfile(entrada,salida/'entrada_original'/entrada.name)
    guardar(salida/'referencia_trabajo.json',trabajo)
    guardar(salida/'auditoria.json',{'fecha_utc':datetime.now(timezone.utc).isoformat(),'estructura':estructura,
        'politica_evaluacion':'Se admiten ANNOTATED exhaustivos para primera localización provisional; no se declaran REVIEWED',
        'segunda_revision_independiente':'PENDIENTE','frames':33,'cajas':203,'clases':dict(clases),
        'visibilidad':dict(visibilidad),'estados_persona':dict(estados),'autores_originales':dict(autores),
        'normalizacion_autor':'NFKC + strip + casefold, solo copia de trabajo; no cambia estados ni revisores',
        'identificadores_objeto_globales_distintos':len(set(box_ids)),'avisos':avisos,'muestras':muestras,
        'archivo_original':str(entrada.relative_to(ROOT)),'sha256_original':sha(entrada),
        'parametros_fijados':{'confidence':.30,'imgsz':640,'iou_minimo':.50,'device':'cpu'},
        'regla_ignoradas':'Tras matching positivo: ignorar unmatched si intersecta región NO_EVALUABLE de misma clase, o caja de persona con estado humano NO_EVALUABLE para ese equipo. Máscara conservadora, no caja humana de equipo.',
        'protegidos_antes':protegidos})
    print(json.dumps({'frames':33,'cajas':dict(clases),'estados':dict(estados),'avisos':avisos},ensure_ascii=True),flush=True)


def inferir(salida):
    from ultralytics import YOLO
    ref=leer(salida/'referencia_trabajo.json')
    modelos={k:YOLO(str(path)) for k,path in PESOS.items()}
    if modelos['personas'].names[0]!='person' or modelos['epp'].names[3]!='Hardhat' or modelos['epp'].names[13]!='Safety Vest':
        raise ValueError('Catálogo de pesos incompatible.')
    muestras=[]
    for f in ref['frames']:
        path=BASE/f['image']
        if sha(path)!=f['image_sha256']: raise ValueError('Imagen alterada antes de inferir.')
        imagen=cv2.imread(str(path));detecciones=[];personas={}
        resultado=modelos['personas'].predict(imagen,classes=[0],conf=.30,imgsz=640,device='cpu',save=False,verbose=False)[0]
        for i,b in enumerate(resultado.boxes):
            caja=b.xyxy[0].tolist();personas[i]=caja
            detecciones.append({'clase':'PERSONA','bbox_xyxy':caja,'score':float(b.conf[0]),'persona_pred_id':i,'modelo':'yolo11n'})
        resultado=modelos['epp'].predict(imagen,conf=.30,imgsz=640,device='cpu',save=False,verbose=False)[0]
        raw=[]
        for b in resultado.boxes:
            clase=modelos['epp'].names[int(b.cls[0])];caja=b.xyxy[0].tolist();score=float(b.conf[0])
            equipo='CASCO' if clase in ('Hardhat','NO-Hardhat') else 'CHALECO' if clase in ('Safety Vest','NO-Safety Vest') else None
            owner=asociar(caja,personas,equipo) if equipo else None
            raw.append({'clase_modelo':clase,'bbox_xyxy':caja,'score':score,'persona_pred_id':owner})
            if clase in ('Hardhat','Safety Vest'):
                detecciones.append({'clase':equipo,'bbox_xyxy':caja,'score':score,'persona_pred_id':owner,'modelo':'best.pt'})
        muestras.append({'sample_id':f['sample_id'],'image_sha256':f['image_sha256'],'detecciones':detecciones,'salida_epp_completa':raw})
    guardar(salida/'predicciones.json',{'samples':muestras,'clases_ejecutadas':list(CLASES),
        'parametros':{'conf':.30,'imgsz':640,'device':'cpu','save':False,'tracking':'NO_EJECUTADO_EN_FRAMES_AISLADOS'},
        'modelos':{k:{'path':str(PESOS[k].relative_to(ROOT)),'sha256':sha(PESOS[k]),'catalogo':m.names} for k,m in modelos.items()},
        'versiones':{p:version(p) for p in ['ultralytics','torch','opencv-python','numpy']},
        'referencia_trabajo_sha256':sha(salida/'referencia_trabajo.json')})
    print('Inferencia real completa: 33/33 fotogramas.',flush=True)


def comparar_frame(frame,predicciones,umbral=.50):
    humanos=frame['objects'];usados=set();preds=[]
    ignoradas={c:[o['bbox_xyxy'] for o in humanos if o['clase']==c and o['visibilidad']=='NO_EVALUABLE'] for c in CLASES}
    for persona in frame['personas']:
        cajas=[o['bbox_xyxy'] for o in humanos if o['clase']=='PERSONA' and o.get('persona_id')==persona['id']]
        for equipo in ('casco','chaleco'):
            if persona.get(equipo+'_estado')=='NO_EVALUABLE':ignoradas[equipo.upper()].extend(cajas)
    cuentas={c:{'TP':0,'FP':0,'FN':0,'ignoradas':0} for c in CLASES}
    for numero,p in sorted(enumerate(predicciones),key=lambda v:v[1]['score'],reverse=True):
        if p['clase'] not in CLASES or not math.isfinite(p['score']) or not 0<=p['score']<=1: raise ValueError('Predicción inválida.')
        candidatos=[(iou(p['bbox_xyxy'],o['bbox_xyxy']),i) for i,o in enumerate(humanos)
            if i not in usados and o['clase']==p['clase'] and o['visibilidad']!='NO_EVALUABLE']
        mejor=max(candidatos,default=(0,None))
        if mejor[0]>=umbral:estado='TP';usados.add(mejor[1])
        elif any(iou(p['bbox_xyxy'],zona)>0 for zona in ignoradas[p['clase']]):estado='IGNORADA'
        else:estado='FP'
        cuentas[p['clase']]['ignoradas' if estado=='IGNORADA' else estado]+=1
        preds.append({**p,'prediction_index':numero,'resultado':estado,'reference_index':mejor[1] if estado=='TP' else None,
                      'iou_match':mejor[0] if estado=='TP' else None})
    refs=[]
    for i,o in enumerate(humanos):
        estado='NO_EVALUABLE' if o['visibilidad']=='NO_EVALUABLE' else 'TP' if i in usados else 'FN'
        if estado=='FN':cuentas[o['clase']]['FN']+=1
        refs.append({**o,'reference_index':i,'resultado':estado,
            'max_iou_predicha':max((iou(o['bbox_xyxy'],p['bbox_xyxy']) for p in preds if p['clase']==o['clase']),default=None)})
    persona_map={p['persona_pred_id']:humanos[p['reference_index']]['persona_id'] for p in preds if p['clase']=='PERSONA' and p['resultado']=='TP'}
    asociaciones=[]
    for ref in refs:
        if ref['clase']=='PERSONA' or ref['resultado']=='NO_EVALUABLE' or not ref.get('persona_id'):continue
        pred=next((p for p in preds if p['resultado']=='TP' and p['reference_index']==ref['reference_index']),None)
        if pred is None:estado='EQUIPO_NO_LOCALIZADO';owner=None
        elif pred.get('persona_pred_id') is None:estado='SIN_ASOCIACION';owner=None
        elif pred['persona_pred_id'] not in persona_map:estado='PERSONA_NO_EMPAREJADA';owner=None
        else:
            owner=persona_map[pred['persona_pred_id']]
            estado='CORRECTA' if owner==ref['persona_id'] else 'INCORRECTA'
        asociaciones.append({'equipo':ref['clase'],'reference_index':ref['reference_index'],'persona_humana':ref['persona_id'],
            'persona_humana_de_prediccion':owner,'resultado':estado})
    return {'sample_id':frame['sample_id'],'video_id':frame['video_id'],'frame_index':frame['frame_index'],
            'tiempo_nominal_s':frame['tiempo_nominal_s'],'cuentas':cuentas,'predicciones':preds,'referencias':refs,'asociaciones':asociaciones}


def resumir(detalles):
    metricas={}
    for clase in CLASES:
        c={campo:sum(d['cuentas'][clase][campo] for d in detalles) for campo in ['TP','FP','FN','ignoradas']}
        tp,fp,fn=c['TP'],c['FP'],c['FN']
        c.update(precision=tp/(tp+fp) if tp+fp else None,recall=tp/(tp+fn) if tp+fn else None,
                 f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None)
        metricas[clase]=c
    asociaciones={}
    for clase in ('CASCO','CHALECO'):
        c=Counter(a['resultado'] for d in detalles for a in d['asociaciones'] if a['equipo']==clase)
        total=sum(c.values());verificables=c['CORRECTA']+c['INCORRECTA']
        asociaciones[clase]={'conteos':dict(c),'enlaces_humanos':total,
            'exactitud_condicional_verificable':c['CORRECTA']/verificables if verificables else None,
            'cobertura_verificable':verificables/total if total else None,
            'recall_cadena_completa':c['CORRECTA']/total if total else None}
    return {'deteccion':metricas,'asociacion':asociaciones}


def imagen_anotada(imagen,boxes,pred=False):
    copia=imagen.copy();colores={'TP':(0,190,0),'FP':(0,0,230),'FN':(0,130,255),'IGNORADA':(150,150,150),'NO_EVALUABLE':(150,150,150)}
    for b in boxes:
        a,c,d,f=map(round,b['bbox_xyxy']);color=colores[b['resultado']]
        cv2.rectangle(copia,(a,c),(d,f),color,3)
        texto=f"{'P'+str(b['prediction_index']) if pred else 'H'+str(b['reference_index'])} {b['clase']} {b['resultado']}"
        texto+=f" owner={b.get('persona_pred_id') if pred else b.get('persona_id')}"
        if pred:texto+=f" {b['score']:.2f}"
        cv2.putText(copia,texto,(max(0,a),max(20,c+20)),cv2.FONT_HERSHEY_SIMPLEX,.65,(0,0,0),4)
        cv2.putText(copia,texto,(max(0,a),max(20,c+20)),cv2.FONT_HERSHEY_SIMPLEX,.65,color,2)
    return copia


def comparar(salida):
    import imageio_ffmpeg
    refs=leer(salida/'referencia_trabajo.json');preds=leer(salida/'predicciones.json')
    byid={p['sample_id']:p for p in preds['samples']}
    if len(byid)!=33:raise ValueError('Predicciones incompletas.')
    detalles=[]
    for f in refs['frames']:
        p=byid[f['sample_id']]
        if p['image_sha256']!=f['image_sha256']:raise ValueError('Hash de referencia y predicción incompatible.')
        detalles.append(comparar_frame(f,p['detecciones']))
    total=resumir(detalles)
    total.update(estado='PRIMERA_EVALUACION_ANNOTATED_SEGUNDA_REVISION_PENDIENTE',iou=.50,
        incumplimientos={'metricas':None,'motivo':'No hay ausencias humanas confirmadas ni referencia temporal exhaustiva'},
        tracking={'metricas':None,'motivo':'Inferencia en fotogramas aislados, no se evalúan trayectorias ni ID-switches'})
    guardar(salida/'metricas.json',total)
    guardar(salida/'por_video.json',{v:resumir([d for d in detalles if d['video_id']==v]) for v in sorted({d['video_id'] for d in detalles})})
    guardar(salida/'comparacion_por_frame.json',detalles)
    (salida/'galeria').mkdir();cards=[];errores=[];demos={};originales={f['sample_id']:f for f in refs['frames']}
    try:
        for d in detalles:
            sid=d['sample_id'];f=originales[sid];imagen=cv2.imread(str(BASE/f['image']))
            humana=imagen_anotada(imagen,d['referencias']);predicha=imagen_anotada(imagen,d['predicciones'],True)
            if not cv2.imwrite(str(salida/'galeria'/f'{sid}_humano.jpg'),humana) or not cv2.imwrite(str(salida/'galeria'/f'{sid}_prediccion.jpg'),predicha):raise OSError('No se guardó imagen comparativa.')
            panels=cv2.hconcat([cv2.resize(imagen,(960,540)),cv2.resize(humana,(960,540)),cv2.resize(predicha,(960,540))])
            for j,texto in enumerate(['ORIGINAL','REFERENCIA HUMANA - REVISION 2 PENDIENTE','PREDICCION REAL - IoU >= 0.50']):
                cv2.putText(panels,texto,(j*960+10,25),cv2.FONT_HERSHEY_SIMPLEX,.58,(0,255,255),2)
            cv2.putText(panels,f"{sid} | frame {f['frame_index']} | {f['tiempo_nominal_s']:.2f}s | MUESTRAS A 2 FPS, NO VIDEO CONTINUO",(10,525),cv2.FONT_HERSHEY_SIMPLEX,.6,(0,255,255),2)
            v=d['video_id']
            if v not in demos:
                demos[v]=subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(),'-n','-v','error','-f','rawvideo','-pix_fmt','bgr24',
                    '-s','2880x540','-r','2','-i','-','-an','-c:v','libx264','-preset','fast','-pix_fmt','yuv420p','-movflags','+faststart',str(salida/f'{v}_demostracion.mp4')],stdin=subprocess.PIPE)
            demos[v].stdin.write(panels.tobytes())
            original=(BASE/f['image']).relative_to(ROOT)
            ruta_original=str(Path('..')/'..'/'..'/original).replace('\\','/')
            imagenes=''.join(f'<figure><figcaption>{titulo}</figcaption><a href="{url}"><img loading="lazy" src="{url}" alt="{titulo}"></a></figure>' for titulo,url in
                [('Original',ruta_original),('Referencia humana',f'galeria/{sid}_humano.jpg'),('Predicciones reales',f'galeria/{sid}_prediccion.jpg')])
            info=html.escape(json.dumps(d,ensure_ascii=False,indent=2))
            estados_humanos=html.escape('; '.join(f"{p['id']}: CASCO {p['casco_estado']}, CHALECO {p['chaleco_estado']}" for p in f['personas']))
            cuentas_frame=html.escape(json.dumps(d['cuentas'],ensure_ascii=False))
            cards.append(f'<article><h2>{sid} · {f["tiempo_nominal_s"]:.2f}s</h2><p>Estados humanos conservados: {estados_humanos}</p><p>{cuentas_frame}</p><div class="paneles">{imagenes}</div><details><summary>Cajas, matches, errores y asociaciones</summary><pre>{info}</pre></details></article>')
            for tipo,key in [('prediccion','predicciones'),('referencia','referencias')]:
                for b in d[key]:
                    if b['resultado'] not in ('FP','FN','IGNORADA','NO_EVALUABLE'):continue
                    errores.append({'sample_id':sid,'video_id':v,'frame_index':f['frame_index'],'tiempo_nominal_s':f['tiempo_nominal_s'],
                        'tipo':tipo,'clase':b['clase'],'resultado':b['resultado'],'bbox_xyxy':b['bbox_xyxy'],
                        'score':b.get('score'),'visibilidad':b.get('visibilidad'),'persona_id':b.get('persona_id'),
                        'max_iou_predicha':b.get('max_iou_predicha')})
        for proceso in demos.values():
            proceso.stdin.close()
            if proceso.wait()!=0:raise RuntimeError('Fallo codificando la demostración.')
    finally:
        for proceso in demos.values():
            if proceso.poll() is None:proceso.kill();proceso.wait()
    guardar(salida/'errores.json',errores)
    with (salida/'errores.csv').open('x',encoding='utf-8-sig',newline='') as archivo:
        escritor=csv.DictWriter(archivo,fieldnames=list(errores[0]) if errores else ['sample_id']);escritor.writeheader();escritor.writerows(errores)
    guardar(salida/'asociaciones.json',[{'sample_id':d['sample_id'],'asociaciones':d['asociaciones']} for d in detalles])
    encabezado='<h1>EPP v002 · 33 referencias humanas</h1><p>Inferencia real. Anotaciones ANNOTATED exhaustivas; segunda revisión independiente pendiente. No se evalúan incumplimientos ni tracking.</p><p>Verde: TP; naranja: FN; rojo: FP; gris: ignorada/no evaluable. Los estados humanos NO_EVALUABLE se conservan.</p>'
    videos=''.join(f'<h2>{v}: demostración de muestras, no video continuo</h2><video controls preload="metadata" src="{v}_demostracion.mp4"></video>' for v in demos)
    tabla='<table border="1" cellpadding="8"><tr><th>Clase</th><th>TP</th><th>FP</th><th>FN</th><th>Precisión</th><th>Recall</th><th>F1</th></tr>'
    for clase,m in total['deteccion'].items():
        tabla+=f'<tr><td>{clase}</td><td>{m["TP"]}</td><td>{m["FP"]}</td><td>{m["FN"]}</td>'+''.join(f'<td>{m[k]*100:.2f}%</td>' if m[k] is not None else '<td>No calculable</td>' for k in ['precision','recall','f1'])+'</tr>'
    tabla+='</table>'
    pagina='<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Evaluación EPP 33</title><style>body{font:15px system-ui;max-width:1700px;margin:25px auto;padding:12px}.paneles{display:flex;gap:10px}figure{width:33%;margin:0}img,video{width:100%}article{border-top:1px solid #aaa;padding:15px 0}pre{white-space:pre-wrap}@media(max-width:900px){.paneles{display:block}figure{width:100%}}</style></head><body>'+encabezado+tabla+'<details><summary>Métricas completas y asociaciones</summary><pre>'+html.escape(json.dumps(total,ensure_ascii=False,indent=2))+'</pre></details>'+videos+''.join(cards)+'</body></html>'
    (salida/'index.html').write_text(pagina,encoding='utf-8')
    protegidos=leer(salida/'auditoria.json')['protegidos_antes'];cambios=[p for p,h in protegidos.items() if sha(ROOT/p)!=h]
    if cambios:raise RuntimeError('Entradas modificadas: '+str(cambios))
    guardar(salida/'verificacion_inicial.json',{'entradas_protegidas':len(protegidos),'cambios':cambios,
        'sha256_salidas':{str(p.relative_to(salida)):sha(p) for p in salida.rglob('*') if p.is_file()}})
    print(json.dumps(total,ensure_ascii=False),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('accion',choices=['auditar','inferir','comparar'])
    parser.add_argument('--entrada',type=Path)
    parser.add_argument('--salida',type=Path,required=True)
    args=parser.parse_args();salida=args.salida.resolve()
    if not salida.is_relative_to(ROOT/'output/experimental_pilotos'):raise ValueError('Salida fuera del laboratorio.')
    if args.accion=='auditar':
        entrada=args.entrada.resolve()
        if not entrada.is_relative_to(ROOT):raise ValueError('Entrada fuera del workspace.')
        auditar(entrada,salida)
    elif args.accion=='inferir':inferir(salida)
    else:comparar(salida)


if __name__=='__main__':main()
