"""Inspección de cajas públicas existentes, sin modelos ni reanotación."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[2]
IMPORT=ROOT/'datasets/publicos_calidad_botellas/imports/roboflow_caps_v26_001'


def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def readrows(p):return [json.loads(s) for s in p.read_text(encoding='utf-8').splitlines() if s]


def dump(p,data):
    with p.open('x',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False,indent=2)


def inspeccionar(out):
    out=out.resolve()
    if not out.is_relative_to(ROOT/'output') or out.exists():raise ValueError('Solo salida nueva experimental')
    rows=readrows(IMPORT/'samples.public.jsonl')
    splits={r['sample_id']:r for r in readrows(ROOT/'datasets/publicos_calidad_botellas/selections/pretrain_v001/split_proposal.jsonl')}
    out.mkdir(parents=True);(out/'contactos').mkdir();(out/'contextos').mkdir()
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
    records=[];all_classes=Counter();annotations={};dates=defaultdict(Counter)
    for r in rows:
        p=IMPORT/r['image']
        if sha(p)!=r['image_sha256']:raise ValueError('Hash de imagen incompatible')
        raw=ROOT/'datasets/publicos_calidad_botellas/raw/roboflow_caps_v26/extracted'/r['source_occurrences'][0]['relative']
        if sha(raw)!=r['image_sha256']:raise ValueError('RAW de imagen incompatible')
        image=Image.open(p).convert('RGB')
        if image.size!=(r['width'],r['height']):raise ValueError('Dimensiones incompatibles')
        group=splits[r['sample_id']]['group_id']
        m=re.search(r'WIN_(\d{8})',r['filename_source_groups'][0]);day=m.group(1) if m else None
        anns=[a for o in r['source_occurrences'] for a in o['annotations']]
        dates[str(day)].update(a['source_class'] for a in anns)
        for o in r['source_occurrences']:
            f=ROOT/'datasets/publicos_calidad_botellas/raw/roboflow_caps_v26/extracted'/o['annotation_file']
            annotations[str(f.relative_to(ROOT))]=o['annotation_sha256']
        for a in anns:
            all_classes[a['source_class']]+=1
            x,y,w,h=a['bbox_xywh_pixels']
            if not (0<=x<x+w<=r['width'] and 0<=y<y+h<=r['height']):raise ValueError('Geometría inválida')
            if a['source_class'] not in ('Good Cap','Broken Cap'):continue
            index=len(records)
            record=dict(index=index,sample_id=r['sample_id'],image_sha256=r['image_sha256'],source_image=str(p.relative_to(ROOT)).replace('\\','/'),
                        width=r['width'],height=r['height'],group_id=group,capture_date_proxy=day,
                        source_class=a['source_class'],source_annotation=a,
                        full_image_annotation_count=len(anns),license=r['license'],license_url=r['license_url'],source_url=r['source_url'],
                        source_creators=r['source_creators'],source_occurrences=r['source_occurrences'],
                        candidate_class='TAPA',mapping_approved=False,training_approved=False,
                        convention='CAJA_FUENTE_DE_ESTADO_CAP_PUEDE_INCLUIR_ANILLO_O_CUELLO',
                        bbox_min_side_640=min(w,h)*640/max(r['width'],r['height']))
            records.append(record)
            context=image.copy();d=ImageDraw.Draw(context);d.rectangle([x,y,x+w,y+h],outline='red',width=8)
            context.thumbnail((960,540));context.save(out/'contextos'/f'{index:03d}.jpg',quality=91)
    for p,h in annotations.items():
        if sha(ROOT/p)!=h:raise ValueError('Anotaciones RAW incompatibles')
    # 20 recortes por hoja: contexto alrededor de la caja fuente, no caja nueva.
    for start in range(0,len(records),20):
        sheet=Image.new('RGB',(1600,1420),'#e9eef4');d=ImageDraw.Draw(sheet)
        for off,r in enumerate(records[start:start+20]):
            x0=(off%4)*400;y0=(off//4)*284
            a=r['source_annotation'];x,y,w,h=a['bbox_xywh_pixels'];im=Image.open(ROOT/r['source_image']).convert('RGB')
            left=max(0,int(x-.18*w));top=max(0,int(y-.25*h));right=min(im.width,int(x+w*1.18));bottom=min(im.height,int(y+h*1.25))
            crop=im.crop((left,top,right,bottom));dd=ImageDraw.Draw(crop);dd.rectangle([x-left,y-top,x+w-left,y+h-top],outline='red',width=6)
            crop.thumbnail((390,237));sheet.paste(crop,(x0+(400-crop.width)//2,y0+44))
            d.text((x0+5,y0+2),f'{r["index"]:03d} {r["source_class"]} {r["capture_date_proxy"]}',font=font,fill='black')
            d.text((x0+5,y0+23),r['sample_id'].split(':')[1][:16],font=font,fill='black')
        sheet.save(out/'contactos'/f'v26_{start//20+1:02d}.jpg',quality=94)
    with (out/'candidatas_v26.jsonl').open('x',encoding='utf-8') as f:
        for r in records:f.write(json.dumps(r,ensure_ascii=False)+'\n')
    dump(out/'resumen_v26.json',dict(imagenes_verificadas=len(rows),clases_cajas=dict(all_classes),candidatas_good_broken=len(records),
         imagenes_candidatas=len({r['sample_id'] for r in records}),grupos_candidatos=dict(Counter(r['group_id'] for r in records)),
         por_fecha_proxy={k:dict(v) for k,v in dates.items()},cantidad_anotaciones_por_imagen_candidata=dict(Counter(r['full_image_annotation_count'] for r in records)),
         anotaciones_raw_verificadas=annotations,entrenamiento=False,inferencias=0))
    print((out/'resumen_v26.json').read_text(encoding='utf-8'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--salida',type=Path,required=True)
    inspeccionar(p.parse_args().salida)
