"""Auditoría individual y configuraciones exploratorias, sin cambiar referencias/pesos."""
import argparse
from collections import Counter
import csv
import html
import json
from pathlib import Path
import time

import cv2
import numpy as np
from .evaluacion_epp33 import ROOT, BASE, PESOS, CLASES, leer, guardar, sha, iou, comparar_frame, resumir
from seguridad.piloto import asociar

EVALUACION = ROOT/'output/experimental_pilotos/evaluacion_epp33_v002_001'
CONFIGURACIONES = [
    {'id':'base_reproducida','imgsz':640,'conf':.30,'iou_nms':.50},
    {'id':'conf015_640','imgsz':640,'conf':.15,'iou_nms':.50},
    {'id':'res960','imgsz':960,'conf':.30,'iou_nms':.50},
    {'id':'res960_conf015','imgsz':960,'conf':.15,'iou_nms':.50},
    {'id':'res1280','imgsz':1280,'conf':.30,'iou_nms':.50},
    {'id':'res960_conf015_nms070','imgsz':960,'conf':.15,'iou_nms':.70},
]


def preparar(salida):
    referencia=leer(EVALUACION/'referencia_trabajo.json')
    comparacion=leer(EVALUACION/'comparacion_por_frame.json')
    preds={p['sample_id']:p for p in leer(EVALUACION/'predicciones.json')['samples']}
    refs={r['sample_id']:r for r in referencia['frames']}
    protegidos=leer(EVALUACION/'auditoria.json')['protegidos_antes']
    for p in EVALUACION.rglob('*'):
        if p.is_file():protegidos[str(p.relative_to(ROOT))]=sha(p)
    if any(sha(ROOT/p)!=h for p,h in protegidos.items()):raise ValueError('Una entrada ya difiere de la evaluación base.')
    salida.mkdir(parents=True,exist_ok=False);(salida/'casos').mkdir();(salida/'contactos').mkdir()
    guardar(salida/'plan_previo.json',{'configuraciones':CONFIGURACIONES,'evaluacion_iou':.50,
        'regla_presupuesto_exploratorio':{'precision_minima':'baseline - 0.05 absoluto','FP_maximos':'baseline + 3 por clase en 33 frames',
            'condicion_adicional':'recall y F1 estrictamente mayores que baseline'},
        'advertencia':'Mismos 33 frames usados para ajustar: conjunto de desarrollo, no test independiente. No se aplica configuración a la aplicación.',
        'base_nms':'Predictor instalado: PREDICT_IOU=0.5; se exige replay explícito coincidente',
        'pesos':{k:sha(p) for k,p in PESOS.items()},'protegidos_antes':protegidos})
    casos=[]
    for clase,estado,key in [('CHALECO','FN','referencias'),('CASCO','FN','referencias'),('PERSONA','FP','predicciones')]:
        contador=0
        for d in comparacion:
            frame=refs[d['sample_id']];imagen=cv2.imread(str(BASE/frame['image']))
            if sha(BASE/frame['image'])!=frame['image_sha256']:raise ValueError('Imagen modificada.')
            for obj in d[key]:
                if obj['clase']!=clase or obj['resultado']!=estado:continue
                contador+=1;cid=f'{clase}_{estado}_{contador:03d}'
                target=obj['bbox_xyxy'];w=target[2]-target[0];h=target[3]-target[1]
                opposite=d['predicciones' if estado=='FN' else 'referencias']
                candidatos=[(iou(target,o['bbox_xyxy']),o) for o in opposite if o['clase']==clase]
                near=max(candidatos,key=lambda x:x[0]) if candidatos else (None,None)
                x1,y1,x2,y2=target;cx,cy=(x1+x2)/2,(y1+y2)/2
                rw,rh=max(320,w*1.5),max(240,h*1.5)
                a,c,z,f=max(0,int(cx-rw/2)),max(0,int(cy-rh/2)),min(imagen.shape[1],int(cx+rw/2)),min(imagen.shape[0],int(cy+rh/2))
                roi=imagen[max(0,int(y1)):min(imagen.shape[0],int(np.ceil(y2))),max(0,int(x1)):min(imagen.shape[1],int(np.ceil(x2)))]
                gray=cv2.cvtColor(roi,cv2.COLOR_BGR2GRAY)
                escala=min(1,256/max(gray.shape));small=cv2.resize(gray,(max(1,round(gray.shape[1]*escala)),max(1,round(gray.shape[0]*escala))))
                sharp=float(cv2.Laplacian(small,cv2.CV_64F).var());media=float(gray.mean())
                clip_dark=float(np.mean(gray<=10));clip_bright=float(np.mean(gray>=245))
                alternativa=[]
                if estado=='FN':
                    for raw in preds[d['sample_id']]['salida_epp_completa']:
                        ov=iou(target,raw['bbox_xyxy'])
                        if ov>=.3 and raw['clase_modelo'] not in ('Hardhat' if clase=='CASCO' else 'Safety Vest',):
                            alternativa.append({'clase_modelo':raw['clase_modelo'],'score':raw['score'],'iou':ov})
                flags={'oclusion_humana':obj.get('visibilidad')=='OCLUIDO',
                    'parcial_humano':obj.get('visibilidad')=='PARCIAL',
                    'objeto_pequeno_640':min(w,h)*640/max(frame['width'],frame['height'])<16,
                    'aviso_desenfoque_roi':sharp<50,
                    'aviso_iluminacion':media<40 or media>215 or clip_dark>.2 or clip_bright>.2,
                    'desacuerdo_localizacion':near[0] is not None and .3<=near[0]<.5,
                    'clase_alternativa_solapada':bool(alternativa)}
                registro={'id':cid,'sample_id':d['sample_id'],'video_id':d['video_id'],'frame_index':d['frame_index'],
                    'clase':clase,'tipo_error':estado,'objeto_base':obj,'ancho_px':w,'alto_px':h,
                    'min_dimension_proyectada_640':min(w,h)*640/max(frame['width'],frame['height']),
                    'contraparte_mas_cercana':near[1],'max_iou':near[0],'roi':[a,c,z,f],
                    'laplaciano_roi_normalizada_256':sharp,'gris_medio_roi':media,'pixeles_oscuros':clip_dark,'pixeles_saturados':clip_bright,
                    'indicadores':flags,'clases_alternativas':alternativa,
                    'revision_independiente':'PENDIENTE','observacion_visual_agente':None,
                    'categorias_auditoria':[],'imagen_crop':f'casos/{cid}.jpg'}
                dibujo=imagen.copy()
                for other in opposite:
                    if other['clase']==clase:
                        p1,p2,p3,p4=map(round,other['bbox_xyxy']);cv2.rectangle(dibujo,(p1,p2),(p3,p4),(255,170,0),2)
                p1,p2,p3,p4=map(round,target);cv2.rectangle(dibujo,(p1,p2),(p3,p4),(0,90,255),4)
                crop=dibujo[c:f,a:z]
                if not cv2.imwrite(str(salida/registro['imagen_crop']),crop):raise OSError('No se guardó el crop.')
                # Miniatura con proporciones intactas y fondo neutro.
                factor=min(620/crop.shape[1],310/crop.shape[0]);sm=cv2.resize(crop,(round(crop.shape[1]*factor),round(crop.shape[0]*factor)))
                cell=np.full((360,640,3),240,np.uint8);cell[45:45+sm.shape[0],10:10+sm.shape[1]]=sm
                texto=f"{cid} | {d['sample_id']} | IoU {near[0] if near[0] is not None else -1:.3f}"
                cv2.putText(cell,texto,(8,20),cv2.FONT_HERSHEY_SIMPLEX,.43,(0,0,0),1)
                cv2.putText(cell,f"vis={obj.get('visibilidad','PRED')} min640={registro['min_dimension_proyectada_640']:.1f}px blur={sharp:.0f}",(8,39),cv2.FONT_HERSHEY_SIMPLEX,.43,(0,0,0),1)
                registro['_contacto']=cell;casos.append(registro)
        esperado={'CHALECO':44,'CASCO':20,'PERSONA':19}[clase]
        if contador!=esperado:raise ValueError('La base de errores cambió.')
    for inicio in range(0,len(casos),10):
        grupo=casos[inicio:inicio+10];cells=[r['_contacto'] for r in grupo]
        while len(cells)<10:cells.append(np.full((360,640,3),240,np.uint8))
        sheet=cv2.vconcat([cv2.hconcat(cells[j:j+2]) for j in range(0,10,2)])
        cv2.imwrite(str(salida/'contactos'/f'contacto_{inicio//10+1:02d}.jpg'),sheet)
    for c in casos:del c['_contacto']
    guardar(salida/'casos_auditoria.json',casos)
    print('Preparados 83 casos: 44 FN CHALECO, 20 FN CASCO y 19 FP PERSONA.',flush=True)


def configuraciones(salida):
    from ultralytics import YOLO
    refs=leer(EVALUACION/'referencia_trabajo.json');base=leer(EVALUACION/'metricas.json')
    (salida/'configuraciones').mkdir()
    modelos={k:YOLO(str(path)) for k,path in PESOS.items()};todos=[]
    for config in leer(salida/'plan_previo.json')['configuraciones']:
        carpeta=salida/'configuraciones'/config['id'];carpeta.mkdir();inicio=time.perf_counter();predicciones=[];detalles=[]
        for f in refs['frames']:
            im=cv2.imread(str(BASE/f['image']));persons={};detections=[];raw=[]
            kwargs={'conf':config['conf'],'imgsz':config['imgsz'],'iou':config['iou_nms'],'max_det':300,
                'agnostic_nms':False,'device':'cpu','save':False,'verbose':False}
            result=modelos['personas'].predict(im,classes=[0],**kwargs)[0]
            for i,b in enumerate(result.boxes):
                persons[i]=b.xyxy[0].tolist();detections.append({'clase':'PERSONA','bbox_xyxy':persons[i],'score':float(b.conf[0]),'persona_pred_id':i,'modelo':'yolo11n'})
            result=modelos['epp'].predict(im,**kwargs)[0]
            for b in result.boxes:
                tipo=modelos['epp'].names[int(b.cls[0])];caja=b.xyxy[0].tolist();score=float(b.conf[0])
                eq='CASCO' if tipo in ('Hardhat','NO-Hardhat') else 'CHALECO' if tipo in ('Safety Vest','NO-Safety Vest') else None
                owner=asociar(caja,persons,eq) if eq else None
                raw.append({'clase_modelo':tipo,'bbox_xyxy':caja,'score':score,'persona_pred_id':owner})
                if tipo in ('Hardhat','Safety Vest'):detections.append({'clase':eq,'bbox_xyxy':caja,'score':score,'persona_pred_id':owner,'modelo':'best.pt'})
            predicciones.append({'sample_id':f['sample_id'],'image_sha256':f['image_sha256'],'detecciones':detections,'salida_epp_completa':raw})
            detalles.append(comparar_frame(f,detections))
        metricas=resumir(detalles);metricas['segundos']=time.perf_counter()-inicio
        metricas['configuracion']=config
        if config['id']=='base_reproducida':
            for clase in CLASES:
                if any(metricas['deteccion'][clase][k]!=base['deteccion'][clase][k] for k in ['TP','FP','FN','ignoradas']):
                    guardar(carpeta/'replay_incompatible.json',metricas);raise ValueError('El replay no coincide; se detiene el ajuste.')
        metricas['presupuesto_por_clase']={}
        for clase in CLASES:
            old,new=base['deteccion'][clase],metricas['deteccion'][clase]
            cumple=(new['recall']>old['recall'] and new['f1']>old['f1'] and new['precision']>=old['precision']-.05 and new['FP']<=old['FP']+3)
            metricas['presupuesto_por_clase'][clase]={'cumple':cumple,'delta_FP':new['FP']-old['FP'],
                'delta_recall':new['recall']-old['recall'],'delta_precision':new['precision']-old['precision'],'delta_f1':new['f1']-old['f1']}
        guardar(carpeta/'predicciones.json',{'samples':predicciones,'configuracion':config,
            'parametros_resueltos':{k:{n:getattr(m.predictor.args,n,None) for n in ['conf','imgsz','iou','max_det','agnostic_nms','rect','device']} for k,m in modelos.items()},
            'referencia_sha256':sha(EVALUACION/'referencia_trabajo.json'),'pesos':{k:sha(p) for k,p in PESOS.items()}})
        guardar(carpeta/'comparacion.json',detalles);guardar(carpeta/'metricas.json',metricas)
        guardar(carpeta/'por_video.json',{v:resumir([d for d in detalles if d['video_id']==v]) for v in ['epp_corto','epp_largo']})
        todos.append(metricas);print(config['id'],json.dumps(metricas['deteccion']),flush=True)
    guardar(salida/'comparacion_configuraciones.json',todos)


def galeria(salida):
    casos=leer(salida/'casos_auditoria.json');base=leer(EVALUACION/'comparacion_por_frame.json');refs=leer(EVALUACION/'referencia_trabajo.json')
    byid={f['sample_id']:f for f in refs['frames']};det={d['sample_id']:d for d in base}
    (salida/'escenas').mkdir()
    for sid in {c['sample_id'] for c in casos}:
        im=cv2.imread(str(BASE/byid[sid]['image']))
        from .evaluacion_epp33 import imagen_anotada
        cv2.imwrite(str(salida/'escenas'/f'{sid}_humano.jpg'),imagen_anotada(im,det[sid]['referencias']))
        cv2.imwrite(str(salida/'escenas'/f'{sid}_prediccion.jpg'),imagen_anotada(im,det[sid]['predicciones'],True))
    cards=[]
    for caso in sorted(casos,key=lambda c:(-c.get('prioridad',0),c['id'])):
        sid=caso['sample_id'];texto=html.escape(caso.get('observacion_visual_agente') or 'Revisión visual pendiente')
        cats=html.escape(', '.join(caso.get('categorias_auditoria',[])))
        cards.append(f'<article data-clase="{caso["clase"]}"><h2>{caso["id"]} · {sid}</h2><p>Prioridad {caso.get("prioridad",0)} · {cats}</p><p>{texto}</p><p>Revisión independiente: PENDIENTE. No se modificó la referencia.</p><div class="paneles"><figure><figcaption>Detalle: naranja error objetivo, azul contraparte de la otra fuente</figcaption><a href="{caso["imagen_crop"]}"><img loading="lazy" src="{caso["imagen_crop"]}"></a></figure><figure><figcaption>Escena con referencias humanas</figcaption><a href="escenas/{sid}_humano.jpg"><img loading="lazy" src="escenas/{sid}_humano.jpg"></a></figure><figure><figcaption>Predicciones base</figcaption><a href="escenas/{sid}_prediccion.jpg"><img loading="lazy" src="escenas/{sid}_prediccion.jpg"></a></figure></div><details><summary>Registro individual y evidencia técnica</summary><pre>{html.escape(json.dumps(caso,ensure_ascii=False,indent=2))}</pre></details></article>')
    pagina='<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Auditoría priorizada EPP</title><style>body{font:15px system-ui;max-width:1700px;margin:25px auto;padding:12px}.paneles{display:flex;gap:12px}figure{width:33%;margin:0}img{width:100%}article{border-top:1px solid #aaa;padding:15px 0}pre{white-space:pre-wrap}</style></head><body><h1>Auditoría EPP · 83 errores base</h1><p>44 FN CHALECO, 20 FN CASCO, 19 FP PERSONA. Las categorías son diagnóstico, no nuevas anotaciones ni causas demostradas. Se separan hechos geométricos, atributos humanos e hipótesis visuales.</p><p><a href="INFORME_AUDITORIA.md">Informe</a> · <a href="comparacion_configuraciones.json">Configuraciones exploratorias</a></p><label>Mostrar <select onchange="document.querySelectorAll(\'article\').forEach(a=>a.hidden=this.value!==\'TODAS\'&&a.dataset.clase!==this.value)"><option>TODAS</option><option>CHALECO</option><option>CASCO</option><option>PERSONA</option></select></label>'+''.join(cards)+'</body></html>'
    (salida/'index.html').write_text(pagina,encoding='utf-8')
    filas=[{k:c.get(k) for k in ['id','sample_id','video_id','frame_index','clase','tipo_error','prioridad','categorias_auditoria','observacion_visual_agente']} for c in casos]
    with (salida/'auditoria_casos.csv').open('x',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(filas[0]));w.writeheader();w.writerows(filas)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('accion',choices=['preparar','configuraciones','galeria']);p.add_argument('--salida',type=Path,required=True)
    args=p.parse_args();salida=args.salida.resolve()
    if not salida.is_relative_to(ROOT/'output/experimental_pilotos'):raise ValueError('Fuera del laboratorio.')
    {'preparar':preparar,'configuraciones':configuraciones,'galeria':galeria}[args.accion](salida)


if __name__=='__main__':main()
