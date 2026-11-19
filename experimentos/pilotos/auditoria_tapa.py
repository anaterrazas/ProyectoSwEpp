"""Auditoría reproducible de referencias TAPA. No etiqueta, predice ni entrena."""
import argparse
from collections import Counter, defaultdict
import hashlib
import html
import json
import math
import os
from pathlib import Path
import shutil

import cv2
import numpy as np
from .fuentes import ROOT, REFERENCIAS
from .evaluacion import iou


def sha(p):
    with Path(p).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def leer(p):
    return json.loads(p.read_text(encoding="utf-8"))


def guardar(p, contenido):
    with p.open("x", encoding="utf-8") as f:
        json.dump(contenido, f, ensure_ascii=False, indent=2, allow_nan=False)


def medidas(caja, ancho, alto):
    if len(caja) != 4 or any(not math.isfinite(v) for v in caja):
        raise ValueError("Caja no finita")
    x,y,x2,y2=caja
    if not (0<=x<x2<=ancho and 0<=y<y2<=alto):
        raise ValueError("Caja fuera de imagen o vacía")
    w,h=x2-x,y2-y;escala=640/max(ancho,alto)
    return {"ancho_px":w,"alto_px":h,"min_lado_entrada640":min(w,h)*escala,
            "pequena_640_menor16":min(w,h)*escala<16,"aspecto":w/h,
            "aspecto_extremo_aviso":w/h<.1 or w/h>10}


def duplicados_visuales(frames):
    """Parejas perceptuales candidatas, nunca eliminación ni independencia inferida."""
    return [{"a":a["sample_id"],"b":b["sample_id"],"distancia_dhash":(int(a["dhash"],16)^int(b["dhash"],16)).bit_count()}
            for i,a in enumerate(frames) for b in frames[i+1:]
            if (int(a["dhash"],16)^int(b["dhash"],16)).bit_count()<=4]


def ejecutar(salida, copia):
    salida=salida.resolve();copia=copia.resolve()
    if not salida.is_relative_to(ROOT/"output") or not copia.is_relative_to(REFERENCIAS.parent) or copia==REFERENCIAS:
        raise ValueError("Salidas fuera del laboratorio de auditoría/revisión")
    if salida.exists() or copia.exists():raise FileExistsError("No sobrescribir artefactos")
    # Fotogramas y todas las revisiones históricas originales antes de crear salidas.
    protegido={}
    for folder in [REFERENCIAS,ROOT/"produccion",ROOT/"monitoreo",ROOT/"seguridad",ROOT/"config",ROOT/"Modelos",ROOT/"output/experimental_pilotos"]:
        for p in folder.rglob("*"):
            if p.is_file() and "__pycache__" not in p.parts:
                protegido[p.relative_to(ROOT).as_posix()]=sha(p)
    protegido["db.sqlite3"]=sha(ROOT/"db.sqlite3")
    manifest=leer(REFERENCIAS/"manifest.json")
    snapshot=leer(ROOT/"output/experimental_pilotos/evaluacion_deteccion_v002_001/referencias.json")
    refs={f["sample_id"]:f for f in snapshot["records"]}
    registros=[];imagenes={};resumen=Counter();porvideo=defaultdict(Counter);conflictos=[];solapes=[];exactas=defaultdict(list)
    salida.mkdir(parents=True);(salida/"imagenes").mkdir();(salida/"contactos").mkdir()
    for frame in manifest["frames"]:
        sid=frame["sample_id"];p=REFERENCIAS/frame["image"]
        assert sha(p)==frame["image_sha256"]
        anot=leer(sorted((REFERENCIAS/"revisions"/sid).glob("*.json"))[-1])
        assert anot==refs[sid]["annotation"],"Hay revisiones nuevas; no usar snapshot obsoleto"
        image=cv2.imread(str(p));assert image is not None
        alto,ancho=image.shape[:2];assert [ancho,alto]==[frame["width"],frame["height"]]
        imagenes[sid]=image;exactas[frame["image_sha256"]].append(sid)
        tapas=[b for b in anot["boxes"] if b["class_name"]=="TAPA"]
        padres={b["box_id"]:b for b in anot["boxes"] if b["class_name"]=="ENVASE"}
        resumen["frames"]+=1;porvideo[frame["video_id"]]["frames"]+=1
        for b in anot["boxes"]:
            if b["class_name"]=="ENVASE" and b.get("notes","").lower().strip().startswith("tapa "):
                conflictos.append({"sample_id":sid,"box_id":b["box_id"],"clase_guardada":b["class_name"],"nota_humana":b["notes"],"bbox_xyxy":b["bbox_xyxy"]})
        for i,b in enumerate(tapas):
            m=medidas(b["bbox_xyxy"],ancho,alto);parent=b.get("parent_envase_box_id")
            if parent and parent not in padres:raise ValueError("Enlace sin envase del mismo frame")
            for key in ("partial","occluded","not_evaluable"):
                resumen[f"{key}:{b.get(key)}"]+=1
            resumen["tapas"]+=1;resumen["con_enlace" if parent else "sin_enlace"]+=1
            resumen["pequenas_640"]+=m["pequena_640_menor16"]
            porvideo[frame["video_id"]]["TAPA"]+=1
            porvideo[frame["video_id"]]["con_enlace" if parent else "sin_enlace"]+=1
            x,y,x2,y2=b["bbox_xyxy"];crop=image[math.floor(y):math.ceil(y2),math.floor(x):math.ceil(x2)].copy()
            gris=cv2.cvtColor(crop,cv2.COLOR_BGR2GRAY);m["laplaciano_roi_nativa"]=float(cv2.Laplacian(gris,cv2.CV_64F).var())
            m["aviso_posible_desENFOQUE_no_etiqueta"]=m["laplaciano_roi_nativa"]<50
            item={"sample_id":sid,"video_id":frame["video_id"],"frame_index":frame["frame_index"],"pts_seconds":frame["pts_seconds"],"image_sha256":frame["image_sha256"],"box":b,"medidas":m,"condicion_colocacion":"NO_ANOTADA_ESTRUCTURADAMENTE","ausencia_tapa":"NO_EVALUADA","sesion":None,"crop_sha256_pixels":hashlib.sha256(crop.tobytes()).hexdigest()}
            registros.append(item)
            for otra in tapas[i+1:]:
                valor=iou(b["bbox_xyxy"],otra["bbox_xyxy"])
                if valor>=.8:solapes.append({"sample_id":sid,"a":b["box_id"],"b":otra["box_id"],"iou":valor})
            # Contexto por caja y crop visibles; son referencias humanas, no detecciones.
            dib=image.copy();cv2.rectangle(dib,(round(x),round(y)),(round(x2),round(y2)),(0,170,255),3)
            nombre=f"tapa_{len(registros):03d}";assert cv2.imwrite(str(salida/"imagenes"/(nombre+"_contexto.jpg")),dib)
            assert cv2.imwrite(str(salida/"imagenes"/(nombre+"_crop.png")),crop)
    guardados=leer(ROOT/"output/experimental_pilotos/evaluacion_deteccion_v002_001/conflictos_semanticos.json")
    assert {(c['sample_id'],c['box_id']) for c in conflictos}=={(c['sample_id'],c['box_id']) for c in guardados}
    assert len(registros)==136 and len(conflictos)==7
    # Copia independiente; los guardados humanos futuros anexan revisiones aquí.
    copia.mkdir();shutil.copy2(REFERENCIAS/"manifest.json",copia/"manifest.json")
    for carpeta in ("images","revisions"):
        shutil.copytree(REFERENCIAS/carpeta,copia/carpeta)
    if (REFERENCIAS/"grouping_revisions").exists():shutil.copytree(REFERENCIAS/"grouping_revisions",copia/"grouping_revisions")
    guardar(copia/"IMPORTACION_AUDITADA.json",{"origen":REFERENCIAS.relative_to(ROOT).as_posix(),"archivos_importados":{p.relative_to(copia).as_posix():sha(p) for p in copia.rglob('*') if p.is_file()},"estado":"SIN_ADJUDICACIONES_NUEVAS","uso":"Revisión humana; no etiquetas automáticas"})
    crops=defaultdict(list)
    for n,item in enumerate(registros,1):crops[item["crop_sha256_pixels"]].append(n)
    datos={"resumen":dict(resumen),"por_video":{k:dict(v) for k,v in porvideo.items()},"videos_metadata":[{k:v.get(k) for k in ("video_id","original_filename","session_id","license","rights_holder","capture_date","source_status")} for v in manifest['videos']],"conflictos":conflictos,"duplicados_imagen_exactos":[v for v in exactas.values() if len(v)>1],"duplicados_crop_pixeles":[v for v in crops.values() if len(v)>1],"parejas_dhash_candidatas":duplicados_visuales(manifest['frames']),"solapamientos_caja_iou080":solapes,"cajas_tapa":registros}
    guardar(salida/"auditoria_tapas.json",datos);guardar(salida/"protegidos_antes.json",protegido)
    style='<style>body{font:15px system-ui;background:#f3f6f9;color:#182d43;margin:25px}article{border-top:2px solid #b6c6d4;padding:20px 0}.paneles{display:grid;grid-template-columns:1fr 1fr;gap:14px}img{max-width:100%;height:auto}figure{margin:0}pre{white-space:pre-wrap;overflow-wrap:anywhere}.aviso{background:#fff0ce;padding:18px}a{color:#165fba}@media(max-width:750px){.paneles{display:block}}</style>'
    cabecera='<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'+style+'</head><body>'
    def original(sid):return os.path.relpath(REFERENCIAS/refs[sid]['source']['image'],salida).replace('\\','/')
    cards=[]
    for n,c in enumerate(conflictos,1):
        im=imagenes[c['sample_id']].copy();x,y,x2,y2=c['bbox_xyxy'];cv2.rectangle(im,(round(x),round(y)),(round(x2),round(y2)),(0,0,255),4)
        assert cv2.imwrite(str(salida/'imagenes'/f'conflicto_{n:02d}.jpg'),im)
        cards.append('<article><h2>Conflicto '+str(n)+' · '+c['sample_id']+'</h2><div class="paneles"><figure><figcaption>Original sin alterar</figcaption><a href="'+original(c['sample_id'])+'"><img src="'+original(c['sample_id'])+'" alt="Imagen original"></a></figure><figure><figcaption>Caja humana registrada ENVASE; no reclasificada</figcaption><img src="imagenes/conflicto_'+f'{n:02d}'+'.jpg" alt="Caja en conflicto"></figure></div><pre>'+html.escape(json.dumps(c,ensure_ascii=False,indent=2))+'</pre><p><a href="http://127.0.0.1:8792/" target="_blank" rel="noopener">Abrir anotador existente en copia de revisión</a> · Seleccione el sample_id indicado y la caja por ID. Autor real, observación de adjudicación y nueva revisión; no cambia el original.</p></article>')
    (salida/'index.html').write_text(cabecera+'<h1>Siete conflictos para adjudicación humana</h1><p class="aviso">No se ha corregido ninguna clase. Colocación, ausencia y defecto no se deducen de nombres o notas. La revisión usa una copia con historial preservado y requiere una decisión humana.</p><p><a href="tapas.html">Auditar las 136 cajas TAPA</a> · <a href="INFORME.md">Informe y plan de datos</a> · <a href="REVISION_HUMANA.md">Cómo adjudicar</a></p>'+''.join(cards)+'</body></html>',encoding='utf-8')
    cards=[]
    for n,item in enumerate(registros,1):
        cards.append(f'<article id="tapa_{n:03d}"><h2>TAPA {n:03d} · '+item['sample_id']+'</h2><div class="paneles"><img loading="lazy" src="imagenes/'+f'tapa_{n:03d}_contexto.jpg'+'" alt="Contexto con caja TAPA humana"><img loading="lazy" src="imagenes/'+f'tapa_{n:03d}_crop.png'+'" alt="Recorte de la caja humana"></div><pre>'+html.escape(json.dumps(item,ensure_ascii=False,indent=2))+'</pre></article>')
    (salida/'tapas.html').write_text(cabecera+'<h1>Auditoría de las 136 cajas humanas TAPA</h1><p>Los atributos parcial/ocluido son humanos. Un enlace no demuestra colocación y la falta de enlace no demuestra tapa suelta. Avisos de tamaño/desenfoque son indicadores técnicos, no adjudicación.</p><a href="index.html">Volver a conflictos</a>'+''.join(cards)+'</body></html>',encoding='utf-8')
    for start in range(0,len(registros),24):
        lienzo=np.full((4*200,6*220,3),245,dtype=np.uint8)
        for j,item in enumerate(registros[start:start+24]):
            n=start+j+1;im=cv2.imread(str(salida/'imagenes'/f'tapa_{n:03d}_crop.png'));h,w=im.shape[:2];factor=min(208/w,155/h);im=cv2.resize(im,(max(1,round(w*factor)),max(1,round(h*factor))))
            yy=(j//6)*200;xx=(j%6)*220;lienzo[yy+25:yy+25+im.shape[0],xx:xx+im.shape[1]]=im
            cv2.putText(lienzo,f'TAPA {n:03d} {item["frame_index"]}',(xx+3,yy+18),cv2.FONT_HERSHEY_SIMPLEX,.45,(0,0,0),1)
        assert cv2.imwrite(str(salida/'contactos'/f'contacto_{start//24+1:02d}.jpg'),lienzo)
    changed=[p for p,h in protegido.items() if sha(ROOT/p)!=h]
    if changed:raise RuntimeError('Fuentes protegidas cambiadas: '+str(changed))
    guardar(salida/'verificacion_integridad.json',{"archivos_intactos":len(protegido),"alterados":changed,"anotaciones_nuevas":0,"entrenamientos":0})
    print(json.dumps({"resumen":datos['resumen'],"por_video":datos['por_video'],"duplicados_exactos":datos['duplicados_imagen_exactos'],"crops_repetidos":datos['duplicados_crop_pixeles'],"candidatos_dhash":len(datos['parejas_dhash_candidatas']),"solapes":len(solapes),"copia_revision":copia.relative_to(ROOT).as_posix()},ensure_ascii=False))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--salida',type=Path,required=True);parser.add_argument('--copia-revision',type=Path,required=True)
    a=parser.parse_args();ejecutar(a.salida,a.copia_revision)
