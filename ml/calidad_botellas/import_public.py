"""Importa anotaciones públicas verificadas a un espacio separado; nunca entrena."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
import re
from pathlib import Path, PurePosixPath
import shutil
import warnings

from PIL import Image
import yaml

from .extract_crops import ROOT, sha256

TARGETS = ("RAYADURA", "DEFORMACION", "TAPA_DEFECTUOSA")
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}
PUBLIC_ROOT = ROOT / "datasets/publicos_calidad_botellas"


def safe_path(root, relative):
    name = str(relative).replace("\\", "/")
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or ":" in name:
        raise ValueError("Ruta externa o traversal en la anotación.")
    result = (Path(root).resolve() / name).resolve()
    if not result.is_relative_to(Path(root).resolve()):
        raise ValueError("El archivo sale del directorio de origen.")
    return result


def source_definition(dataset_id):
    registry = json.loads(Path(__file__).with_name("public_sources.json").read_text(encoding="utf-8"))
    source = registry["sources"][dataset_id]
    if source.get("license") != "CC-BY-4.0" or not source.get("license_evidence") or not source.get("license_verified_on"):
        raise ValueError("No hay licencia verificada para esta fuente.")
    if not source.get("creators") or not source.get("version"):
        raise ValueError("Faltan autoría o versión de la fuente.")
    return source


def map_positive_presence(classes, source):
    labels = dict.fromkeys(TARGETS)
    for name in classes:
        target = source["positive_mapping"].get(name)
        if target is not None:
            if target not in labels:
                raise ValueError("Taxonomía de destino desconocida.")
            labels[target] = 1
    return labels


def verify_export_identity(dataset_id, root, annotation_format, source):
    """No atribuir una carpeta arbitraria a una fuente licenciada."""
    root = Path(root)
    if dataset_id == 'mendeley_kthmmbsh8t_v1':
        raw = root.parent.parent
        metadata = json.loads((raw / 'metadata.json').read_text(encoding='utf-8'))
        if (metadata.get('id') != 'kthmmbsh8t' or metadata.get('version') != 1
                or metadata.get('data_licence', {}).get('short_name') != 'CC BY 4.0'
                or sha256(raw / 'dataset.rar') != source['archive_sha256']):
            raise ValueError("La procedencia o integridad del archivo Mendeley no coincide.")
        return
    project_url = source['url'].rsplit('/dataset/', 1)[0]
    if annotation_format == 'yolo':
        config = yaml.safe_load((root / 'data.yaml').read_text(encoding='utf-8'))
        info = config.get('roboflow', {})
        expected = '/'.join([str(info.get('workspace', '')), str(info.get('project', ''))])
        if (project_url.endswith('/' + expected) and str(info.get('version')) == source['version']
                and info.get('license') == 'CC BY 4.0'):
            return
    else:
        readmes = [p for p in root.rglob('README*.txt') if p.is_file()]
        texts = []
        for path in readmes:
            safe_path(root, path.relative_to(root))
            texts.append(path.read_text(encoding='utf-8-sig'))
        text = '\n'.join(texts)
        if (project_url in text and 'cc by 4.0' in text.lower()
                and re.search(r'(?:version\s*:?\s*|\bv)' + re.escape(source['version']) + r'\b', text, re.I)):
            return
    raise ValueError("La exportación no acredita proyecto, versión y licencia esperados. Revisar su README/data.yaml antes de importar.")


def box_valid(x, y, w, h, width, height):
    values = [x, y, w, h, width, height]
    if (not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in values)
            or width <= 0 or height <= 0 or x < -1e-5 or y < -1e-5 or w <= 0 or h <= 0
            or x + w > width + 1e-5 or y + h > height + 1e-5):
        raise ValueError("Coordenadas de detección inválidas.")


def image_metadata(path):
    if path.suffix.lower() not in IMAGE_SUFFIXES:
        raise ValueError("Formato de imagen no admitido.")
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(path) as image:
            if image.format not in ("JPEG", "PNG") or image.width * image.height > 40_000_000:
                raise ValueError("Imagen fuera de los límites admitidos.")
            width, height, fmt = image.width, image.height, image.format
            image.verify()
        with Image.open(path) as image:
            image.load()
    return width, height, fmt


def parse_yolo(root):
    root = Path(root).resolve()
    config = yaml.safe_load((root / "data.yaml").read_text(encoding="utf-8"))
    names = config["names"]
    if isinstance(names, dict):
        names = [names[i] for i in range(len(names))]
    if not isinstance(names, list) or not names or len(set(names)) != len(names) or not all(isinstance(n, str) for n in names):
        raise ValueError("Catálogo de clases inválido.")
    image_paths = [p for p in sorted(root.rglob('*')) if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES and '.ipynb_checkpoints' not in p.parts]
    for path in image_paths:
        if path.parent.name != "images":
            raise ValueError("Se esperaba estructura YOLO split/images y split/labels.")
        path = safe_path(root, path.relative_to(root))
        width, height, fmt = image_metadata(path)
        label = safe_path(root, path.parent.parent.relative_to(root) / 'labels' / (path.stem + '.txt'))
        if not label.is_file():
            raise ValueError("Imagen sin anotación; no inferir negativos: " + str(path))
        annotations = []
        for number, line in enumerate(label.read_text(encoding='utf-8-sig').splitlines(), 1):
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) != 5:
                raise ValueError("Solo se admite detección YOLO de cinco columnas.")
            class_id = int(parts[0])
            if not 0 <= class_id < len(names):
                raise ValueError("Clase YOLO fuera de rango.")
            cx, cy, w, h = map(float, parts[1:])
            box_valid(cx - w / 2, cy - h / 2, w, h, 1, 1)
            annotations.append({"source_class": names[class_id], "source_class_id": class_id,
                                "bbox_xywh_pixels": [(cx - w / 2) * width, (cy - h / 2) * height, w * width, h * height],
                                "source_yolo_line": line, "source_line_number": number})
        yield {"path": path, "relative": path.relative_to(root).as_posix(), "width": width, "height": height,
               "format": fmt, "split": path.parent.parent.name, "annotations": annotations,
               "annotation_file": label.relative_to(root).as_posix(), "annotation_sha256": sha256(label)}


def parse_coco(root):
    root = Path(root).resolve()
    files = sorted(root.rglob('_annotations.coco.json'))
    if not files:
        raise ValueError("No se encontró _annotations.coco.json de Roboflow.")
    seen_paths = set()
    for annotation_file in files:
        safe_path(root, annotation_file.relative_to(root))
        data = json.loads(annotation_file.read_text(encoding='utf-8'))
        categories = {c['id']: c['name'] for c in data['categories']}
        if len(categories) != len(data['categories']):
            raise ValueError("Categorías COCO duplicadas.")
        images = {image['id']: image for image in data['images']}
        if len(images) != len(data['images']):
            raise ValueError("IDs COCO de imagen duplicados.")
        by_image, annotation_ids = defaultdict(list), set()
        for annotation in data['annotations']:
            if annotation['id'] in annotation_ids or annotation['image_id'] not in images or annotation['category_id'] not in categories:
                raise ValueError("Referencias o IDs COCO inválidos.")
            annotation_ids.add(annotation['id'])
            by_image[annotation['image_id']].append(annotation)
        for image_id, info in images.items():
            path = safe_path(annotation_file.parent, info['file_name'])
            if not path.is_relative_to(root) or path in seen_paths:
                raise ValueError("Ruta COCO repetida o fuera del conjunto.")
            seen_paths.add(path)
            width, height, fmt = image_metadata(path)
            if info['width'] != width or info['height'] != height:
                raise ValueError("Dimensiones COCO distintas de la imagen.")
            annotations = []
            for item in by_image[image_id]:
                box_valid(*item['bbox'], width, height)
                annotations.append({"source_class": categories[item['category_id']], "source_class_id": item['category_id'],
                                    "bbox_xywh_pixels": item['bbox'], "source_coco_annotation": item})
            yield {"path": path, "relative": path.relative_to(root).as_posix(), "width": width, "height": height,
                   "format": fmt, "split": annotation_file.parent.name, "annotations": annotations,
                   "annotation_file": annotation_file.relative_to(root).as_posix(), "annotation_sha256": sha256(annotation_file)}


def known_images(reference_root, imports_root):
    known = {}
    for path in Path(reference_root).rglob('*'):
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES:
            known.setdefault(sha256(path), {"kind": "EPP_REFERENCE", "path": str(path.resolve())})
    for manifest in Path(imports_root).rglob('samples.public.jsonl'):
        status = manifest.parent / 'STATUS.json'
        if not status.is_file() or json.loads(status.read_text(encoding='utf-8')).get('status') != 'COMPLETED':
            continue
        for line in manifest.read_text(encoding='utf-8').splitlines():
            row = json.loads(line)
            known.setdefault(row['image_sha256'], {"kind": "PREVIOUS_PUBLIC_IMPORT", "manifest": str(manifest.resolve()), "sample_id": row['sample_id']})
    return known


def import_dataset(dataset_id, input_root, output, annotation_format, reference_root=None, imports_root=None):
    source = source_definition(dataset_id)  # Verificar licencia antes de abrir imágenes.
    input_root, output = Path(input_root).resolve(), Path(output).resolve()
    if not output.is_relative_to(PUBLIC_ROOT / 'imports'):
        raise ValueError("La importación solo puede escribirse en datasets/publicos_calidad_botellas/imports.")
    if input_root.is_relative_to(output) or output.is_relative_to(input_root):
        raise ValueError("Separar la fuente de la importación.")
    if output.exists():
        raise FileExistsError("No sobrescribir importaciones anteriores.")
    verify_export_identity(dataset_id, input_root, annotation_format, source)
    reference_root = reference_root or ROOT / 'datasets/calidad_botellas'
    imports_root = imports_root or PUBLIC_ROOT / 'imports'
    known = known_images(reference_root, imports_root)
    parser = {'yolo': parse_yolo, 'coco': parse_coco}[annotation_format]
    records, raw_instances, raw_class_images = {}, Counter(), Counter()
    source_splits, source_groups, errors = Counter(), defaultdict(set), []
    count = 0
    # Leer y validar todo antes de crear el directorio de destino.
    for item in parser(input_root):
        count += 1
        digest = sha256(item['path'])
        classes = {a['source_class'] for a in item['annotations']}
        raw_instances.update(a['source_class'] for a in item['annotations'])
        raw_class_images.update(classes)
        source_splits[item['split']] += 1
        group = Path(item['relative']).stem.split('.rf.')[0]
        source_groups[group].add(item['split'])
        occurrence = {k: v for k, v in item.items() if k not in ('path', 'format')}
        if digest not in records:
            records[digest] = {'first': item, 'occurrences': []}
        records[digest]['occurrences'].append(occurrence)
    if not records:
        raise ValueError("La fuente no contiene imágenes admitidas.")
    output.mkdir(parents=True, exist_ok=False)
    (output / 'STATUS.json').write_text(json.dumps({'status': 'IMPORTING'}), encoding='utf-8')
    statistics = {'source_images': count, 'unique_sha256': len(records), 'duplicates_within_source': count-len(records),
                  'external_duplicates': 0, 'copied_images': 0, 'candidate_images': 0, 'unmapped_only_images': 0,
                  'positive_image_counts': dict.fromkeys(TARGETS, 0), 'unknown_image_counts': dict.fromkeys(TARGETS, 0),
                  'source_instances': dict(raw_instances), 'source_class_images': dict(raw_class_images),
                  'source_splits': dict(source_splits), 'filename_source_groups': len(source_groups),
                  'filename_groups_crossing_source_splits': sum(len(v)>1 for v in source_groups.values()),
                  'training_approved_images': 0, 'errors': errors}
    rows = []
    try:
        for digest, data in sorted(records.items()):
            item, occurrences = data['first'], data['occurrences']
            classes = sorted({a['source_class'] for o in occurrences for a in o['annotations']})
            labels = map_positive_presence(classes, source)
            candidate = any(v == 1 for v in labels.values())
            duplicate = known.get(digest)
            image = None
            if duplicate:
                statistics['external_duplicates'] += 1
            else:
                bucket = 'candidate_presence' if candidate else 'unmapped_review_only'
                image = Path('images') / bucket / (digest + ('.jpg' if item['format'] == 'JPEG' else '.png'))
                destination = output / image
                destination.parent.mkdir(parents=True, exist_ok=True)
                with item['path'].open('rb') as src, destination.open('xb') as dst:
                    shutil.copyfileobj(src, dst)
                if sha256(destination) != digest:
                    raise ValueError("La copia no conserva el SHA-256 de origen.")
                statistics['copied_images'] += 1
                statistics['candidate_images' if candidate else 'unmapped_only_images'] += 1
                for label, value in labels.items():
                    statistics['positive_image_counts' if value == 1 else 'unknown_image_counts'][label] += 1
            row = {'schema_version': 'public-image-presence/1.0', 'sample_id': dataset_id + ':' + digest,
                   'image': image.as_posix() if image else None, 'image_sha256': digest,
                   'width': item['width'], 'height': item['height'], 'dataset_id': dataset_id,
                   'source_version': source['version'], 'source_url': source['url'], 'source_creators': source['creators'],
                   'source_annotation_author': source['source_annotation_author'], 'license': source['license'],
                   'license_url': source['license_url'], 'domain': source['domain'],
                   'labels': labels, 'evaluable': {'body': None, 'cap': None}, 'other_defect': None,
                   'categories': {'CONFORME': None, 'NO_EVALUABLE': None},
                   'annotation_status': 'IMPORTED_UNREVIEWED', 'annotator': None, 'reviewer': None,
                   'split': 'UNASSIGNED', 'label_scope': 'image_contains_annotated_defect_not_individual_bottle',
                   'training_eligible': False, 'duplicate_of': duplicate,
                   'source_classes': classes, 'source_occurrences': occurrences,
                   'mapping_requires_review': {c: source['conditional_mapping'][c] for c in classes if c in source['conditional_mapping']},
                   'filename_source_groups': sorted({Path(o['relative']).stem.split('.rf.')[0] for o in occurrences}),
                   'transformations': 'Image bytes unchanged; detection annotations mapped to positive scene presence only; no negative labels inferred.'}
            rows.append(row)
        (output / 'samples.public.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False)+'\n' for r in rows), encoding='utf-8')
        (output / 'statistics.json').write_text(json.dumps(statistics, ensure_ascii=False, indent=2), encoding='utf-8')
        attribution = {'dataset_id': dataset_id, **source, 'imported_at': datetime.now(timezone.utc).isoformat(),
                       'input_manifest_format': annotation_format, 'mapping_code_sha256': sha256(Path(__file__)),
                       'source_registry_sha256': sha256(Path(__file__).with_name('public_sources.json')),
                       'notice': 'Retain attribution and indicate conversion. No endorsement by source creators. Public data are not EPP observations.'}
        (output / 'PROVENANCE_LICENSE.json').write_text(json.dumps(attribution, ensure_ascii=False, indent=2), encoding='utf-8')
        (output / 'STATUS.json').write_text(json.dumps({'status': 'COMPLETED'}), encoding='utf-8')
    except Exception:
        (output / 'STATUS.json').write_text(json.dumps({'status': 'FAILED'}), encoding='utf-8')
        raise
    return statistics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset-id', required=True)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--format', choices=['yolo', 'coco'], required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(import_dataset(args.dataset_id, args.input, args.output, args.format), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
