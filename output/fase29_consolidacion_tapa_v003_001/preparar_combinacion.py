"""Índice experimental multifuente por referencias; no exporta etiquetas nuevas."""
from collections import Counter, defaultdict
import hashlib
import html
import json
from pathlib import Path

import cv2
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
DATA=ROOT/'datasets/calidad_botellas/v003/tapa_multifuente_candidato_001'
import sys
sys.path.insert(0,str(ROOT))
from ml.calidad_botellas.audit_visual import inspect_image

def rows(p):return [json.loads(s) for s in p.read_text(encoding='utf-8').splitlines() if s]
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def dump(p,data):
    with p.open('x',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False,indent=2)
def jsonl(p,data):
    with p.open('x',encoding='utf-8') as f:
        for r in data:f.write(json.dumps(r,ensure_ascii=False)+'\n')

if DATA.exists():raise FileExistsError('No sobrescribir dataset anterior')
v26=rows(OUT/'candidatas_v26.jsonl')
v4=rows(ROOT/'output/fase28_suficiencia_tapa_v003_001/subconjunto_minimo_candidato.jsonl')
combined=[]
for r in v26:
    a=r['source_annotation']
    combined.append(dict(sample_id=r['sample_id'],source='roboflow_caps_v26',source_version='26',
        image=r['source_image'],image_sha256=r['image_sha256'],width=r['width'],height=r['height'],
        group_id=r['group_id'],capture_date_proxy=r['capture_date_proxy'],source_annotations=[a],
        candidate_target='TAPA',geometry_convention='ROI_CAP_CON_ANILLO_Y_CONTEXTO_DE_CUELLO',
        source_class=r['source_class'],source_url=r['source_url'],source_creators=r['source_creators'],
        license=r['license'],license_url=r['license_url'],source_occurrences=r['source_occurrences'],
        compatibility='TAPA_FISICA_VISIBLE_EN_ROI_FUENTE_NO_CAJA_AJUSTADA_CERTIFICADA',
        foreground_cap_count_visual=1,technical_visual_screening=True,human_adjudication_new=False,
        mapping_approved=False,training_approved=False,partition_approved=False,negative_confirmed=None,
        proposed_partition='train' if r['capture_date_proxy']=='20220701' else 'validation'))
for r in v4:
    combined.append(dict(sample_id=f'roboflow_bottle_v4:image:{r["image_id"]}',source='roboflow_bottle_v4',source_version='4',
        image=r['source_image'],image_sha256=r['sha256'],width=None,height=None,group_id=r['group_id'],capture_date_proxy=None,
        source_annotations=r['source_annotations_cap'],candidate_target='TAPA',geometry_convention='CAP_COCO_FUENTE_V4',
        source_class='cap',source_url='https://universe.roboflow.com/spark-intelligence-scqhh/bottle-defect-detection/dataset/4',
        source_creators=['Spark Intelligence'],license='CC-BY-4.0',license_url='https://creativecommons.org/licenses/by/4.0/',
        compatibility='NUCLEO_VISUAL_PREVIO_PROCEDENCIA_INDIVIDUAL_PENDIENTE',technical_visual_screening=True,
        human_adjudication_new=False,mapping_approved=False,training_approved=False,partition_approved=False,
        negative_confirmed=None,proposed_partition='RESERVA_SIN_TEST_INDEPENDIENTE'))
assert len(combined)==284 and len({r['image_sha256'] for r in combined})==284
desc=[];quality=[]
for r in combined:
    metrics,preview,ph,dh,color=inspect_image(ROOT/r['image'],r['image_sha256'])
    assert metrics['actual_sha256']==r['image_sha256']
    r['width']=metrics['width'];r['height']=metrics['height']
    gray=cv2.resize(cv2.cvtColor(preview,cv2.COLOR_BGR2GRAY),(64,64),interpolation=cv2.INTER_AREA)
    desc.append((ph,dh,color,gray,metrics['aspect_ratio']))
    bbox=r['source_annotations'][0].get('bbox_xywh_pixels') or r['source_annotations'][0]['bbox']
    mins=min(bbox[2:])*640/max(r['width'],r['height'])
    quality.append(dict(sample_id=r['sample_id'],metrics=metrics,min_side_640=mins))
pairs=[]
for i,a in enumerate(desc):
    for j,b in enumerate(desc[:i]):
        ph,dh,color,gray,aspect=a;ph2,dh2,color2,gray2,aspect2=b
        if (ph^ph2).bit_count()>2 or (dh^dh2).bit_count()>4 or abs(aspect-aspect2)>.03:continue
        diff=np.abs(gray.astype(float)-gray2.astype(float));cd=float(np.abs(color.astype(float)-color2.astype(float)).mean()/255)
        if cd<=.025 and float(diff.mean()/255)<=.025 and float((diff>12).mean())<=.04:
            pairs.append(dict(a=combined[i]['sample_id'],b=combined[j]['sample_id'],
                group_a=combined[i]['group_id'],group_b=combined[j]['group_id'],
                cross_group=combined[i]['group_id']!=combined[j]['group_id'],
                cross_source=combined[i]['source']!=combined[j]['source'],
                phash_distance=(ph^ph2).bit_count(),dhash_distance=(dh^dh2).bit_count(),color_difference=cd))
cross=[p for p in pairs if p['cross_group']]
if cross:
    # Nunca presentar como válida una partición atravesada por similitud nueva.
    for r in combined:
        if r['group_id'] in {p[k] for p in cross for k in ('group_a','group_b')}:
            r['proposed_partition']='CUARENTENA_RELACION_ENTRE_GRUPOS'
DATA.mkdir(parents=True)
jsonl(DATA/'samples.candidate.jsonl',combined)
jsonl(DATA/'core_v26.native_roi.jsonl',[r for r in combined if r['source']=='roboflow_caps_v26'])
jsonl(DATA/'reserve_v4.unapproved.jsonl',[r for r in combined if r['source']=='roboflow_bottle_v4'])
group_summary={}
for r in combined:
    d=group_summary.setdefault(r['group_id'],dict(source=r['source'],proposed_partition=r['proposed_partition'],sample_ids=[],capture_date_proxy=r['capture_date_proxy']))
    assert d['proposed_partition']==r['proposed_partition'];d['sample_ids'].append(r['sample_id'])
dump(DATA/'groups.json',dict(groups=group_summary,approved=False,prior_202_groups_unchanged=True,notes='No repartir miembros de un grupo ni confiar en splits originales. Fechas en nombre son proxies, no IDs de botella.'))
licenses=read(ROOT/'output/auditoria_datasets_calidad_v002_001/licencias_y_procedencia.json')
dump(DATA/'licenses.json',dict(evidencia_local_previa=licenses,actualizacion_v4='Exportación adquirida y verificada en auditoria_roboflow_v4_v002_002; registro antiguo local_images=0 es histórico, no disponibilidad actual.',
    v4_acquisition=read(ROOT/'output/auditoria_roboflow_v4_v002_002/adquisicion.json'),
    own25='EXCLUIDAS_DERECHOS_PENDIENTES',rights_guarantee_inferred=False))
exclusions=dict(mendeley=dict(images=7907,boxes=28413,TAPA_direct_boxes=0,reason='Cajas de defectos, no tapas completas. Conservar para superficie; no convertir a positivos o negativos TAPA.'),
    roboflow_v26=dict(images_outside_positive_core=298,boxes_not_mapped=334,source_classes_excluded={'No Cap':162,'Loose Cap':124,'Broken Ring':48},
        reason='No Cap delimita boca; Loose suele delimitar hueco; Ring delimita anillo. No se convierten en TAPA ni negativos automáticamente. Siete cajas Loose coexisten con Broken Cap y se conservan solo como anotaciones fuente.'),
    roboflow_v4=dict(images_outside_visual_core=250,reason='Se conservan resultados de fase28: omisiones, ambigüedad y alertas de origen. No asumir que todas las 173 TAPA candidatas son aprovechables en imágenes completas.'),
    own25=dict(images=25,boxes=244,TAPA=143,ENVASE=101,included=False,reason='Autorización de uso no confirmada.'))
dump(DATA/'exclusions.json',exclusions)
dump(OUT/'similitud_combinada.json',dict(comparisons=284*283//2,pairs=pairs,cross_group_pairs=len(cross),
    exact_duplicates=0,method='Criterios estrictos de audit_visual reutilizados; similitud no demuestra identidad física ni independencia.'))
dump(OUT/'quality_combined.json',quality)
summary=dict(total_candidatas=284,cajas_fuente=284,por_fuente={'roboflow_caps_v26':272,'roboflow_bottle_v4':12,'mendeley':0,'referencia_propia':0},
    cajas_roi_cap_v26=272,cajas_TAPA_estrictas_nuevas_humanas=0,cajas_cap_v4_previamente_candidatas=12,
    source_classes_v26=dict(Counter(r['source_class'] for r in v26)),grupos_con_fuente=8,grupos_fecha_v26=2,grupos_visuales_v4=6,
    particiones=dict(Counter(r['proposed_partition'] for r in combined)),grupos_por_particion=dict(Counter(r['proposed_partition'] for r in group_summary.values())),
    min_side_640_by_source={s:dict(min=min(q['min_side_640'] for q,r in zip(quality,combined) if r['source']==s),max=max(q['min_side_640'] for q,r in zip(quality,combined) if r['source']==s)) for s in ('roboflow_caps_v26','roboflow_bottle_v4')},
    blancos_v26=272,colores_v4_descripcion='Tapas azules, verdes y turquesa, fotos de producto y botellas en suelo; sin aumentar artificialmente número de orígenes.',
    falta='Convención física de caja consistente; test reservado con procedencia e independencia justificadas; más diversidad de tamaño/escena para generalización a video.',
    entrenamiento_autorizado=False,estado='CANDIDATO_AMPLIADO_ROI_FUENTE_NO_PREPARADO_COMO_TAPA_ESTRICTA_CON_TEST_INDEPENDIENTE',
    solicitar_nuevas_capturas_ahora=False,inferencias=0,entrenamientos=0)
dump(OUT/'resumen_consolidacion.json',summary)
dump(DATA/'manifest.json',dict(format='CANDIDATO_MULTIFUENTE_REFERENCIAS_SEPARADAS_NO_EXPORT_YOLO',status=summary['estado'],training_approved=False,
    sha256={p.name:sha(p) for p in DATA.iterdir() if p.is_file()}))
cards=''.join(f'<details><summary>{i:03d} · {html.escape(r["source_class"])} · {r["capture_date_proxy"]} · {r["image_sha256"][:12]}</summary><img loading="lazy" src="contextos/{i:03d}.jpg" alt="ROI fuente de tapa {i}"><p>Coordenadas: {html.escape(str(r["source_annotation"]["bbox_xywh_pixels"]))}. Convención con contexto, no reajustada.</p></details>' for i,r in enumerate(v26))
page='<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Consolidación TAPA · Fase 2.9</title><style>body{font:16px system-ui;max-width:1300px;margin:25px;background:#122033;color:#eef5ff}a{color:#8cd4ff}details{padding:15px;background:#21354e;margin:12px 0}img{max-width:100%;height:auto}summary{cursor:pointer}</style><h1>TAPA · Consolidación de fuentes</h1><p>272 ROI de v26 con tapa física visible, más 12 imágenes candidatas v4. No son 284 cajas estrictas ajustadas y aprobadas ni un test independiente. No se entrenó ni infirió.</p><a href="INFORME.md">Informe y decisión</a><h2>Criba de las 272 regiones</h2>'+''.join(f'<details><summary>Hoja de regiones {i}</summary><img loading="lazy" src="contactos/v26_{i:02d}.jpg" alt="Regiones de tapas, hoja {i}"></details>' for i in range(1,15))+'<h2>Escenas completas</h2>'+''.join(f'<details><summary>Escenas {i}</summary><img loading="lazy" src="contactos/escenas_{i:02d}.jpg" alt="Escenas, hoja {i}"></details>' for i in range(1,7))+'<h2>Contextos individuales</h2>'+cards+'</html>'
with (OUT/'index.html').open('x',encoding='utf-8') as f:f.write(page)
print(json.dumps(summary,ensure_ascii=False,indent=2))
