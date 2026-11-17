"""Auditoría visual offline: solo escribe miniaturas e informes en una carpeta nueva."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import random

import cv2
import numpy as np

from .extract_crops import ROOT, sha256

LABELS = ('RAYADURA', 'DEFORMACION', 'TAPA_DEFECTUOSA')


def read_rows(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines() if line.strip()]


def fingerprints(gray):
    small = cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA)
    values = cv2.dct(small.astype(np.float32))[:8, :8].flatten()[1:]
    phash = sum(int(b) << i for i, b in enumerate(values > np.median(values)))
    grid = cv2.resize(gray, (9, 8), interpolation=cv2.INTER_AREA)
    dhash = sum(int(b) << i for i, b in enumerate((grid[:, 1:] > grid[:, :-1]).flatten()))
    return phash, dhash


def gray_for_similarity(image):
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def inspect_image(path, expected_hash=None):
    data = Path(path).read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    image = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR | cv2.IMREAD_IGNORE_ORIENTATION)
    if image is None:
        raise ValueError('No se puede decodificar la imagen')
    height, width = image.shape[:2]
    scale = min(1, 512 / max(width, height))
    preview = cv2.resize(image, (max(1, round(width * scale)), max(1, round(height * scale))), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(preview, cv2.COLOR_BGR2GRAY)
    sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    dark, bright = float(np.mean(gray <= 10)), float(np.mean(gray >= 245))
    flags = []
    if expected_hash and digest != expected_hash:
        flags.append('hash_mismatch')
    if min(width, height) < 224 or width * height < 65536:
        flags.append('low_resolution')
    if sharpness < 50:
        flags.append('possible_blur')
    if dark > .4:
        flags.append('dark_background_or_underexposure')
    if bright > .4:
        flags.append('bright_background_or_overexposure')
    phash, dhash = fingerprints(gray)
    color = cv2.resize(image, (16, 16), interpolation=cv2.INTER_AREA)
    return {'width': width, 'height': height, 'aspect_ratio': width / height,
            'laplacian_512': sharpness, 'gray_mean': float(gray.mean()), 'gray_std': float(gray.std()),
            'dark_fraction': dark, 'bright_fraction': bright, 'actual_sha256': digest, 'flags': flags}, preview, phash, dhash, color


class BKTree:
    def __init__(self):
        self.root = None

    def add(self, value, index):
        if self.root is None:
            self.root = [value, [index], {}]
            return
        node = self.root
        while True:
            distance = (value ^ node[0]).bit_count()
            if not distance:
                node[1].append(index)
                return
            if distance not in node[2]:
                node[2][distance] = [value, [index], {}]
                return
            node = node[2][distance]

    def find(self, value, radius):
        queue = [self.root] if self.root else []
        result = []
        while queue:
            node = queue.pop()
            distance = (value ^ node[0]).bit_count()
            if distance <= radius:
                result.extend(node[1])
            queue.extend(child for key, child in node[2].items() if distance - radius <= key <= distance + radius)
        return result


def load_sources(imports, reference, workspace):
    rows, inputs = [], []
    for root in imports:
        root = Path(root).resolve()
        if json.loads((root / 'STATUS.json').read_text())['status'] != 'COMPLETED':
            raise ValueError('Importación incompleta')
        manifest = root / 'samples.public.jsonl'
        inputs.append({'path': str(manifest), 'sha256': sha256(manifest)})
        for source in read_rows(manifest):
            if not source.get('image'):
                continue
            path = (root / source['image']).resolve()
            if not path.is_relative_to(root / 'images'):
                raise ValueError('Ruta de imagen fuera de la importación')
            rows.append({'sample_id': source['sample_id'], 'path': path, 'source': source['dataset_id'],
                         'role': 'PUBLIC', 'labels': source['labels'], 'expected_hash': source['image_sha256'],
                         'license': source['license'], 'license_url': source['license_url'], 'source_url': source['source_url'],
                         'creators': source['source_creators'], 'classes': source['source_classes'],
                         'file_name': source['source_occurrences'][0]['relative'],
                         'occurrences': source['source_occurrences'], 'source_groups': source['filename_source_groups'],
                         'conditional': source.get('mapping_requires_review', {}),
                         'scope': source['label_scope'], 'expected_width': source['width'], 'expected_height': source['height']})
    reference = Path(reference).resolve()
    original = reference / 'samples.jsonl'
    inputs.append({'path': str(original), 'sha256': sha256(original)})
    originals = read_rows(original)
    annotations = {r['sample_id']: r for r in originals}
    revisions = sorted((Path(workspace) / 'revisions').glob('*.jsonl')) if workspace else []
    if revisions:
        inputs.append({'path': str(revisions[-1].resolve()), 'sha256': sha256(revisions[-1])})
        annotations.update({r['sample_id']: r for r in read_rows(revisions[-1])})
    for source in originals:
        annotation = annotations[source['sample_id']]
        path = (reference / source['image']).resolve()
        if not path.is_relative_to(reference / 'images'):
            raise ValueError('Ruta EPP fuera de la extracción')
        rows.append({'sample_id': source['sample_id'], 'path': path, 'source': 'EPP_REFERENCE', 'role': 'EPP_REFERENCE',
                     'labels': annotation['labels'], 'expected_hash': source['image_sha256'],
                     'license': 'Interna; licencia pública no especificada', 'license_url': '', 'source_url': '',
                     'creators': ['Captura EPP; autor de captura no especificado'], 'classes': [],
                     'file_name': Path(source['image']).name, 'occurrences': [], 'conditional': {},
                     'scope': 'individual_bottle_crop', 'source_groups': [source['run_id'] + ':' + str(source['track_id'])],
                     'expected_width': source['quality']['width'], 'expected_height': source['quality']['height'],
                     'categories': annotation.get('categories'), 'annotation_status': annotation['annotation_status']})
    if len({r['sample_id'] for r in rows}) != len(rows):
        raise ValueError('IDs de muestra repetidos')
    return rows, inputs


def distributions(rows):
    output = {}
    for name in sorted({r['source'] for r in rows}):
        selected = [r for r in rows if r['source'] == name]
        counts = {label: {'positive': sum(r['labels'][label] == 1 for r in selected),
                          'negative': sum(r['labels'][label] == 0 for r in selected),
                          'unknown': sum(r['labels'][label] is None for r in selected)} for label in LABELS}
        overlap = {a + ' + ' + b: sum(r['labels'][a] == 1 and r['labels'][b] == 1 for r in selected)
                   for i, a in enumerate(LABELS) for b in LABELS[i+1:]}
        metrics = [r['metrics'] for r in selected if r.get('metrics')]
        output[name] = {'images': len(selected), 'labels': counts, 'positive_overlap': overlap,
                        'patterns': dict(Counter(' / '.join(f'{label}={r["labels"][label]}' for label in LABELS) for r in selected)),
                        'technical_flags': dict(Counter(f for r in selected for f in r['flags'])),
                        'semantic_review_flags': dict(Counter(f for r in selected for f in r['semantic_flags'])),
                        'dimensions': dict(Counter(f'{m["width"]}x{m["height"]}' for m in metrics)),
                        'medians': {key: float(np.median([m[key] for m in metrics])) if metrics else None
                                    for key in ['width', 'height', 'aspect_ratio', 'laplacian_512', 'gray_mean']}}
    return output


def audit(imports, reference, workspace, output, seed=20261114):
    output = Path(output).resolve()
    allowed = ROOT / 'datasets/publicos_calidad_botellas/audits'
    if not output.is_relative_to(allowed):
        raise ValueError('Guardar la auditoría en datasets/publicos_calidad_botellas/audits, fuera de originales')
    if output.exists():
        raise FileExistsError('No sobrescribir una auditoría previa')
    rows, inputs = load_sources(imports, reference, workspace)
    output.mkdir(parents=True, exist_ok=False)
    (output / 'thumbs').mkdir()
    (output / 'STATUS.json').write_text('{"status":"RUNNING"}')
    tree, fingerprints_seen, exact, pairs, parent = BKTree(), {}, defaultdict(list), [], {}
    pair_count = 0
    def find(index):
        parent.setdefault(index, index)
        if parent[index] != index:
            parent[index] = find(parent[index])
        return parent[index]
    def union(a, b):
        parent[find(a)] = find(b)
    try:
        for index, row in enumerate(rows):
            row['flags'], row['semantic_flags'], row['metrics'] = [], [], None
            row['original_url'] = Path(os.path.relpath(row['path'], output)).as_posix()
            if row['role'] == 'PUBLIC':
                row['semantic_flags'].append('scene_presence_not_verified_individual_bottle')
            if row['conditional']:
                row['semantic_flags'].append('conditional_source_mapping')
            if any(c.startswith('scuff_') for c in row['classes']):
                row['semantic_flags'].append('scuff_not_necessarily_scratch_morphology')
            if 'Good Cap' in row['classes'] and any(c in row['classes'] for c in ('Broken Cap', 'Loose Cap', 'No Cap')):
                row['semantic_flags'].append('mixed_cap_states_in_scene_not_proven_wrong_label')
            if row['role'] == 'PUBLIC' and not any(v == 1 for v in row['labels'].values()):
                row['semantic_flags'].append('no_safe_target_equivalence')
            tiny = sum(a['bbox_xywh_pixels'][2] < 16 or a['bbox_xywh_pixels'][3] < 16
                       for o in row['occurrences'] for a in o['annotations'])
            row['tiny_annotation_regions'] = tiny
            if tiny:
                row['semantic_flags'].append('defect_region_under_16px')
            try:
                metrics, preview, phash, dhash, color = inspect_image(row['path'], row['expected_hash'])
                row['metrics'], row['flags'] = metrics, metrics['flags'].copy()
                if (metrics['width'], metrics['height']) != (row['expected_width'], row['expected_height']):
                    row['flags'].append('manifest_dimensions_mismatch')
                exact[metrics['actual_sha256']].append(index)
                thumb = cv2.resize(preview, (max(1, round(preview.shape[1] * min(1, 280 / max(preview.shape[:2])))),
                                             max(1, round(preview.shape[0] * min(1, 280 / max(preview.shape[:2]))))), interpolation=cv2.INTER_AREA)
                relative = f'thumbs/{index:06d}.jpg'
                if not cv2.imwrite(str(output / relative), thumb, [cv2.IMWRITE_JPEG_QUALITY, 88]):
                    raise OSError('No se pudo guardar miniatura')
                row['thumbnail'] = relative
                if metrics['gray_std'] >= 4:
                    gray64 = cv2.resize(gray_for_similarity(preview), (64, 64), interpolation=cv2.INTER_AREA)
                    for old in tree.find(phash, 2):
                        old_hash, old_dhash, old_color, old_gray = fingerprints_seen[old]
                        difference = float(np.abs(color.astype(float) - old_color.astype(float)).mean()) / 255
                        pixel_difference = np.abs(gray64.astype(float) - old_gray.astype(float))
                        changed_fraction = float(np.mean(pixel_difference > 12))
                        if ((dhash ^ old_dhash).bit_count() <= 4 and difference <= .025
                                and float(pixel_difference.mean()) / 255 <= .025 and changed_fraction <= .04
                                and abs(metrics['aspect_ratio'] - rows[old]['metrics']['aspect_ratio']) <= .03):
                            pair_count += 1
                            union(old, index)
                            if len(pairs) < 50000:
                                pairs.append({'left': old, 'right': index, 'phash_distance': (phash ^ old_hash).bit_count(),
                                              'dhash_distance': (dhash ^ old_dhash).bit_count(), 'color_difference': difference,
                                              'changed_pixel_fraction_64': changed_fraction})
                    tree.add(phash, index)
                    fingerprints_seen[index] = phash, dhash, color, gray64
            except (OSError, ValueError, cv2.error) as error:
                row['flags'].append('unreadable_or_damaged')
                row['read_error'] = str(error)
                row['thumbnail'] = None
            row['path'] = str(row['path'])
            if (index + 1) % 1000 == 0:
                print(f'Auditadas {index+1}/{len(rows)} imágenes', flush=True)
        groups = defaultdict(list)
        for index in parent:
            groups[find(index)].append(index)
        visual_groups = [v for v in groups.values() if len(v) > 1]
        for group_id, members in enumerate(visual_groups, 1):
            for index in members:
                rows[index]['visual_group'] = group_id
                rows[index]['flags'].append('possible_visual_duplicate')
        for members in exact.values():
            if len(members) > 1:
                for index in members:
                    rows[index]['flags'].append('exact_sha256_duplicate')
        filename_groups = defaultdict(lambda: defaultdict(set))
        for index, row in enumerate(rows):
            for group in row['source_groups']:
                for o in row['occurrences']:
                    filename_groups[(row['source'], group)][o['split']].add(index)
        crossing = [{'source': source, 'group': group, 'splits': {k: sorted(v) for k, v in splits.items()}}
                    for (source, group), splits in filename_groups.items() if len(splits) > 1]
        for group in crossing:
            for indices in group['splits'].values():
                for index in indices:
                    if 'source_partition_leakage_risk' not in rows[index]['semantic_flags']:
                        rows[index]['semantic_flags'].append('source_partition_leakage_risk')
        summary = {'seed': seed, 'public_images': sum(r['role'] == 'PUBLIC' for r in rows),
                   'epp_reference_images': sum(r['role'] == 'EPP_REFERENCE' for r in rows),
                   'sources': distributions(rows), 'exact_duplicate_groups': [v for v in exact.values() if len(v)>1],
                   'visual_candidate_groups': visual_groups, 'visual_candidate_pairs_total': pair_count,
                   'visual_pairs_stored': len(pairs), 'visual_pairs_truncated': pair_count > len(pairs),
                   'filename_groups_crossing_source_partitions': len(crossing),
                   'thresholds': {'sharpness_normalized_long_side': 512, 'possible_blur_laplacian_below': 50,
                                  'minimum_short_side': 224, 'minimum_area': 65536,
                                  'phash_radius': 2, 'dhash_radius': 4, 'max_color_difference': .025,
                                  'max_gray_difference_64': .025, 'max_changed_pixel_fraction_64': .04,
                                  'changed_pixel_threshold': 12, 'max_aspect_ratio_difference': .03},
                   'input_manifests': inputs,
                   'disclaimer': 'Alertas heurísticas; no certifican defectos ni errores de etiqueta. No se infieren negativos.'}
        for item in inputs:
            if sha256(item['path']) != item['sha256']:
                raise ValueError('Un manifiesto cambió durante la auditoría; repetir con fuentes estables')
        (output / 'metrics.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False)+'\n' for r in rows), encoding='utf-8')
        (output / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
        (output / 'visual_pairs.jsonl').write_text(''.join(json.dumps(p)+'\n' for p in pairs), encoding='utf-8')
        (output / 'source_partition_groups.json').write_text(json.dumps(crossing, ensure_ascii=False, indent=2), encoding='utf-8')
        for name in ('audit_gallery.js', 'audit_gallery.css'):
            (output / name).write_bytes(Path(__file__).with_name(name).read_bytes())
        template = Path(__file__).with_name('audit_gallery.html').read_text(encoding='utf-8')
        # JSON inline funciona también con file://, sin fetch ni servidor.
        gallery_rows = [{k:v for k,v in row.items() if k not in ('occurrences','path','source_groups')} for row in rows]
        payload = json.dumps({'rows': gallery_rows, 'summary': summary}, ensure_ascii=True).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
        (output / 'index.html').write_text(template.replace('AUDIT_DATA_HERE', payload), encoding='utf-8')
        write_report(output, rows, summary)
        (output / 'STATUS.json').write_text('{"status":"COMPLETED"}')
        return summary
    except Exception:
        (output / 'STATUS.json').write_text('{"status":"FAILED"}')
        raise


def write_report(output, rows, summary):
    lines = ['# Auditoría visual de botellas EPP', '',
             f"Imágenes públicas auditadas: **{summary['public_images']}**. Referencias EPP: **{summary['epp_reference_images']}**.",
             'No se modificaron imágenes, etiquetas, revisiones ni particiones; no hubo entrenamiento.', '',
             '## Distribución observada', '', '| Fuente | Imágenes | Rayadura (+ / − / ?) | Deformación (+ / − / ?) | Tapa (+ / − / ?) |', '|---|---:|---|---|---|']
    for source, data in summary['sources'].items():
        values = [' / '.join(str(data['labels'][label][k]) for k in ('positive','negative','unknown')) for label in LABELS]
        lines.append(f"| {source} | {data['images']} | " + ' | '.join(values) + ' |')
    lines.extend(['', 'Desconocido no significa negativo. No se han generado etiquetas ausentes.', '',
                  '## Alertas técnicas por fuente', '', '| Fuente | Posible desenfoque | Resolución insuficiente | No decodificable | Hash distinto |', '|---|---:|---:|---:|---:|'])
    for source, data in summary['sources'].items():
        f = data['technical_flags']
        lines.append(f"| {source} | {f.get('possible_blur',0)} | {f.get('low_resolution',0)} | {f.get('unreadable_or_damaged',0)} | {f.get('hash_mismatch',0)} |")
    lines.extend(['', 'Laplaciano calculado tras ajustar el lado largo a un máximo de 512 px; umbral inicial 50. No es una evaluación de visibilidad semántica. El fondo, la textura y la escala influyen.',
                  'Resolución insuficiente: lado corto <224 px o área <65536 px. Es una alerta genérica, no una garantía de detalle de un defecto.', '',
                  '## Duplicados y fugas', '',
                  f"Grupos exactos SHA-256: {len(summary['exact_duplicate_groups'])}.",
                  f"Grupos candidatos visuales: {len(summary['visual_candidate_groups'])}; pares candidatos: {summary['visual_candidate_pairs_total']}.",
                  f"Se guardaron {summary['visual_pairs_stored']} pares en visual_pairs.jsonl. Límite de 50000: los pares guardados son los primeros, no una muestra representativa; los grupos y totales usan TODOS los pares encontrados.",
                  f"Grupos nominales compartidos entre particiones de origen: {summary['filename_groups_crossing_source_partitions']}.",
                  'La búsqueda global combina pHash (radio 2), dHash (radio 4), color, diferencia de píxeles en 64x64 y relación de aspecto. Los grupos son componentes conectados de semejanza, NO equivalencias certificadas. Pueden unir botellas distintas de apariencia parecida. No se eliminan ni se fusionan imágenes.',
                  'No detecta todas las variantes giradas, recortadas o con cambios fuertes de iluminación. Examinar los pares y reagrupar por origen físico antes de dividir entrenamiento/prueba.', '',
                  '## Solapamiento y compatibilidad de etiquetas', ''])
    for source, data in summary['sources'].items():
        lines.append(f"- {source}: solapamientos positivos {json.dumps(data['positive_overlap'],ensure_ascii=False)}; alertas semánticas {json.dumps(data['semantic_review_flags'],ensure_ascii=False)}.")
    public = [row for row in rows if row['role'] == 'PUBLIC']
    joint = sum(sum(value == 1 for value in row['labels'].values()) > 1 for row in public)
    lines.append(f'\nImágenes públicas con más de una categoría objetivo positiva: **{joint}**. No confundir múltiples cajas de la misma categoría con cobertura multietiqueta.')
    for label in LABELS:
        sources = sorted({row['source'] for row in public if row['labels'][label] == 1})
        if len(sources) == 1:
            lines.append(f'- Todos los positivos públicos de {label} proceden de {sources[0]}. Riesgo de confusión fuente/producto frente a defecto.')
    lines.extend(['', 'Las alertas semánticas identifican riesgos revisables, no errores demostrados: scuff puede representar abrasión más amplia que una rayadura; No Cap y Broken Ring requieren criterio de proceso; Good Cap no prueba conformidad global. Estados buenos y defectuosos en una escena pueden pertenecer a objetos diferentes.',
                  'Las cajas pequeñas de defecto (<16 px en alguna dimensión) pueden no aportar detalle suficiente. Se conservan todas sus anotaciones.', '',
                  '## Diferencias de dominio', '',
                  'La galería incluye un grupo de referencia EPP separado. Mendeley muestra botellas de champú opacas, etiquetas y cierres diferentes; Roboflow incluye primeros planos de cuellos/anillos/tapas; EPP son recortes verticales de botellas con contenido oscuro y tapa amarilla junto a maquinaria. Estas observaciones proceden de inspección de ejemplos, no de segmentación automática de todos los objetos.',
                  'Comparar color/material/transparencia de botella, tipo de tapa, fondo, iluminación, reflejos, perspectiva, oclusiones, encuadre y tamaño efectivo del defecto. Las estadísticas de resolución y brillo son descriptivas, no una medida de transferencia del modelo.', '',
                  '## Recomendaciones', '',
                  '1. Revisar primero pares visuales que crucen particiones y ejemplos de cada fuente/categoría.',
                  '2. Verificar asignación de cada defecto a una botella antes de usar etiquetas de escena para recortes.',
                  '3. Revisar mapeos condicionales y scuff; no convertir desconocidos en negativos.',
                  '4. Acordar criterios de calidad por cámara; calibrar umbrales con revisión humana, sin descartar automáticamente las alertas.',
                  '5. Capturar ejemplos EPP evaluables de defectos y conformidad; mantener una prueba independiente por sesión/botella.',
                  '6. Mantener el entrenamiento bloqueado hasta validar datos, licencias, particiones y etiquetas.', '',
                  '## Reproducibilidad y trazabilidad', '',
                  f"Semilla inicial de muestreo: {summary['seed']}. La galería puede regenerar muestras sin modificar los datos.",
                  'Cada tarjeta muestra etiquetas, clase fuente, nombre original, proveedor, autores y licencia. Las miniaturas son derivados exclusivos de visualización; el enlace abre el original sin modificarlo.',
                  'Consultar summary.json, metrics.jsonl, visual_pairs.jsonl y source_partition_groups.json. Los índices de pares/grupos corresponden al orden de metrics.jsonl.',
                  'El muestreo de tarjetas está estratificado por fuente; no es una muestra representativa de prevalencia ni un tamaño de prueba estadística.'])
    rng = random.Random(summary['seed'])
    lines.extend(['', '## Ejemplos inspeccionados para comparar dominio', ''])
    for source in ['mendeley_kthmmbsh8t_v1', 'roboflow_caps_v26', 'EPP_REFERENCE']:
        examples = [row for row in rows if row['source'] == source]
        if examples:
            row = rng.choice(examples)
            lines.append(f"- {source}: [{row['file_name']}]({row['original_url']}); SHA-256 `{row['expected_hash']}`. Licencia: {row['license']}.")
    (output / 'INFORME_CALIDAD.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--imports', type=Path, nargs='+', default=[ROOT/'datasets/publicos_calidad_botellas/imports/mendeley_kthmmbsh8t_v1_001', ROOT/'datasets/publicos_calidad_botellas/imports/roboflow_caps_v26_001'])
    parser.add_argument('--reference', type=Path, default=ROOT/'datasets/calidad_botellas/v001/runs/referencia_a3')
    parser.add_argument('--workspace', type=Path, default=ROOT/'datasets/calidad_botellas/v001/labeling/revision_humana_001')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seed', type=int, default=20261114)
    args = parser.parse_args()
    result = audit(args.imports, args.reference, args.workspace, args.output, args.seed)
    print(json.dumps({k:result[k] for k in ['public_images','epp_reference_images','visual_candidate_pairs_total']}, indent=2))


if __name__ == '__main__':
    main()
