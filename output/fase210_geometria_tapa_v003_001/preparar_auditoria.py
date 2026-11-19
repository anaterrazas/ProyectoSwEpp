"""Registra la criba técnica conforme al protocolo; no corrige coordenadas."""
from pathlib import Path
from collections import Counter
import hashlib
import json

ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
def rows(p):return [json.loads(s) for s in p.read_text(encoding='utf-8').splitlines() if s]
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def dump(name,data):
    with (OUT/name).open('x',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False,indent=2)

source=rows(ROOT/'output/fase29_consolidacion_tapa_v003_001/candidatas_v26.jsonl')
reserve=rows(ROOT/'output/fase28_suficiencia_tapa_v003_001/subconjunto_minimo_candidato.jsonl')
keep={54,147,224,238}
records=[]
for r in source:
    x,y,w,h=r['source_annotation']['bbox_xywh_pixels']
    status='CONSERVAR' if r['index'] in keep else 'REQUIERE AJUSTE HUMANO'
    records.append(dict(case_id=r['index'],source='roboflow_caps_v26',source_sample_id=r['sample_id'],
        source_image=r['source_image'],sha256=r['image_sha256'],width=r['width'],height=r['height'],
        group_id=r['group_id'],source_class=r['source_class'],source_annotation=r['source_annotation'],
        bbox_original_xyxy=[x,y,x+w,y+h],audit_status=status,
        audit_note='La tapa y banda unida quedan dentro; el límite inferior no se prolonga a la brida/cuello. Conservar coordenadas fuente, sujeto a revisión humana independiente.' if status=='CONSERVAR' else 'ROI de estado de tapa con cuello/brida o contexto exterior innecesario; requiere delimitar manualmente tapa y anillo unido. Los casos próximos al límite pueden confirmarse como CONSERVAR por una persona.',
        audit_kind='CRIBA_TECNICA_ASISTENTE_NO_ADJUDICACION_HUMANA',training_approved=False))
for j,r in enumerate(reserve,272):
    from PIL import Image
    with Image.open(ROOT/r['source_image']) as im:width,height=im.size
    a=r['source_annotations_cap'][0];x,y,w,h=a['bbox']
    records.append(dict(case_id=j,source='roboflow_bottle_v4',source_sample_id=f'v4:image:{r["image_id"]}',image_id=r['image_id'],
        source_image=r['source_image'],sha256=r['sha256'],width=width,height=height,group_id=r['group_id'],source_class='cap',
        source_annotation=a,bbox_original_xyxy=[x,y,x+w,y+h],audit_status='REQUIERE AJUSTE HUMANO',
        audit_note='La tapa física está visible; confirmar y ajustar si procede el límite de anillo unido frente a cuello con la nueva convención. No conservar como referencia estricta automáticamente.',
        audit_kind='CRIBA_TECNICA_ASISTENTE_NO_ADJUDICACION_HUMANA',training_approved=False,independent_test_approved=False))
for r in records:assert sha(ROOT/r['source_image'])==r['sha256']
dump('catalogo.json',records)
dump('resumen_auditoria.json',dict(v26=dict(Counter(r['audit_status'] for r in records if r['source']=='roboflow_caps_v26')),
    v26_total=272,conservar_indices=sorted(keep),no_evaluables_v26=0,
    reserva_v4_total=12,reserva_v4_status='REQUIERE_REVISION_MANUAL_LIMITE_SEGUN_NUEVA_CONVENCION',
    tipo='AUDITORIA_TECNICA_PROVISIONAL_NO_NUEVAS_DECISIONES_HUMANAS',coordenadas_modificadas=0,
    protocolo='docs/PROTOCOLO_TAPA_GEOMETRIA_v1.md',protocolo_sha256=sha(ROOT/'docs/PROTOCOLO_TAPA_GEOMETRIA_v1.md'),
    entrenamiento_autorizado=False,estado='NO_PREPARADO_AJUSTES_Y_TEST_PENDIENTES'))
print((OUT/'resumen_auditoria.json').read_text(encoding='utf-8'))
