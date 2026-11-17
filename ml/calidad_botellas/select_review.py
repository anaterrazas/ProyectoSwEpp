"""Selección humana y propuesta de particiones; no cambia etiquetas ni imágenes."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import random
import re

from .extract_crops import ROOT, sha256

LABELS = ('RAYADURA', 'DEFORMACION', 'TAPA_DEFECTUOSA')
SPLITS = ('train', 'validation', 'test')


class UnionFind:
    def __init__(self, size):
        self.parent = list(range(size))

    def find(self, index):
        while self.parent[index] != index:
            self.parent[index] = self.parent[self.parent[index]]
            index = self.parent[index]
        return index

    def join(self, a, b):
        self.parent[self.find(a)] = self.find(b)


def capture_day(row):
    match = re.search(r'WIN_(\d{8})_', row['file_name'])
    return match[1] if match else None


def origin_groups(rows, visual_groups):
    uf, known = UnionFind(len(rows)), {}
    for i, row in enumerate(rows):
        keys = [('sha256', row['expected_hash'])]
        if row['role'] == 'PUBLIC':
            keys += [('filename_origin', row['source'], group) for group in row['source_groups']]
            day = capture_day(row)
            if day:
                keys.append(('capture_day_proxy', row['source'], day))
        for key in keys:
            if key in known:
                uf.join(i, known[key])
            else:
                known[key] = i
    for group in visual_groups:
        if not group:
            continue
        if any(type(i) is not int or not 0 <= i < len(rows) for i in group):
            raise ValueError('Índice de semejanza fuera del manifiesto')
        for i in group[1:]:
            uf.join(group[0], i)
    members = defaultdict(list)
    reference_roots = {uf.find(i) for i, r in enumerate(rows) if r['role'] != 'PUBLIC'}
    for i, row in enumerate(rows):
        if row['role'] == 'PUBLIC':
            members[uf.find(i)].append(i)
    groups, membership = [], {}
    for root, indices in members.items():
        ids = sorted(rows[i]['sample_id'] for i in indices)
        gid = 'origin-' + hashlib.sha256('\n'.join(ids).encode()).hexdigest()[:16]
        group = {'group_id': gid, 'indices': indices, 'size': len(indices),
                 'sources': sorted({rows[i]['source'] for i in indices}),
                 'capture_day_proxies': sorted({capture_day(rows[i]) for i in indices if capture_day(rows[i])}),
                 'positives': {label: sum(rows[i]['labels'][label] == 1 for i in indices) for label in LABELS},
                 'linked_to_epp_reference': root in reference_roots}
        groups.append(group)
        for i in indices:
            membership[i] = gid
    return sorted(groups, key=lambda g: g['group_id']), membership


def tiny_utility(row, mapping, proposed_size=384):
    boxes = [a for occurrence in row['occurrences'] for a in occurrence['annotations']]
    small = [a for a in boxes if min(a['bbox_xywh_pixels'][2:]) < 16]
    target = [a for a in boxes if a['source_class'] in mapping]
    target_small = [a for a in target if min(a['bbox_xywh_pixels'][2:]) < 16]
    factor = min(1, proposed_size / max(row['expected_width'], row['expected_height']))
    if not small:
        category = 'NO_SMALL_REGION'
    elif not target:
        category = 'OUTSIDE_TARGET_TAXONOMY'
    elif any(flag in row['flags'] for flag in ('possible_blur', 'unreadable_or_damaged', 'hash_mismatch')):
        category = 'TECHNICAL_REVIEW_REQUIRED'
    elif any(min(a['bbox_xywh_pixels'][2:]) >= 16 for a in target):
        category = 'OTHER_LARGER_TARGET_REGION_AVAILABLE'
    elif any(max(a['bbox_xywh_pixels'][2:]) >= 48 and max(a['bbox_xywh_pixels'][2:]) / min(a['bbox_xywh_pixels'][2:]) >= 4 for a in target_small):
        category = 'THIN_ELONGATED_TARGET_POTENTIALLY_USEFUL'
    else:
        category = 'ONLY_SMALL_TARGET_REGIONS_NEEDS_DETAIL'
    return {'category': category, 'small_regions': len(small), 'small_target_regions': len(target_small),
            'target_regions': len(target), 'proposed_input_long_side': proposed_size,
            'small_target_min_sides_projected': [round(min(a['bbox_xywh_pixels'][2:]) * factor, 2) for a in target_small],
            'interpretation': 'Heurística geométrica; no elimina, certifica legibilidad ni cambia etiquetas.'}


def review_cues(row):
    bad = any(flag in row['flags'] for flag in ('unreadable_or_damaged', 'hash_mismatch', 'possible_blur', 'low_resolution'))
    cap_only = set(row['classes']) == {'Good Cap'} and not any(v == 1 for v in row['labels'].values())
    full_view = (row['source'].startswith('mendeley_') and not bad
                 and .35 <= row['metrics']['aspect_ratio'] <= 1.2 and row['expected_height'] >= 512)
    return {'conformity_candidate': 'CAP_GOOD_SOURCE_CUE_ONLY' if cap_only else 'NO_SOURCE_BASIS',
            'conformity_confirmed': None,
            'joint_evaluation': 'FULL_OBJECT_FRAMING_CANDIDATE' if full_view else
                               'CAP_FOCUSED_SOURCE_NEEDS_BODY_VIEW' if row['source'].startswith('roboflow_') else 'TECHNICAL_OR_FRAMING_REVIEW',
            'joint_evaluation_confirmed': None,
            'note': 'Good Cap no prueba conformidad global. Evaluar cuerpo, contorno, tapa y detalle de superficie requiere revisión humana.'}


def propose_splits(groups):
    proposals = {}
    # Reserva temporal explícita: el 13/07 solo aporta tres positivos; nunca ocultar esta limitación.
    cap_days = {'20220704': 'train', '20220705': 'validation', '20220713': 'validation', '20220701': 'test'}
    ordinary = defaultdict(list)
    for group in groups:
        if group['linked_to_epp_reference'] or len(group['sources']) != 1:
            proposals[group['group_id']] = 'HOLD_FOR_REVIEW'
        elif group['sources'][0] == 'roboflow_caps_v26':
            days = group['capture_day_proxies']
            values = {cap_days[d] for d in days if d in cap_days}
            proposals[group['group_id']] = next(iter(values)) if len(values) == 1 and all(d in cap_days for d in days) else 'HOLD_FOR_REVIEW'
        else:
            ordinary[group['sources'][0]].append(group)
    ratios = {'train': .70, 'validation': .15, 'test': .15}
    for source_groups in ordinary.values():
        total = {'images': sum(g['size'] for g in source_groups), **{label: sum(g['positives'][label] for g in source_groups) for label in LABELS}}
        counts = {split: dict.fromkeys(total, 0) for split in SPLITS}
        for group in sorted(source_groups, key=lambda g: (-g['size'], g['group_id'])):
            features = {'images': group['size'], **group['positives']}
            def cost(candidate):
                return sum(((counts[split][key] + (features[key] if split == candidate else 0) - ratios[split] * amount) / max(1, amount)) ** 2 * (1 if key == 'images' else 2)
                           for split in SPLITS for key, amount in total.items() if amount)
            best = min(SPLITS, key=cost)
            proposals[group['group_id']] = best
            for key in total:
                counts[best][key] += features[key]
    return proposals


def select_review(rows, membership, cues, utilities, limit=100, seed=20261114):
    if not 1 <= limit <= 100:
        raise ValueError('La galería debe contener como máximo 100 imágenes')
    chosen, reasons, group_load, visual_used, origins_used = [], {}, Counter(), set(), set()
    rng = random.Random(seed)
    tie = {i: rng.random() for i, row in enumerate(rows) if row['role'] == 'PUBLIC'}
    def take(pool, number, reason):
        available = set(pool) - set(chosen)
        for _ in range(number):
            candidates = [i for i in available if ('visual', rows[i]['source'], rows[i].get('visual_group')) not in visual_used or not rows[i].get('visual_group')]
            if not candidates or len(chosen) >= limit:
                break
            def rank(i):
                original = tuple((rows[i]['source'], g) for g in rows[i]['source_groups'])
                return (any(g in origins_used for g in original), group_load[membership[i]],
                        'possible_blur' in rows[i]['flags'], -min(rows[i]['metrics']['laplacian_512'], 1000) if rows[i]['metrics'] else 0, tie[i])
            index = min(candidates, key=rank)
            chosen.append(index); reasons[index] = reason; available.remove(index)
            group_load[membership[index]] += 1
            if rows[index].get('visual_group'):
                visual_used.add(('visual', rows[index]['source'], rows[index]['visual_group']))
            origins_used.update((rows[index]['source'], g) for g in rows[index]['source_groups'])
    m = [i for i, r in enumerate(rows) if r['role'] == 'PUBLIC' and r['source'].startswith('mendeley_')]
    cap = [i for i, r in enumerate(rows) if r['role'] == 'PUBLIC' and r['source'] == 'roboflow_caps_v26']
    half = limit // 2
    for category in sorted({utilities[i]['category'] for i in m if utilities[i]['small_regions']}):
        take([i for i in m if utilities[i]['category'] == category], min(2, max(0, half - sum(i in m for i in chosen))), 'Regiones pequeñas: ' + category)
    for label in ('RAYADURA', 'DEFORMACION'):
        take([i for i in m if rows[i]['labels'][label] == 1], min(16, half // 3, max(0, half - sum(i in m for i in chosen))), 'Positivo parcial: ' + label)
    remaining = half - sum(i in m for i in chosen)
    take([i for i in m if not any(v == 1 for v in rows[i]['labels'].values())], min(4, remaining), 'Fuera de taxonomía: revisión de cobertura')
    take(m, half - sum(i in m for i in chosen), 'Encuadre y evaluabilidad conjunta por confirmar')
    take([i for i in cap if rows[i]['labels']['TAPA_DEFECTUOSA'] == 1], min(24, half), 'Positivo parcial: TAPA_DEFECTUOSA')
    take([i for i in cap if cues[i]['conformity_candidate'] == 'CAP_GOOD_SOURCE_CUE_ONLY'], min(14, half - sum(i in cap for i in chosen)), 'Good Cap: conformidad global NO confirmada')
    take([i for i in cap if rows[i]['conditional']], max(0, half - sum(i in cap for i in chosen)), 'Mapeo condicional: No Cap / Broken Ring')
    take(cap, max(0, half - sum(i in cap for i in chosen)), 'Diversidad de tapas y sesiones')
    return chosen, reasons


def prepare(audit_root, output, limit=100, seed=20261114):
    audit_root, output = Path(audit_root).resolve(), Path(output).resolve()
    if not output.is_relative_to(ROOT/'datasets/publicos_calidad_botellas/selections'):
        raise ValueError('La selección debe estar fuera de imágenes y anotaciones originales')
    if output.exists():
        raise FileExistsError('No sobrescribir selecciones previas')
    if json.loads((audit_root/'STATUS.json').read_text())['status'] != 'COMPLETED':
        raise ValueError('La auditoría no está completa')
    inputs = {str(audit_root/name): sha256(audit_root/name) for name in ('metrics.jsonl', 'summary.json')}
    rows = [json.loads(line) for line in (audit_root/'metrics.jsonl').read_text(encoding='utf-8').splitlines()]
    audit_summary = json.loads((audit_root/'summary.json').read_text(encoding='utf-8'))
    registry = json.loads(Path(__file__).with_name('public_sources.json').read_text(encoding='utf-8'))['sources']
    groups, membership = origin_groups(rows, audit_summary['visual_candidate_groups'])
    utilities, cues = {}, {}
    for i, row in enumerate(rows):
        if row['role'] != 'PUBLIC':
            continue
        utilities[i] = tiny_utility(row, registry[row['source']]['positive_mapping'])
        cues[i] = review_cues(row)
    proposals = propose_splits(groups)
    selected, reasons = select_review(rows, membership, cues, utilities, limit, seed)
    assignments, review = [], []
    for i, row in enumerate(rows):
        if row['role'] != 'PUBLIC':
            continue
        assignments.append({'sample_id': row['sample_id'], 'source': row['source'], 'image_sha256': row['expected_hash'],
                            'group_id': membership[i], 'proposed_partition': proposals[membership[i]],
                            'labels': row['labels'], 'license': row['license'], 'source_url': row['source_url'],
                            'source_capture_day_proxy': capture_day(row), 'proposal_only': True})
        if i in selected:
            record = {k: row[k] for k in ('sample_id','source','labels','expected_hash','license','license_url','source_url','creators','classes','file_name','scope','flags','semantic_flags')}
            record.update({'group_id': membership[i], 'proposed_partition': proposals[membership[i]],
                           'review_reason': reasons[i], 'tiny_utility': utilities[i], 'review_cues': cues[i],
                           'human_confirmation': None, 'original_url': Path(os.path.relpath(row['path'], output)).as_posix(),
                           'thumbnail': Path(os.path.relpath(audit_root/row['thumbnail'], output)).as_posix() if row.get('thumbnail') else None})
            if sha256(row['path']) != row['expected_hash']:
                raise ValueError('Imagen seleccionada distinta de la auditada')
            review.append(record)
    # Ninguna relación auditada ni grupo nominal puede cruzar particiones.
    for component in groups:
        if len({proposals[membership[i]] for i in component['indices']}) != 1:
            raise AssertionError('Fuga dentro de un componente de origen')
    distribution = {}
    for source in sorted({r['source'] for r in assignments}):
        distribution[source] = {}
        for split in (*SPLITS, 'HOLD_FOR_REVIEW'):
            part = [r for r in assignments if r['source'] == source and r['proposed_partition'] == split]
            distribution[source][split] = {'images': len(part), 'groups': len({r['group_id'] for r in part}),
                                           'positives': {label: sum(r['labels'][label] == 1 for r in part) for label in LABELS}}
    summary = {'seed': seed, 'public_images': len(assignments), 'excluded_epp_reference_images': sum(r['role'] != 'PUBLIC' for r in rows),
               'input_visual_groups': len(audit_summary['visual_candidate_groups']), 'origin_components': len(groups),
               'largest_components': sorted([g['size'] for g in groups], reverse=True)[:10],
               'selected_images': len(review), 'selected_by_source': dict(Counter(r['source'] for r in review)),
               'selected_reasons': dict(Counter(r['review_reason'] for r in review)),
               'selected_label_states': {label: {str(value): sum(r['labels'][label] == value for r in review) for value in (1,0,None)} for label in LABELS},
               'small_region_images': sum(u['small_regions'] > 0 for u in utilities.values()),
               'small_region_utility': dict(Counter(u['category'] for u in utilities.values() if u['small_regions'])),
               'cap_good_source_candidates': sum(c['conformity_candidate'] == 'CAP_GOOD_SOURCE_CUE_ONLY' for c in cues.values()),
               'confirmed_conforming_bottles': 0, 'joint_evaluation_candidates': dict(Counter(c['joint_evaluation'] for c in cues.values())),
               'confirmed_joint_evaluability': 0, 'proposed_distribution': distribution, 'known_link_cross_partition_violations': 0,
               'input_sha256': inputs, 'training_authorized': False,
               'limitations': ['Los componentes protegen relaciones conocidas, no certifican identidad física.',
                               'Fecha inferida del nombre no equivale a una sesión de captura verificada.',
                               'No hay negativos públicos explícitos; no se infieren de Good Cap.',
                               'Good Cap no certifica cuerpo ni conformidad global.',
                               'Evaluabilidad conjunta y utilidad de regiones pequeñas requieren revisión humana.',
                               'Solo tres positivos de tapa en la fecha reservada para validación: calibración insuficiente.']}
    if any(sha256(path) != digest for path, digest in inputs.items()):
        raise ValueError('La auditoría cambió durante la selección')
    output.mkdir(parents=True, exist_ok=False)
    def write_jsonl(name, records):
        (output/name).write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in records),encoding='utf-8')
    write_jsonl('review_selection.jsonl', review)
    write_jsonl('split_proposal.jsonl', assignments)
    write_jsonl('origin_components.jsonl', [{**g, 'sample_ids': [rows[i]['sample_id'] for i in g['indices']], 'proposed_partition': proposals[g['group_id']]} for g in groups])
    write_jsonl('small_region_assessment.jsonl', [{'sample_id': rows[i]['sample_id'], 'source': rows[i]['source'], 'labels': rows[i]['labels'], **u} for i,u in utilities.items() if u['small_regions']])
    (output/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    template = Path(__file__).with_name('selection_gallery.html').read_text(encoding='utf-8')
    payload = json.dumps({'rows':review,'summary':summary},ensure_ascii=True).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    (output/'index.html').write_text(template.replace('SELECTION_DATA_HERE',payload),encoding='utf-8')
    report(output, summary)
    return summary


def report(output, summary):
    lines = ['# Selección previa al entrenamiento multietiqueta', '',
             f"Revisión propuesta: **{summary['selected_images']} imágenes**; distribución por fuente: {json.dumps(summary['selected_by_source'])}.",
             f"Se analizaron {summary['input_visual_groups']} grupos visuales y se generaron **{summary['origin_components']} componentes de origen** uniendo SHA, origen nominal, semejanza y fecha de captura inferida en Roboflow.",
             'Las 19 muestras propias no participan en selección ni particiones; permanecen intactas.', '',
             '## Regiones pequeñas', '', f"Se conservan las {summary['small_region_images']} imágenes señaladas. Clasificación heurística:", '']
    for category, count in summary['small_region_utility'].items():
        lines.append(f'- {category}: {count}.')
    lines.extend(['', 'Una región estrecha puede ser una rayadura larga útil; no se descarta por tener un eje <16 px. Se distingue evidencia adicional de mayor tamaño, regiones fuera de taxonomía y casos que necesitan detalle. La proyección a 384 px es solo un escenario de planificación, no una transformación del dataset ni una decisión de arquitectura.', '',
                  '## Conformidad y evaluabilidad', '',
                  f"Hay {summary['cap_good_source_candidates']} imágenes con Good Cap como única clase fuente. Son evidencia parcial de tapa, no botellas globalmente conformes. Confirmadas conformes: 0.",
                  f"Candidatos de encuadre conjunto: {json.dumps(summary['joint_evaluation_candidates'])}. Evaluabilidad confirmada: 0.",
                  'El encuadre y la nitidez no demuestran que cuerpo, rayaduras, contorno y tapa sean simultáneamente inspeccionables. La galería pide comprobación humana; no asigna negativos ni CONFORME.', '',
                  '## Propuesta de particiones por origen', '', '| Fuente | Partición | Imágenes | Grupos | Positivos RAY / DEF / TAPA |', '|---|---|---:|---:|---|'])
    for source, parts in summary['proposed_distribution'].items():
        for split, values in parts.items():
            if values['images']:
                lines.append(f"| {source} | {split} | {values['images']} | {values['groups']} | " + ' / '.join(str(values['positives'][label]) for label in LABELS) + ' |')
    lines.extend(['', 'Mendeley: objetivo aproximado 70/15/15 con estratificación de positivos a nivel de componente, sin romper grupos grandes.',
                  'Roboflow: 04/07/2022 → train; 05/07 y 13/07 → validation; 01/07 → test. Las fechas son proxies del nombre, no metadatos verificados. La prueba conserva 87 positivos de tapa, pero validación solo tiene tres positivos: NO permite calibrar umbrales de tapa de forma fiable. No forzar 70/15/15 rompiendo sesiones.',
                  'Las particiones son propuestas en un archivo NUEVO; no se cambia split en los manifiestos originales, no se mueven imágenes ni se crean carpetas de entrenamiento.', '',
                  '## Limitaciones y recomendaciones', '',
                  'El balance 50/50 de la galería equilibra esfuerzo humano, no prevalencia ni calidad del corpus completo. La selección prioriza categorías, regiones pequeñas, diversidad de componentes y evitar repetir grupos visuales.',
                  'No hay negativos públicos explícitos ni positivos conjuntos de varias categorías objetivo. Los defectos corporales solo tienen positivos de Mendeley y los de tapa solo de Roboflow: persiste confusión entre fuente, producto y defecto.',
                  'Los componentes transitivos pueden agrupar botellas distintas de apariencia similar. Revisarlos conservadoramente sin separarlos entre particiones hasta resolver la identidad. Persisten fugas no detectables si el origen físico no está documentado.',
                  'Antes de entrenar: confirmar visibilidad y etiquetas por botella, obtener conformes globales y combinaciones reales, ampliar sesiones de tapas para validación independiente y congelar las particiones. No reutilizar el test para decidir umbrales tras observar resultados.',
                  'Todas las etiquetas se preservan; las propuestas, candidatos e incertidumbres no son anotaciones humanas nuevas. No se ha entrenado ningún modelo.', '',
                  '## Archivos', '',
                  '- index.html: galería local reducida, etiquetas/procedencia/licencias y preguntas de revisión.',
                  '- review_selection.jsonl: lista seleccionada, motivos y estado pendiente de confirmación.',
                  '- origin_components.jsonl y split_proposal.jsonl: agrupaciones y propuesta por imagen.',
                  '- small_region_assessment.jsonl: evaluación potencial de las 945 imágenes sin eliminarlas.',
                  '- summary.json: distribución, cobertura y huellas de la auditoría de entrada.'])
    (output/'INFORME_SELECCION.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit',type=Path,default=ROOT/'datasets/publicos_calidad_botellas/audits/visual_v002')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--limit',type=int,default=100)
    parser.add_argument('--seed',type=int,default=20261114)
    args=parser.parse_args()
    summary=prepare(args.audit,args.output,args.limit,args.seed)
    print(json.dumps({k:summary[k] for k in ('selected_images','selected_by_source','origin_components','small_region_utility','proposed_distribution')},ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
