"""Consolidación explícita de decisiones humanas; nunca autoriza entrenamiento."""
import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

LABELS = ('RAYADURA', 'DEFORMACION', 'TAPA_DEFECTUOSA')
REASONS = {
    'Positivo parcial: DEFORMACION': 16,
    'Positivo parcial: RAYADURA': 16,
    'Positivo parcial: TAPA_DEFECTUOSA': 24,
    'Mapeo condicional: No Cap / Broken Ring': 12,
    'Good Cap: conformidad global NO confirmada': 14,
    'Fuera de taxonomía: revisión de cobertura': 4,
    'Encuadre y evaluabilidad conjunta por confirmar': 7,
    'Regiones pequeñas: OTHER_LARGER_TARGET_REGION_AVAILABLE': 2,
    'Regiones pequeñas: THIN_ELONGATED_TARGET_POTENTIALLY_USEFUL': 1,
    'Regiones pequeñas: ONLY_SMALL_TARGET_REGIONS_NEEDS_DETAIL': 2,
    'Regiones pequeñas: OUTSIDE_TARGET_TAXONOMY': 2,
}
SUBTYPES = {'No Cap': 'TAPA_AUSENTE', 'Broken Ring': 'ANILLO_ROTO',
            'Broken Cap': 'TAPA_DANADA', 'Loose Cap': 'TAPA_MAL_COLOCADA'}
INPUTS = ('review_selection.jsonl', 'small_region_assessment.jsonl',
          'origin_components.jsonl', 'split_proposal.jsonl')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_rows(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def indexed(rows, key='sample_id'):
    result = {r[key]: r for r in rows}
    if len(result) != len(rows):
        raise ValueError('Identificadores duplicados: ' + key)
    return result


def decide(row, timestamp):
    """Solo las decisiones explícitas generan valores confirmados 0/1."""
    reason = row['review_reason']
    if reason not in REASONS:
        raise ValueError('Motivo no autorizado: ' + reason)
    result = deepcopy(row)
    result['source_labels'] = result.pop('labels')
    result['labels'] = dict.fromkeys(LABELS)
    result['status'] = 'CONFIRMED_PARTIAL'
    classes = set(row['classes'])
    if reason.startswith('Positivo parcial: '):
        target = reason.split(': ', 1)[1]
        if row['labels'].get(target) != 1:
            raise ValueError('Positivo fuente incompatible')
        if target == 'TAPA_DEFECTUOSA' and not classes.intersection(SUBTYPES):
            raise ValueError('Subtipo de tapa ausente')
        result['labels'][target] = 1
    elif reason.startswith('Mapeo condicional:'):
        if not classes or not classes.issubset({'No Cap', 'Broken Ring'}):
            raise ValueError('Mapeo de tapa incompatible')
        result['labels']['TAPA_DEFECTUOSA'] = 1
    elif reason.startswith('Good Cap:'):
        if classes != {'Good Cap'}:
            raise ValueError('Evidencia Good Cap contradictoria')
        result['labels']['TAPA_DEFECTUOSA'] = 0
    elif reason.endswith('OTHER_LARGER_TARGET_REGION_AVAILABLE'):
        result['status'] = 'RETAINED_SOURCE_EVIDENCE'
    elif reason.endswith('THIN_ELONGATED_TARGET_POTENTIALLY_USEFUL'):
        result['status'] = 'CANDIDATE_RETAINED'
    elif reason.startswith('Encuadre') or reason.endswith('ONLY_SMALL_TARGET_REGIONS_NEEDS_DETAIL'):
        result['status'] = 'PENDING'
    else:
        result['status'] = 'OUTSIDE_TARGETS'
    result.update(schema_version='human_review_v001',
                  cap_subtypes=[SUBTYPES[c] for c in sorted(classes) if c in SUBTYPES],
                  categories={'CONFORME': None, 'NO_EVALUABLE': None},
                  joint_evaluability=None, training_authorized=False,
                  review_author={'identity': None, 'authority': 'explicit_user_instructions'},
                  recorded_at_utc=timestamp,
                  negative_scope='CAP_ONLY' if result['labels']['TAPA_DEFECTUOSA'] == 0 else None)
    validate_decision(result)
    return result


def validate_decision(row):
    if set(row['labels']) != set(LABELS) or any(
            v is not None and (type(v) is not int or v not in (0, 1)) for v in row['labels'].values()):
        raise ValueError('Etiqueta inválida')
    if any(v is not None for v in row['categories'].values()):
        raise ValueError('No se autorizaron conclusiones globales')
    if row['labels']['TAPA_DEFECTUOSA'] == 0:
        if set(row['classes']) != {'Good Cap'} or any(row['labels'][k] is not None for k in LABELS[:2]):
            raise ValueError('Negativo parcial contradictorio')
    if row['status'] != 'CONFIRMED_PARTIAL' and any(v is not None for v in row['labels'].values()):
        raise ValueError('Confirmación no autorizada')
    for key, value in row['labels'].items():
        source_value = row['source_labels'][key]
        if source_value is not None and value is not None and source_value != value:
            raise ValueError('Contradicción entre fuente y decisión')


def consolidate(directory, output_directory=None):
    directory = Path(directory).resolve()
    destination = Path(output_directory).resolve() if output_directory else directory
    names = ('human_review_v001.jsonl', 'human_review_v001.coverage.json',
             'human_review_v001.report.md', 'human_review_v001.provenance.json')
    if any((destination / name).exists() for name in names):
        raise FileExistsError('La revisión ya existe; no se sobrescribe')
    input_hashes = {name: digest(directory / name) for name in INPUTS}
    selected, small, groups, splits = [read_rows(directory / name) for name in INPUTS]
    selected_index, small_index, group_index, split_index = (
        indexed(selected), indexed(small), indexed(groups, 'group_id'), indexed(splits))
    if len(selected_index) != 100 or Counter(r['review_reason'] for r in selected) != Counter(REASONS):
        raise ValueError('La selección no coincide con las 100 decisiones autorizadas')
    memberships = {}
    for group in groups:
        for sample in group['sample_ids']:
            if sample in memberships:
                raise ValueError('Componentes de origen solapados')
            memberships[sample] = group['group_id']
    if set(memberships) != set(split_index):
        raise ValueError('Cobertura de particiones inconsistente')
    for row in splits:
        group = group_index[memberships[row['sample_id']]]
        if row['group_id'] != group['group_id'] or row['proposed_partition'] != group['proposed_partition']:
            raise ValueError('Fuga o discrepancia de partición por origen')
    public_imports = (directory.parent.parent / 'imports').resolve()
    timestamp = datetime.now(timezone.utc).isoformat()
    decisions = []
    for row in selected:
        sample = row['sample_id']
        split = split_index[sample]
        if any(row[k] != split[k] for k in ('group_id', 'proposed_partition', 'labels', 'source')):
            raise ValueError('La selección contradice la propuesta de partición')
        if row['license'] != 'CC-BY-4.0' or row['license'] != split['license'] or not row['creators']:
            raise ValueError('Licencia o autoría no verificable')
        if row['review_reason'].startswith('Regiones pequeñas: '):
            if small_index[sample]['category'] != row['review_reason'].split(': ', 1)[1]:
                raise ValueError('Evaluación de región pequeña inconsistente')
        image = (directory / row['original_url']).resolve()
        if not image.is_relative_to(public_imports):
            raise ValueError('Imagen fuera del área pública importada')
        if not (digest(image) == row['expected_hash'] == split['image_sha256'] == sample.split(':')[-1]):
            raise ValueError('Hash de imagen alterado: ' + sample)
        decisions.append(decide(row, timestamp))
    if input_hashes != {name: digest(directory / name) for name in INPUTS}:
        raise ValueError('Entradas cambiaron durante la consolidación')
    coverage = {
        'total_decisions': len(decisions), 'unique_sample_ids': len(indexed(decisions)),
        'labels': {key: {'positive': sum(r['labels'][key] == 1 for r in decisions),
                         'negative': sum(r['labels'][key] == 0 for r in decisions),
                         'unknown': sum(r['labels'][key] is None for r in decisions)} for key in LABELS},
        'statuses': dict(Counter(r['status'] for r in decisions)),
        'sources': dict(Counter(r['source'] for r in decisions)),
        'origin_components': len({r['group_id'] for r in decisions}),
        'partitions_images': dict(Counter(r['proposed_partition'] for r in decisions)),
        'physical_bottle_count': None,
        'pending': [{k: r[k] for k in ('sample_id', 'expected_hash', 'file_name', 'review_reason')}
                    for r in decisions if r['status'] == 'PENDING'],
        'errors': [], 'contradictions': [], 'image_hashes_verified': len(decisions),
        'training_authorized': False,
    }
    report = ['# Consolidación humana v001', '',
              '100 decisiones explícitas; 100 hashes de imágenes verificados. Sin contradicciones.',
              'Las etiquetas confirmadas son una capa nueva; source_labels conserva la evidencia previa.',
              'Autor humano: identidad no proporcionada; se registra la instrucción explícita del usuario y la fecha de consolidación, sin inventar una firma.', '',
              '| Categoría | Positivos | Negativos | Desconocidos |', '|---|---:|---:|---:|']
    for key, counts in coverage['labels'].items():
        report.append(f"| {key} | {counts['positive']} | {counts['negative']} | {counts['unknown']} |")
    report += ['', '## Estados', '', *[f'- {k}: {v}' for k, v in coverage['statuses'].items()], '',
               'Los 14 Good Cap son negativos exclusivamente de tapa. CONFORME y NO_EVALUABLE siguen null.',
               'Las 2 conservadas y la candidata conservan sus positivos fuente, sin confirmación humana inventada.',
               'Los 6 casos fuera de taxonomía no producen negativos. No se elimina ninguna imagen.',
               f"Se conservan {coverage['origin_components']} componentes de origen y todas las particiones propuestas. Las 100 imágenes no equivalen a 100 botellas independientes.",
               'La partición sigue siendo propuesta; esta revisión no habilita entrenamiento ni resuelve por sí sola la cobertura insuficiente de tapas en validación.', '',
               '## Pendientes de confirmación (9)', '']
    report += [f"- {r['sample_id']} — {r['file_name']} — {r['review_reason']}" for r in coverage['pending']]
    report += ['', '## Procedencia y conservación', '',
               'Mendeley y Roboflow: CC BY 4.0. Cada registro conserva autores, fuente, URL de licencia, clases originales, hash, componente y partición.',
               'Sin modificaciones de anotaciones, imágenes, muestras propias, base de datos, modelos, seguimiento o código de producción.',
               'Los hashes de los cuatro archivos de entrada se incluyen en el manifiesto de procedencia.']
    contents = [ ''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in decisions),
                 json.dumps(coverage, ensure_ascii=False, indent=2) + '\n', '\n'.join(report) + '\n',
                 json.dumps({'input_sha256': input_hashes, 'recorded_at_utc': timestamp,
                             'decision_source': 'explicit_user_instructions',
                             'output_sha256': hashlib.sha256((''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in decisions)).encode('utf-8')).hexdigest()}, indent=2) + '\n']
    destination.mkdir(parents=True, exist_ok=True)
    for name, content in zip(names, contents):
        with (destination / name).open('x', encoding='utf-8', newline='\n') as handle:
            handle.write(content)
    return coverage


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    print(json.dumps(consolidate(args.directory), ensure_ascii=False, indent=2))
