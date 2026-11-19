"""Anotación manual independiente. Sin modelos, Django ni escritura en fuentes."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import os
from pathlib import Path
import re
import secrets
import sys
import threading
from urllib.parse import urlsplit
from uuid import uuid4

import cv2
import numpy as np

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[4]
sys.path.insert(0, str(BASE.parents[1] / 'tools'))
import video_dataset as video_tools

CLASSES = ('ENVASE', 'TAPA')
SPLITS = ('UNASSIGNED', 'train', 'validation', 'test')
LOCK = threading.RLock()


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_new(path, data):
    """Publicar un JSON completo, sin reemplazar revisiones anteriores (Windows)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name('.' + path.name + '.' + uuid4().hex + '.tmp')
    try:
        with temp.open('x', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, allow_nan=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        if path.exists():
            raise FileExistsError(path)
        # Todos los escritores de esta herramienta comparten LOCK.
        os.rename(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def output_root(path):
    path = Path(path).resolve()
    if not path.is_relative_to(BASE) or path == BASE:
        raise ValueError('Salida solamente en una subcarpeta de detection_manual_v001')
    return path


def dhash(image):
    gray = cv2.resize(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), (9, 8))
    return format(int(''.join('1' if x else '0' for x in (gray[:, 1:] > gray[:, :-1]).flat), 2), '016x')


def sample_indices(pts, interval):
    if not math.isfinite(interval) or interval < .5:
        raise ValueError('Intervalo mínimo de 0.5 s')
    result = [0]
    for i, t in enumerate(pts):
        if t - pts[result[-1]] >= interval:
            result.append(i)
    if pts[-1] - pts[result[-1]] >= interval / 2:
        result.append(len(pts) - 1)
    return result


def prepare(path, sources, interval=1.0):
    path = output_root(path)
    if path.exists():
        raise FileExistsError('No sobrescribir dataset existente')
    videos = []
    for source in sources:
        source = Path(source).resolve()
        signature = sha(source)
        if any(v['video_sha256'] == signature for v in videos):
            raise ValueError('Video duplicado')
        info = video_tools.inspect_video(source)
        videos.append({'video_id': 'vid_' + signature[:24], 'video_sha256': signature,
                       'source_path': str(source), 'original_filename': source.name,
                       'session_id': None, 'license': None, 'rights_holder': None,
                       'capture_date': None, 'source_status': 'USER_SUPPLIED_REFERENCE_RIGHTS_UNCONFIRMED',
                       'metadata': info})
    path.mkdir(parents=True)
    frames = []
    for v in videos:
        info = v['metadata']; indices = set(sample_indices(info['pts_seconds'], interval))
        cap = cv2.VideoCapture(v['source_path'])
        try:
            for index in range(info['frames']):
                ok, image = cap.read()
                if not ok:
                    raise ValueError('Decodificación incompleta')
                if index not in indices:
                    continue
                identity = v['video_id'] + '_f' + str(index).zfill(6)
                relative = 'images/' + identity + '.png'
                target = path / relative; target.parent.mkdir(exist_ok=True)
                ok, encoded = cv2.imencode('.png', image)
                if not ok:
                    raise ValueError('No se pudo generar PNG')
                with target.open('xb') as f:
                    f.write(encoded.tobytes())
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                frames.append({'sample_id': identity, 'video_id': v['video_id'],
                    'video_sha256': v['video_sha256'], 'frame_index': index,
                    'pts_seconds': info['pts_seconds'][index],
                    'timestamp_seconds': info['pts_seconds'][index] - info['time_origin_pts_seconds'],
                    'timestamp_method': info['timestamp_method'], 'image': relative,
                    'image_sha256': sha(target), 'width': image.shape[1], 'height': image.shape[0],
                    'dhash': dhash(image), 'laplacian_variance': float(cv2.Laplacian(gray, cv2.CV_64F).var()),
                    'derivation': 'PNG sin pérdida del fotograma decodificado completo; no es el MP4 original'})
        finally:
            cap.release()
        if sha(v['source_path']) != v['video_sha256']:
            raise ValueError('Video cambió durante extracción')
    manifest = {'schema_version': 1, 'created_at_utc': now(), 'classes': list(CLASSES),
                'sampling_interval_seconds': interval, 'sampling': 'temporal deterministic, not semantic selection',
                'videos': videos, 'frames': frames, 'automatic_boxes': False,
                'quality_models': {'RAYADURA': 'NO DISPONIBLE', 'DEFORMACION': 'NO DISPONIBLE',
                                   'TAPA_DEFECTUOSA': 'NO HABILITADO'}}
    write_new(path / 'manifest.json', manifest)
    return Dataset(path).report()


def required(value, name):
    if not isinstance(value, str) or not value.strip() or len(value) > 500:
        raise ValueError('Falta ' + name + ' o longitud excesiva')
    return value.strip()


def identity(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,100}', value):
        raise ValueError('Identificador inválido')
    return value


class Dataset:
    def __init__(self, path):
        self.path = output_root(path)
        self.manifest = read(self.path / 'manifest.json')
        self.frames = {f['sample_id']: f for f in self.manifest['frames']}
        if len(self.frames) != len(self.manifest['frames']):
            raise ValueError('sample_id duplicado')
        videos = {v['video_id']: v for v in self.manifest['videos']}
        seen = set()
        for sid, frame in self.frames.items():
            identity(sid)
            v = videos[frame['video_id']]; n = frame['frame_index']
            if (frame['video_id'], n) in seen or type(n) is not int or not 0 <= n < v['metadata']['frames']:
                raise ValueError('Fotograma repetido o índice inválido')
            seen.add((frame['video_id'], n))
            if frame['video_sha256'] != v['video_sha256'] or frame['pts_seconds'] != v['metadata']['pts_seconds'][n] or abs(frame['timestamp_seconds']-(frame['pts_seconds']-v['metadata']['time_origin_pts_seconds'])) > 1e-9:
                raise ValueError('Trazabilidad de fotograma inconsistente')
            self.image_path(frame)

    def image_path(self, frame):
        path = (self.path / frame['image']).resolve()
        if not path.is_relative_to(self.path / 'images') or path.suffix != '.png':
            raise ValueError('Ruta de imagen inválida')
        return path

    def latest(self, sample_id):
        if sample_id not in self.frames:
            raise ValueError('Muestra desconocida')
        files = sorted((self.path / 'revisions' / sample_id).glob('*.json'))
        return read(files[-1]) if files else {'sample_id': sample_id, 'revision': 0,
            'author': '', 'status': 'draft', 'exhaustive': False, 'empty_confirmed': False,
            'notes': '', 'boxes': []}

    def validate_annotation(self, sample_id, data):
        frame = self.frames[sample_id]
        if data.get('expected_hash') != frame['image_sha256'] or sha(self.image_path(frame)) != frame['image_sha256']:
            raise ValueError('Hash no coincide')
        required(data.get('author'), 'autor')
        if data.get('status') not in ('draft', 'reviewed'):
            raise ValueError('Estado inválido')
        for k in ('exhaustive', 'empty_confirmed'):
            if type(data.get(k)) is not bool:
                raise ValueError('Confirmación explícita requerida: ' + k)
        if not isinstance(data.get('notes', ''), str) or len(data.get('notes', '')) > 5000:
            raise ValueError('Observaciones inválidas')
        boxes = data.get('boxes')
        if not isinstance(boxes, list) or len(boxes) > 500:
            raise ValueError('Lista de cajas inválida')
        ids = set(); coordinates = set(); physical_envases = set()
        for b in boxes:
            if not isinstance(b, dict):
                raise ValueError('Objeto inválido')
            bid = identity(b.get('box_id'))
            if bid in ids or b.get('class_name') not in CLASSES:
                raise ValueError('ID repetido o clase inválida')
            ids.add(bid)
            coords = b.get('bbox_xyxy')
            if not isinstance(coords, list) or len(coords) != 4 or any(type(x) not in (float, int) or not math.isfinite(x) for x in coords):
                raise ValueError('Coordenadas inválidas')
            x1, y1, x2, y2 = coords
            if not (0 <= x1 < x2 <= frame['width'] and 0 <= y1 < y2 <= frame['height']) or x2-x1 < 2 or y2-y1 < 2:
                raise ValueError('Caja fuera de imagen o menor de 2 píxeles')
            key = (b['class_name'], *coords)
            if key in coordinates:
                raise ValueError('Caja duplicada')
            coordinates.add(key)
            for flag in ('partial', 'occluded', 'not_evaluable'):
                if b.get(flag) is not None and type(b.get(flag)) is not bool:
                    raise ValueError('Atributo debe ser true, false o null')
                if data['status'] == 'reviewed' and b.get(flag) is None:
                    raise ValueError('Resolver atributos antes de finalizar')
            if b.get('physical_id') is not None:
                identity(b['physical_id'])
                if b['class_name'] == 'ENVASE':
                    if b['physical_id'] in physical_envases:
                        raise ValueError('Mismo envase físico repetido en el fotograma')
                    physical_envases.add(b['physical_id'])
            if b.get('parent_envase_box_id') is not None:
                parent = next((p for p in boxes if p['box_id'] == b['parent_envase_box_id']), None)
                if b['class_name'] != 'TAPA' or not parent or parent['class_name'] != 'ENVASE':
                    raise ValueError('Asociación tapa/envase inválida')
                if b.get('physical_id') and parent.get('physical_id') and b['physical_id'] != parent['physical_id']:
                    raise ValueError('Tapa y envase con identidad física contradictoria')
            if not isinstance(b.get('notes', ''), str) or len(b.get('notes', '')) > 2000:
                raise ValueError('Observación de objeto inválida')
        if boxes and data['empty_confirmed']:
            raise ValueError('Imagen con objetos no puede declararse vacía')
        if data['status'] == 'reviewed' and (not data['exhaustive'] or (not boxes and not data['empty_confirmed'])):
            raise ValueError('Finalizar exige revisión exhaustiva y confirmar imágenes realmente vacías')

    def save(self, sample_id, data):
        with LOCK:
            self.validate_annotation(sample_id, data)
            previous = self.latest(sample_id)
            if type(data.get('revision')) is not int or data['revision'] != previous['revision']:
                raise ValueError('Conflicto de versión: recargue antes de guardar')
            frame = self.frames[sample_id]
            result = {'sample_id': sample_id, 'revision': previous['revision'] + 1,
                      'previous_revision_sha256': sha(self.path / 'revisions' / sample_id / f"{previous['revision']:06d}.json") if previous['revision'] else None,
                      'author': data['author'].strip(), 'recorded_at_utc': now(),
                      'status': data['status'], 'exhaustive': data['exhaustive'],
                      'empty_confirmed': data['empty_confirmed'], 'notes': data.get('notes', ''),
                      'boxes': data['boxes'], 'source': frame,
                      'expected_hash': frame['image_sha256'],
                      'review_scope': 'human annotation, not independent quality review'}
            # Una identidad humana nueva también puede unir particiones preexistentes.
            self.components(override={sample_id: result})
            write_new(self.path / 'revisions' / sample_id / f"{result['revision']:06d}.json", result)
            return result

    def grouping_metadata(self):
        files = sorted((self.path / 'grouping_revisions').glob('*.json'))
        return read(files[-1]) if files else {'revision': 0, 'sessions': {}, 'splits': {}}

    def pairs(self):
        frames = list(self.frames.values()); exact = []; similar = []
        for i, a in enumerate(frames):
            for b in frames[i+1:]:
                if a['image_sha256'] == b['image_sha256']:
                    exact.append([a['sample_id'], b['sample_id']])
                distance = (int(a['dhash'], 16) ^ int(b['dhash'], 16)).bit_count()
                if distance <= 4:
                    similar.append({'a': a['sample_id'], 'b': b['sample_id'], 'dhash_distance': distance})
        return exact, similar

    def components(self, override=None, grouping=None):
        grouping = grouping or self.grouping_metadata(); override = override or {}; parent = {}
        def find(x):
            parent.setdefault(x, x)
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]
        def union(a, b):
            parent[find(a)] = find(b)
        for sid, frame in self.frames.items():
            video_id = frame['video_id']; union(sid, 'video:' + video_id)
            # Sesiones desconocidas no justifican independencia: unión conservadora.
            union(sid, 'session:' + (grouping['sessions'].get(video_id) or 'UNKNOWN_SHARED'))
            for box in override.get(sid, self.latest(sid))['boxes']:
                if box.get('physical_id'):
                    union(sid, 'physical:' + box['physical_id'])
        exact, similar = self.pairs()
        for a, b in exact:
            union(a, b)
        for p in similar:
            union(p['a'], p['b'])
        groups = {}
        for sid in self.frames:
            groups.setdefault(find(sid), []).append(sid)
        result = []
        for members in groups.values():
            videos = sorted({self.frames[s]['video_id'] for s in members})
            assigned = {grouping['splits'].get(v, 'UNASSIGNED') for v in videos} - {'UNASSIGNED'}
            if len(assigned) > 1:
                raise ValueError('Fuga entre particiones del mismo componente de origen')
            result.append({'component_id': 'grp_' + hashlib.sha256('|'.join(sorted(members)).encode()).hexdigest()[:20],
                           'sample_ids': sorted(members), 'video_ids': videos,
                           'split': next(iter(assigned), 'UNASSIGNED')})
        return result

    def assign(self, video_id, author, session=None, split=None):
        if video_id not in {v['video_id'] for v in self.manifest['videos']}:
            raise ValueError('Video desconocido')
        required(author, 'autor')
        with LOCK:
            data = self.grouping_metadata(); data['revision'] += 1
            if session is not None:
                data['sessions'][video_id] = identity(session)
            if split is not None:
                if split not in SPLITS:
                    raise ValueError('Partición inválida')
                group = next(g for g in self.components(grouping=data) if video_id in g['video_ids'])
                for v in group['video_ids']:
                    data['splits'][v] = split
            self.components(grouping=data)
            data.update(author=author.strip(), recorded_at_utc=now())
            write_new(self.path / 'grouping_revisions' / f"{data['revision']:06d}.json", data)
            return data

    def report(self, verify=False):
        groups = self.components(); splits = {s: g['split'] for g in groups for s in g['sample_ids']}
        by_video = {}; totals = Counter(); warnings = []; reviewed = 0; eligible = []
        reviewed_totals = Counter(); reviewed_by_split = {split: Counter() for split in SPLITS}
        known_physical = set(); unknown_physical = 0
        if verify:
            for v in self.manifest['videos']:
                if sha(v['source_path']) != v['video_sha256']:
                    raise ValueError('Video original modificado')
        for sid, f in self.frames.items():
            a = self.latest(sid)
            if verify:
                if sha(self.image_path(f)) != f['image_sha256']:
                    raise ValueError('Fotograma alterado')
                decoded = cv2.imread(str(self.image_path(f)))
                if decoded is None or decoded.shape[:2] != (f['height'], f['width']):
                    raise ValueError('Imagen dañada o dimensiones inconsistentes')
                previous_hash = None
                for expected_revision, file in enumerate(sorted((self.path / 'revisions' / sid).glob('*.json')), 1):
                    revision = read(file)
                    if revision['sample_id'] != sid or revision['revision'] != expected_revision or revision['previous_revision_sha256'] != previous_hash or revision['source'] != f:
                        raise ValueError('Cadena de revisión alterada')
                    self.validate_annotation(sid, revision); previous_hash = sha(file)
            entry = by_video.setdefault(f['video_id'], {'frames': 0, 'reviewed_frames': 0, 'ENVASE': 0, 'TAPA': 0, 'splits': Counter()})
            entry['frames'] += 1; entry['splits'][splits[sid]] += 1
            is_reviewed = a['status'] == 'reviewed'; reviewed += is_reviewed; entry['reviewed_frames'] += is_reviewed
            if is_reviewed and all(b.get('not_evaluable') is False for b in a['boxes']):
                eligible.append(sid)
            for b in a['boxes']:
                entry[b['class_name']] += 1; totals[b['class_name']] += 1
                if is_reviewed:
                    reviewed_totals[b['class_name']] += 1
                    reviewed_by_split[splits[sid]][b['class_name']] += 1
                if b.get('physical_id'): known_physical.add(b['physical_id'])
                else: unknown_physical += 1
                if b.get('not_evaluable') is True:
                    totals['not_evaluable_objects'] += 1
                if min(b['bbox_xyxy'][2]-b['bbox_xyxy'][0], b['bbox_xyxy'][3]-b['bbox_xyxy'][1]) < 16:
                    warnings.append({'sample_id': sid, 'box_id': b['box_id'], 'reason': 'region_under_16_pixels'})
            # Cajas muy semejantes de la misma clase requieren inspección, no borrado.
            for i, a_box in enumerate(a['boxes']):
                for b_box in a['boxes'][i+1:]:
                    if a_box['class_name'] == b_box['class_name'] and iou(a_box['bbox_xyxy'], b_box['bbox_xyxy']) > .85:
                        warnings.append({'sample_id': sid, 'reason': 'high_overlap_same_class', 'box_ids': [a_box['box_id'], b_box['box_id']]})
        exact, similar = self.pairs()
        eligible_counts = Counter(splits[s] for s in eligible)
        return {'generated_at_utc': now(), 'frames': len(self.frames), 'videos': len(self.manifest['videos']),
                'reviewed_frames': reviewed, 'unfinished_frames': len(self.frames)-reviewed,
                'objects_including_drafts': {k: totals[k] for k in CLASSES},
                'reviewed_objects': {k: reviewed_totals[k] for k in CLASSES},
                'reviewed_objects_by_partition': {s: {k:c[k] for k in CLASSES} for s,c in reviewed_by_split.items()},
                'declared_physical_ids': sorted(known_physical), 'object_observations_without_physical_id': unknown_physical,
                'not_evaluable_objects': totals['not_evaluable_objects'], 'by_video': by_video,
                'partition_frames': dict(Counter(splits.values())), 'eligible_frames_by_split': dict(eligible_counts),
                'components': groups, 'exact_duplicate_pairs': exact, 'visual_similarity_candidates': similar,
                'annotation_warnings': warnings, 'hashes_verified': verify,
                'possible_blur_frames_laplacian_below_50': [sid for sid,f in self.frames.items() if f.get('laplacian_variance', 50) < 50],
                'low_resolution_frames_under_640x480': [sid for sid,f in self.frames.items() if f['width'] < 640 or f['height'] < 480],
                'unknown_session_video_ids': [v['video_id'] for v in self.manifest['videos'] if not self.grouping_metadata()['sessions'].get(v['video_id'])],
                'license_pending_video_ids': [v['video_id'] for v in self.manifest['videos'] if v['license'] is None],
                'sufficient_for_training': False,
                'verdict': 'NO PREPARADO: requiere anotación exhaustiva, revisión, derechos confirmados y evaluación independiente por origen; número de cajas no equivale a objetos físicos',
                'quality_predictions': 'NO DISPONIBLE; ninguna clase de defecto se infiere de cajas'}

    def export(self):
        with LOCK:
            report = self.report(verify=True)
            splits = {s: g['split'] for g in report['components'] for s in g['sample_ids']}
            accepted = []; skipped = []
            exact_seen = set()
            for sid, f in self.frames.items():
                a = self.latest(sid)
                reason = None
                if a['status'] != 'reviewed': reason = 'not_exhaustively_reviewed'
                elif any(b['not_evaluable'] is not False for b in a['boxes']): reason = 'contains_ignore_regions_no_safe_plain_yolo_export'
                elif f['image_sha256'] in exact_seen: reason = 'duplicate_sha256'
                if reason:
                    skipped.append({'sample_id': sid, 'reason': reason}); continue
                exact_seen.add(f['image_sha256']); accepted.append((sid, f, a))
            target = self.path / 'exports' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '_' + uuid4().hex[:8])
            target.mkdir(parents=True)
            rows = []
            for sid, f, a in accepted:
                relative = 'labels/' + splits[sid] + '/' + sid + '.txt'; dest = target / relative
                dest.parent.mkdir(parents=True, exist_ok=True)
                with dest.open('x', encoding='utf-8') as handle:
                    for b in a['boxes']:
                        x1,y1,x2,y2 = b['bbox_xyxy']; w=f['width']; h=f['height']
                        handle.write(f"{CLASSES.index(b['class_name'])} {(x1+x2)/(2*w):.10f} {(y1+y2)/(2*h):.10f} {(x2-x1)/w:.10f} {(y2-y1)/h:.10f}\n")
                rows.append({'sample_id': sid, 'source': f, 'annotation': a, 'label_file': relative,
                             'label_sha256': sha(dest), 'split': splits[sid], 'image_absolute_path': str(self.path / f['image'])})
            write_new(target / 'traceability.json', {'classes': dict(enumerate(CLASSES)), 'records': rows,
                'skipped': skipped, 'report': report, 'training_ready': False,
                'videos': self.manifest['videos'], 'grouping_revision': self.grouping_metadata(),
                'note': 'Export de etiquetas para revisión, no conjunto de entrenamiento aprobado; imágenes no movidas ni copiadas'})
            return {'export_directory': str(target), 'exported_frames': len(rows), 'skipped_frames': len(skipped)}


def iou(a, b):
    area = max(0, min(a[2],b[2])-max(a[0],b[0])) * max(0,min(a[3],b[3])-max(a[1],b[1]))
    return area / max(1e-12, (a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-area)


def make_server(dataset, port=8792):
    token = secrets.token_urlsafe(32)
    class Handler(BaseHTTPRequestHandler):
        def reply(self, code, body, content='application/json; charset=utf-8'):
            if not isinstance(body, bytes): body = json.dumps(body, ensure_ascii=False).encode('utf-8')
            self.send_response(code); self.send_header('Content-Type', content)
            self.send_header('Content-Length', str(len(body))); self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff'); self.end_headers(); self.wfile.write(body)

        def allowed_host(self):
            return self.headers.get('Host') == f'127.0.0.1:{self.server.server_port}'

        def do_GET(self):
            if not self.allowed_host(): return self.reply(403, {'error':'Host inválido'})
            route = urlsplit(self.path).path
            try:
                if route in ('/', '/app.js', '/style.css'):
                    name, content = {'/': ('index.html','text/html; charset=utf-8'), '/app.js':('app.js','text/javascript; charset=utf-8'), '/style.css':('style.css','text/css; charset=utf-8')}[route]
                    return self.reply(200, (BASE / name).read_bytes(), content)
                if route == '/api/state':
                    with LOCK:
                        return self.reply(200, {'token':token, 'manifest': dataset.manifest,
                            'annotations': {sid: dataset.latest(sid) for sid in dataset.frames}, 'report':dataset.report()})
                if route.startswith('/image/'):
                    sid = route.removeprefix('/image/')
                    f = dataset.frames[sid]; path = dataset.image_path(f)
                    if sha(path) != f['image_sha256']: raise ValueError('Hash de imagen cambió')
                    return self.reply(200, path.read_bytes(), 'image/png')
                return self.reply(404, {'error':'Ruta desconocida'})
            except (KeyError, ValueError) as e:
                return self.reply(400, {'error':str(e)})

        def do_POST(self):
            origin = f'http://127.0.0.1:{self.server.server_port}'
            if not self.allowed_host() or self.headers.get('Origin') != origin or self.headers.get('X-Annotation-Token') != token:
                return self.reply(403, {'error':'Origen o token inválido'})
            try:
                length = int(self.headers.get('Content-Length','0'))
                if not 0 < length <= 1048576: raise ValueError('Tamaño de solicitud inválido')
                if self.headers.get_content_type() != 'application/json': raise ValueError('JSON requerido')
                data = json.loads(self.rfile.read(length))
                route = urlsplit(self.path).path
                if route == '/api/save': result = dataset.save(data['sample_id'],data)
                elif route == '/api/export': result = dataset.export()
                else: return self.reply(404, {'error':'Ruta desconocida'})
                return self.reply(200,result)
            except (ValueError, KeyError, TypeError) as e:
                return self.reply(400, {'error':str(e)})
            except OSError:
                return self.reply(500, {'error':'No se pudo escribir; vuelva a cargar y compruebe el almacenamiento'})
        def log_message(self, format, *args):
            pass
    return ThreadingHTTPServer(('127.0.0.1',port), Handler)


def serve(dataset, port=8792):
    server = make_server(dataset, port)
    print(f'Anotación manual: http://127.0.0.1:{server.server_port}/', flush=True)
    server.serve_forever()


def main():
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='command',required=True)
    prepare_p=sub.add_parser('prepare'); prepare_p.add_argument('--output', required=True)
    prepare_p.add_argument('--input', action='append', required=True); prepare_p.add_argument('--interval',type=float,default=1.0)
    for name in ('serve','report','export','assign'):
        cmd=sub.add_parser(name); cmd.add_argument('--dataset',required=True)
        if name=='serve': cmd.add_argument('--port',type=int,default=8792)
        if name=='report': cmd.add_argument('--output')
        if name=='assign':
            cmd.add_argument('--video-id',required=True);cmd.add_argument('--author',required=True)
            cmd.add_argument('--session-id');cmd.add_argument('--split',choices=SPLITS)
    a=p.parse_args()
    if a.command=='prepare': result=prepare(a.output,a.input,a.interval)
    else:
        ds=Dataset(a.dataset)
        if a.command=='serve': return serve(ds,a.port)
        if a.command=='report':
            result=ds.report(verify=True)
            if a.output: write_new(output_root(a.output),result)
        if a.command=='export': result=ds.export()
        if a.command=='assign':
            if a.session_id is None and a.split is None: p.error('Indique sesión conocida o partición')
            result=ds.assign(a.video_id,a.author,a.session_id,a.split)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
