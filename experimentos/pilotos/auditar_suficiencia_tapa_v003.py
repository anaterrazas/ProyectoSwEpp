"""Inspección offline de píxeles, geometría y relaciones; no usa modelos."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
import os
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from ml.calidad_botellas.audit_visual import inspect_image


def guardar(p, data):
    with p.open('x', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, allow_nan=False)


def iou(a,b):
    x=max(a[0],b[0]);y=max(a[1],b[1]);xx=min(a[2],b[2]);yy=min(a[3],b[3])
    intersection=max(0,xx-x)*max(0,yy-y)
    union=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-intersection
    return intersection/union if union>0 else 0


def ejecutar(salida):
    os.environ['DJANGO_SETTINGS_MODULE']='experimentos.pilotos.settings'
    import django
    django.setup()
    from . import revision_tapa_v4 as v
    root=v.ROOT;salida=salida.resolve()
    if not salida.is_relative_to(root/'output') or salida.exists():
        raise ValueError('Solo salida nueva en output')
    records=v.fuente();history=v.generaciones();derived=v.derivar(records,history)
    current={r['image_id']:r for r in derived};latest=v.ultimas(history)
    salida.mkdir(parents=True);(salida/'contactos').mkdir();(salida/'imagenes').mkdir()
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
    rows=[];descriptors=[];boxes=[]
    coco=v.leer(v.RAW/'_annotations.coco.json');groups=defaultdict(list)
    for source in records:
        i=source['image_id'];r=current[i];p=root/source['source_image']
        metrics,preview,ph,dh,color=inspect_image(p,source['sha256'])
        if metrics['flags'].count('hash_mismatch') or (metrics['width'],metrics['height'])!=(source['width'],source['height']):
            raise ValueError('Imagen o dimensiones incompatibles')
        image=cv2.imdecode(np.frombuffer(p.read_bytes(),np.uint8),cv2.IMREAD_COLOR|cv2.IMREAD_IGNORE_ORIENTATION)
        gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY);g64=cv2.resize(gray,(64,64),interpolation=cv2.INTER_AREA)
        descriptors.append((i,ph,dh,color,g64,source['width']/source['height']))
        row=dict(image_id=i,group_id=source['group_id'],proposed_partition=source['proposed_partition'],
                 source_image=source['source_image'],sha256=source['sha256'],metrics=metrics,
                 cobertura_humana=latest[i]['exhaustividad'] if i in latest else 'SIN_REVISION',
                 effective_counts=dict(Counter(b['clase'] for b in r['effective_annotations'])),semantic_automatic_approval=False)
        rows.append(row);groups[source['group_id']].append(i)
        # Superposición derivada para inspección; coordenadas RAW intactas.
        frame=Image.fromarray(cv2.cvtColor(image,cv2.COLOR_BGR2RGB));draw=ImageDraw.Draw(frame)
        normalized=[]
        for b in r['effective_annotations']:
            if 'bbox_xywh' in b:
                x,y,w,h=b['bbox_xywh'];xy=[x,y,x+w,y+h];aid=b['source_annotation_id']
            else:
                xy=b['bbox_xyxy'];x,y,xx,yy=xy;w=xx-x;h=yy-y;aid=b['id']
            valid=all(math.isfinite(n) for n in xy) and 0<=xy[0]<xy[2]<=source['width'] and 0<=xy[1]<xy[3]<=source['height']
            boxes.append(dict(image_id=i,annotation_id=aid,clase=b['clase'],geometria_valida=valid,bbox_xyxy=xy,
                              min_side_640=min(w,h)*640/max(source['width'],source['height']),
                              visibilidad=b.get('visibilidad','NO_REVISADA')))
            if not valid:raise ValueError('Caja no válida')
            color_box='#ffcd38' if b['clase']=='TAPA' else '#52d6ff' if b['clase']=='ENVASE' else '#ff7777'
            draw.rectangle(xy,outline=color_box,width=max(2,source['width']//320))
            draw.text((x,max(0,y-20)),f'{aid} {b["clase"]}',fill=color_box,font=font)
            if b['clase']=='TAPA':normalized.append([xy[0]/source['width'],xy[1]/source['height'],xy[2]/source['width'],xy[3]/source['height']])
        row['normalized_cap_boxes']=normalized
        frame.thumbnail((1000,1000));frame.save(salida/'imagenes'/f'{i:03d}.jpg',quality=92)
    # 34.191 pares: umbral estricto reutilizado y alertas amplias, no identidades.
    pairs=[];broad=[]
    for n,a in enumerate(descriptors):
        for b in descriptors[:n]:
            ia,pa,da,ca,ga,aa=a;ib,pb,db,cb,gb,ab=b
            pd=(pa^pb).bit_count();dd=(da^db).bit_count()
            if pd>12 or dd>16 or abs(aa-ab)>.03:continue
            diff=np.abs(ga.astype(float)-gb.astype(float));graydiff=float(diff.mean()/255)
            colordiff=float(np.abs(ca.astype(float)-cb.astype(float)).mean()/255)
            changed=float(np.mean(diff>12))
            strict=pd<=2 and dd<=4 and graydiff<=.025 and colordiff<=.025 and changed<=.04
            cross=current[ia]['group_id']!=current[ib]['group_id']
            row=dict(a=ia,b=ib,phash_distance=pd,dhash_distance=dd,gray_difference=graydiff,
                     color_difference=colordiff,changed_fraction=changed,cross_group=cross,strict=strict)
            if strict:
                ba=next(r for r in rows if r['image_id']==ia)['normalized_cap_boxes'];bb=next(r for r in rows if r['image_id']==ib)['normalized_cap_boxes']
                row['annotation_disagreement']=len(ba)!=len(bb) or any(not any(iou(x,y)>=.5 for y in bb) for x in ba) or any(not any(iou(x,y)>=.5 for y in ba) for x in bb)
                pairs.append(row)
            elif cross:
                broad.append(row)
    # Hojas sistemáticas: todas las 262, ordenadas por grupo y luego ID.
    order=sorted(rows,key=lambda r:(r['group_id'],r['image_id']))
    for start in range(0,len(order),12):
        sheet=Image.new('RGB',(1600,1110),'#e8edf2');d=ImageDraw.Draw(sheet)
        for offset,r in enumerate(order[start:start+12]):
            x=(offset%4)*400;y=(offset//4)*370
            im=Image.open(salida/'imagenes'/f'{r["image_id"]:03d}.jpg');im.thumbnail((390,315));sheet.paste(im,(x+(400-im.width)//2,y+48))
            d.text((x+5,y+3),f'ID {r["image_id"]}  {r["group_id"]}  {r["effective_counts"]}',font=font,fill='black')
            d.text((x+5,y+24),r['cobertura_humana'],font=font,fill='black')
        sheet.save(salida/'contactos'/f'hoja_{start//12+1:02d}.jpg',quality=94)
    guardar(salida/'inspeccion_262.json',rows);guardar(salida/'geometria_cajas.json',boxes)
    guardar(salida/'similitud_estricta.json',pairs);guardar(salida/'alertas_similitud_amplia.json',broad)
    guardar(salida/'historial_congelado.json',history)
    guardar(salida/'resumen_tecnico.json',dict(imagenes=len(rows),pares_comparados=len(rows)*(len(rows)-1)//2,
        cajas=len(boxes),clases=dict(Counter(b['clase'] for b in boxes)),hashes_unicos=len({r['sha256'] for r in rows}),
        pares_estrictos=len(pairs),pares_estrictos_entre_grupos=sum(p['cross_group'] for p in pairs),
        pares_discrepancia=sum(p.get('annotation_disagreement',False) for p in pairs),alertas_amplias_entre_grupos=len(broad),
        grupos=groups,revision_global=len(history),cobertura_humana=dict(Counter(r['cobertura_humana'] for r in rows)),
        flags_tecnicos=dict(Counter(f for r in rows for f in r['metrics']['flags'])),entrenamientos=0,inferencias=0,
        advertencia='Las métricas de píxel, semejanza y recuento no validan semántica ni exhaustividad.'))
    print((salida/'resumen_tecnico.json').read_text(encoding='utf-8'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--salida',type=Path,required=True)
    ejecutar(p.parse_args().salida)
