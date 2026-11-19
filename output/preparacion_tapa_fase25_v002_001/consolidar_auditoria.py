"""Consolida evidencia de auditoría; no entrena ni cambia fuentes."""
import hashlib
import html
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PREV = ROOT / 'output/auditoria_roboflow_v4_v002_002'
RAW = ROOT / 'datasets/publicos_calidad_botellas/raw/roboflow_bottle_v4/extracted/train'
def read(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))
def write(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1024*1024), b''):
            h.update(b)
    return h.hexdigest()

coco = read(RAW / '_annotations.coco.json')
inventory = {r['image_id']: r for r in read(PREV / 'inventario_v4.json')}
splits = {r['image_id']: r for line in (PREV / 'propuesta_particiones_actualizada.jsonl').read_text(encoding='utf-8').splitlines() if (r := json.loads(line)).get('source') == 'roboflow_bottle_v4'}
# La propuesta genérica tenía cuarentenas por imagen debidas a otras clases.
# Para TAPA, cualquier propuesta de separación se conserva por grupo completo.
group_partition = {}
for r in splits.values():
    if r['proposed_partition'] in ('train', 'val', 'validation', 'test'):
        previous = group_partition.setdefault(r['group_id'], r['proposed_partition'])
        assert previous == r['proposed_partition']
caps = [a for a in coco['annotations'] if a['category_id'] == 1]
assert len(caps) == 180 and len(inventory) == 262
issues = {
    31: ('CAJA_INCORRECTA', 'Delimita la botella completa, no la tapa.'),
    123: ('CAJA_INCORRECTA', 'Delimita la botella completa, no la tapa.'),
    204: ('CAJA_INCORRECTA', 'Delimita la etiqueta del cuerpo; la tapa azul está fuera de la caja.'),
    567: ('CAJA_INCORRECTA', 'Delimita la botella completa, no la tapa; marca Shutterstock visible.'),
    134: ('DUDOSA_REQUIERE_ADJUDICACION', 'Región de cuello/boca: no confirmar tapa física sin revisión humana.'),
    324: ('DUDOSA_REQUIERE_ADJUDICACION', 'Región de boca aparentemente abierta: requiere adjudicación humana.'),
    773: ('DUDOSA_REQUIERE_ADJUDICACION', 'Rosca/boca azul: no confirmar tapa física sin revisión humana.'),
}
records = []
for a in caps:
    im = inventory[a['image_id']]
    x,y,w,h = a['bbox']
    status, note = issues.get(a['id'], ('SIN_ALERTA_EN_INSPECCION_VISUAL', 'Sin adjudicación humana nueva; no equivale a etiqueta certificada.'))
    records.append(dict(annotation_original=a, image_sha256=im['sha256'], group_id=splits[a['image_id']]['group_id'], estado_auditoria=status, observacion_tecnica=note, autor_tipo='ASISTENTE_AUDITOR_NO_ADJUDICADOR', visibilidad_humana=None, min_side_at_640=min(w,h)*640/max(im['width'],im['height']), touches_border=min(x,y,im['width']-x-w,im['height']-y-h)<=1))
write('auditoria_180_cajas.json', records)
bad_images = {a['image_id'] for a in caps if a['id'] in issues} | {24}
manifest = []
for im in coco['images']:
    i = im['id']; source = inventory[i]; part = splits[i]
    assert sha(RAW / im['file_name']) == source['sha256']
    annotations = [a for a in caps if a['image_id'] == i]
    manifest.append(dict(image_id=i, source_image=str((RAW / im['file_name']).relative_to(ROOT)).replace('\\','/'), sha256=source['sha256'], width=im['width'], height=im['height'], source_annotations_cap=annotations, proposed_class='TAPA', group_id=part['group_id'], proposed_partition=group_partition.get(part['group_id'], 'PENDIENTE'), partition_approved=False, training_approved=False, mapping_approved=False, negative_confirmed=None, annotation_exhaustivity='NO_VERIFICADA', visibility_reference=None, targeted_review=i in bad_images, status='BLOQUEADO_AUDITORIA_SEMANTICA_Y_COBERTURA'))
(OUT / 'dataset_candidato.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False)+'\n' for r in manifest), encoding='utf-8')
groups = {}
for r in manifest:
    g = groups.setdefault(r['group_id'], dict(proposed_partition=r['proposed_partition'], image_ids=[], cap_boxes=0, approved=False, capture_session_confirmed=False))
    assert g['proposed_partition'] == r['proposed_partition']
    g['image_ids'].append(r['image_id']); g['cap_boxes'] += len(r['source_annotations_cap'])
assert len(groups) == 14
assert sum(len(r['source_annotations_cap']) for r in manifest) == 180
assert len({r['sha256'] for r in manifest}) == 262
assert all(r['training_approved'] is False and r['negative_confirmed'] is None for r in manifest)
prior_constraint = read(ROOT / 'output/auditoria_roboflow_v4_v002_001/restricciones_202_grupos.json')
assert sha(ROOT / prior_constraint['origen']) == prior_constraint['sha256']
write('manifiesto_particiones.json', dict(status='PROPUESTA_NO_APROBADA', groups=groups, previous_202_groups=prior_constraint, human_reference_excluded=True, reason='Semántica, exhaustividad e independencia pendientes; no exportar como dataset listo.'))
write('decision_entrenamiento.json', dict(training_authorized_by_audit=False, training_executed=False, inference_executed=False, metrics=None, weights_created=[], reason='Cuatro cajas incorrectas, tres dudosas, tapas visibles sin anotar y separación por procedencia no certificada.'))
summary = dict(images=262, cap_images=len({a['image_id'] for a in caps}), cap_boxes=180, confirmed_box_errors=4, semantic_suspects=3, cap_boxes_under_16px_at_640=sum(r['min_side_at_640']<16 for r in records), border_flags=sum(r['touches_border'] for r in records), groups=14, human_visibility_counts=None, proposed_partition_counts=dict(Counter(r['proposed_partition'] for r in manifest)), image24_cap_boxes=sum(a['image_id']==24 for a in caps), checks='PASS: hashes 262, 180 cajas originales, 14 grupos indivisibles, sin negativos inventados, referencia propia excluida')
write('resumen_auditoria.json', summary)
cards = []
for a in caps:
    if a['id'] in issues:
        status, note = issues[a['id']]
        cards.append(f'<article><h2>Anotación {a["id"]} · imagen {a["image_id"]}</h2><p>{html.escape(status)}: {html.escape(note)}</p><p>Clase original: cap. Caja original: {html.escape(str(a["bbox"]))}. No corregida.</p><img loading="lazy" src="contextos/annotation_{a["id"]}.jpg" alt="Caja original cap {a["id"]}"></article>')
cards.append('<article><h2>Imagen 24 · exhaustividad</h2><p>Una caja cap registrada para el primer plano. Hay tapas verdes visibles sin cajas al fondo. Debe definirse el alcance de evaluación o adjudicar las omisiones; no tratarlas automáticamente como negativos.</p><img src="contextos/annotation_76.jpg" alt="Escena con tapas de fondo sin referencia"></article>')
gallery = '<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Auditoría TAPA Fase 2.5</title><style>body{font:16px system-ui;background:#101923;color:#edf3fa;margin:24px;max-width:1200px}article{background:#1b2938;padding:18px;margin:20px 0;border-radius:12px}img{max-width:100%;height:auto}a{color:#8cd3ff}</style><h1>TAPA · Auditoría previa al entrenamiento</h1><p>Entrenamiento detenido. Observaciones técnicas; no sustituyen adjudicación humana. No hay predicciones ni métricas nuevas.</p><a href="INFORME.md">Informe</a> · <a href="auditoria_180_cajas.json">Auditoría de cajas</a>' + ''.join(cards) + '<h2>Inspección completa de 180 cajas originales</h2>' + ''.join(f'<article><img loading="lazy" src="contactos/cap_{i:02d}.jpg" alt="Hoja de cajas {i}"></article>' for i in range(1,9)) + '<h2>14 grupos provisionales</h2><img loading="lazy" src="grupos_principales.jpg" alt="Cuatro grupos principales"><img loading="lazy" src="grupos_otros.jpg" alt="Diez grupos restantes"></html>'
(OUT / 'index.html').write_text(gallery, encoding='utf-8')
print(json.dumps(summary, ensure_ascii=False))

protected = read(ROOT / 'output/auditoria_datasets_calidad_v002_001/protegidos_antes.json')
changed = [p for p,h in protected.items() if not (ROOT/p).is_file() or sha(ROOT/p) != h]
raw_hash = sha(RAW / '_annotations.coco.json')
assert raw_hash == '06dd4e05a2c6c35c3244dcf62840eeb00759ea340726d58868dd87a8362c7f54'
write('verificacion_integridad.json', dict(previous_files_checked=len(protected), changed=changed, v4_images_verified=262, raw_coco_sha256=raw_hash, previous_202_group_manifest_unchanged=True))
assert not changed, changed
print(f'Integridad: {len(protected)} archivos anteriores sin cambios.')
