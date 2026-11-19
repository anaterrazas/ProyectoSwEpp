"""Revisión humana v4: fuentes inmutables y generaciones JSON fuera de SQLite."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import uuid

from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from django.http import Http404, HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods, require_safe

from .fuentes import ROOT
from .media import respuesta_archivo
from .portal import contexto

BASE = ROOT / 'output/preparacion_tapa_fase25_v002_001'
RAW = ROOT / 'datasets/publicos_calidad_botellas/raw/roboflow_bottle_v4/extracted/train'
CONFLICTOS = {31, 123, 204, 567, 134, 324, 773}
CLASES = ('ENVASE', 'TAPA', 'NO_EVALUABLE', 'PENDIENTE')
VISIBILIDAD = ('NO_REVISADA', 'TOTAL', 'PARCIAL', 'OCLUIDA', 'NO_EVALUABLE', 'DUDOSA')
COCO_SHA = '06dd4e05a2c6c35c3244dcf62840eeb00759ea340726d58868dd87a8362c7f54'


def sha(p):
    with Path(p).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def leer(p):
    return json.loads(p.read_text(encoding='utf-8'))


def raiz():
    p = Path(getattr(settings, 'TAPA_V4_REVISION_ROOT', ROOT / 'output/fase26_tapa_v002_001')).resolve()
    if not p.is_relative_to((ROOT / 'output').resolve()):
        raise ValueError('Solo se permite salida experimental en output')
    return p


def fuente():
    if sha(RAW / '_annotations.coco.json') != COCO_SHA:
        raise ValueError('Cambió la referencia RAW')
    return [json.loads(line) for line in (BASE / 'dataset_candidato.jsonl').read_text(encoding='utf-8').splitlines()]


def imagen_fuente(image_id):
    items = [r for r in fuente() if r['image_id'] == image_id]
    if len(items) != 1:
        raise Http404
    r = items[0]
    p = (ROOT / r['source_image']).resolve()
    if not p.is_relative_to(RAW.resolve()) or sha(p) != r['sha256']:
        raise ValueError('Imagen incompatible con su hash de origen')
    return r, p


def generaciones():
    anteriores = []; previo = None
    for n, folder in enumerate(sorted((raiz() / 'versiones').glob('[0-9]' * 6)), 1):
        d = leer(folder / 'decision.json')
        meta = leer(folder / 'manifest.json')
        if folder.name != f'{n:06d}' or d['revision_global'] != n or d['hash_decision_anterior'] != previo:
            raise ValueError('Historial inconsistente')
        for nombre, digest in meta['sha256'].items():
            if nombre not in ('decision.json', 'dataset.jsonl', 'estado.json') or sha(folder / nombre) != digest:
                raise ValueError('Una versión guardada fue modificada')
        if meta['fuente_coco_sha256'] != COCO_SHA or meta['fuente_candidato_sha256'] != sha(BASE / 'dataset_candidato.jsonl'):
            raise ValueError('La versión no corresponde a la fuente actual')
        anteriores.append(d); previo = sha(folder / 'decision.json')
    return anteriores


def ultimas(historia):
    return {d['image_id']: d for d in historia}


def texto(valor, nombre, maximo=3000):
    if not isinstance(valor, str) or not valor.strip() or len(valor) > maximo:
        raise ValueError(f'Indique {nombre} (máximo {maximo} caracteres)')
    return valor.strip()


def validar(payload, r):
    if not isinstance(payload, dict):
        raise ValueError('Se esperaba un objeto JSON')
    if payload.get('expected_sha256') != r['sha256']:
        raise ValueError('Hash de imagen incompatible')
    autor = texto(payload.get('autor'), 'autor real', 120)
    justificacion = texto(payload.get('justificacion'), 'justificación')
    decisiones = payload.get('decisiones', [])
    nuevas = payload.get('nuevas_cajas', [])
    if not isinstance(decisiones, list) or not isinstance(nuevas, list) or len(nuevas) > 500:
        raise ValueError('Lista de cajas no válida')
    originales = {a['id']: a for a in r['source_annotations_cap']}
    vistos = set(); normalizadas = []
    for d in decisiones:
        if not isinstance(d, dict) or type(d.get('annotation_id')) is not int:
            raise ValueError('Identificador de caja inválido')
        aid = d['annotation_id']
        if aid not in originales or aid in vistos or d.get('clase') not in CLASES:
            raise ValueError('Caja repetida, ajena o clase inválida')
        vistos.add(aid)
        vis = d.get('visibilidad', 'NO_REVISADA')
        if vis not in VISIBILIDAD:
            raise ValueError('Visibilidad inválida')
        normalizadas.append(dict(annotation_id=aid, clase=d['clase'], visibilidad=vis,
                                  justificacion=texto(d.get('justificacion'), 'justificación por caja'),
                                  clase_original='cap', bbox_original=originales[aid]['bbox']))
    cajas = []; ids = set()
    for b in nuevas:
        if not isinstance(b, dict) or b.get('clase') not in ('TAPA', 'ENVASE') or b.get('visibilidad') not in VISIBILIDAD:
            raise ValueError('Clase o visibilidad de caja nueva inválida')
        bid = b.get('id')
        if not isinstance(bid, str) or len(bid) > 80 or not bid.startswith('manual-') or bid in ids:
            raise ValueError('Identificador de caja nueva inválido')
        ids.add(bid)
        xy = b.get('bbox_xyxy')
        if not isinstance(xy, list) or len(xy) != 4 or any(type(v) not in (int, float) or not math.isfinite(v) for v in xy):
            raise ValueError('Coordenadas no finitas o inválidas')
        x1,y1,x2,y2 = xy
        if not (0 <= x1 < x2 <= r['width'] and 0 <= y1 < y2 <= r['height']):
            raise ValueError('Caja fuera de imagen o sin área')
        cajas.append(dict(id=bid, clase=b['clase'], bbox_xyxy=xy, visibilidad=b['visibilidad'],
                          justificacion=texto(b.get('justificacion'), 'justificación de caja nueva')))
    exhaustividad = payload.get('exhaustividad', 'PENDIENTE')
    if exhaustividad not in ('PENDIENTE', 'COMPLETA', 'INCOMPLETA', 'NO_EVALUABLE'):
        raise ValueError('Exhaustividad inválida')
    # Declarar exhaustividad exige resolver las cajas de la imagen; una imagen
    # sin tapas no pasa a negativo automáticamente, incluso con revisión completa.
    if exhaustividad == 'COMPLETA' and (vistos != set(originales) or any(d['clase'] == 'PENDIENTE' for d in normalizadas)):
        raise ValueError('Resuelva todas las cajas de esta imagen antes de declarar cobertura completa')
    return dict(autor=autor, justificacion=justificacion, decisiones=normalizadas,
                nuevas_cajas=cajas, exhaustividad=exhaustividad)


def derivar(records, historia):
    actuales = ultimas(historia); resultado = deepcopy(records)
    for r in resultado:
        rev = actuales.get(r['image_id']); decisiones = {d['annotation_id']: d for d in rev['decisiones']} if rev else {}
        efectivas = []
        for a in r['source_annotations_cap']:
            d = decisiones.get(a['id'])
            clase = d['clase'] if d else ('PENDIENTE' if a['id'] in CONFLICTOS else 'TAPA')
            efectivas.append(dict(source_annotation_id=a['id'], bbox_xywh=a['bbox'],
                                  clase=clase, evaluable=False if clase in ('NO_EVALUABLE','PENDIENTE') else None,
                                  estado='ADJUDICADA' if d else 'ORIGINAL_NO_REVISADA',
                                  visibilidad=d['visibilidad'] if d else 'NO_REVISADA'))
        if rev:
            for b in rev['nuevas_cajas']:
                efectivas.append(dict(id=b['id'], bbox_xyxy=b['bbox_xyxy'], clase=b['clase'],
                                      visibilidad=b['visibilidad'], estado='AGREGADA_POR_PERSONA', evaluable=None))
        r.update(effective_annotations=efectivas, human_revision=rev['revision_global'] if rev else None,
                 annotation_exhaustivity=rev['exhaustividad'] if rev else 'PENDIENTE', training_approved=False,
                 partition_approved=False, status='PENDIENTE_CIERRE_SEMANTICA_COBERTURA_PROCEDENCIA')
    return resultado


def resumen(records, historia):
    actuales = ultimas(historia); resueltos = set()
    for d in actuales.values():
        resueltos.update(b['annotation_id'] for b in d['decisiones'] if b['clase'] != 'PENDIENTE' and b['annotation_id'] in CONFLICTOS)
    pendientes = sorted(CONFLICTOS - resueltos)
    return dict(revision_global=len(historia), conflictos_resueltos=sorted(resueltos), conflictos_pendientes=pendientes,
                imagenes_revisadas=len(actuales), imagenes_cobertura_completa=[i for i,d in actuales.items() if d['exhaustividad']=='COMPLETA'],
                imagen24_estado=actuales.get(24, {}).get('exhaustividad', 'PENDIENTE'),
                cajas_nuevas=sum(len(d['nuevas_cajas']) for d in actuales.values()),
                entrenamiento_autorizado=False, independencia_grupos='NO_CERTIFICADA',
                grupos_indivisibles=14, grupos_publicos_previos=202, negativo_inferido=False,
                referencia_propia_excluida=True, fuentes_originales_modificadas=False,
                motivos_bloqueo=['Conflictos pendientes' if pendientes else 'Revisar cierre de adjudicación',
                                'Exhaustividad del conjunto reservado pendiente', 'Independencia y procedencia de grupos sin certificar'])


def guardar(image_id, payload, usuario):
    r, _ = imagen_fuente(image_id)
    data = validar(payload, r)
    root = raiz(); root.mkdir(parents=True, exist_ok=True)
    lock = root / 'revision.lock'
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise RuntimeError('Hay otro guardado; recargue antes de continuar')
    temporal = None
    try:
        os.close(fd)
        historia = generaciones()
        if type(payload.get('version')) is not int or payload['version'] != len(historia):
            raise RuntimeError('La versión cambió; recargue para evitar sobrescribir otra revisión')
        n = len(historia)+1
        previo = root / 'versiones' / f'{n-1:06d}' / 'decision.json'
        d = dict(**data, image_id=image_id, imagen_sha256=r['sha256'], revision_global=n,
                 hash_decision_anterior=sha(previo) if historia else None,
                 cuenta_usuario=usuario, fecha_utc=datetime.now(timezone.utc).isoformat(),
                 fuente_coco_sha256=COCO_SHA, tipo='REVISION_HUMANA_DECLARADA',
                 segunda_revision_independiente='NO_ACREDITADA')
        historia.append(d); records = fuente()
        versiones = root / 'versiones'; versiones.mkdir(exist_ok=True)
        temporal = versiones / ('.pending-' + uuid.uuid4().hex); temporal.mkdir()
        (temporal / 'decision.json').write_text(json.dumps(d, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
        (temporal / 'dataset.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False, allow_nan=False)+'\n' for r in derivar(records, historia)), encoding='utf-8')
        (temporal / 'estado.json').write_text(json.dumps(resumen(records, historia), ensure_ascii=False, indent=2), encoding='utf-8')
        meta = dict(fuente_coco_sha256=COCO_SHA, fuente_candidato_sha256=sha(BASE / 'dataset_candidato.jsonl'),
                    sha256={name:sha(temporal/name) for name in ('decision.json','dataset.jsonl','estado.json')})
        (temporal / 'manifest.json').write_text(json.dumps(meta, indent=2), encoding='utf-8')
        os.rename(temporal, versiones / f'{n:06d}')
        return resumen(records, historia)
    finally:
        if temporal and temporal.exists():
            shutil.rmtree(temporal)
        lock.unlink(missing_ok=True)


def preparar():
    """Primera copia derivada, sin decisiones humanas ni cajas nuevas ficticias."""
    records = fuente()
    for r in records:
        imagen_fuente(r['image_id'])
    grupos = {}
    for r in records:
        anterior = grupos.setdefault(r['group_id'], r['proposed_partition'])
        if anterior != r['proposed_partition']:
            raise ValueError('Grupo dividido entre particiones')
    if len(grupos) != 14 or len({r['sha256'] for r in records}) != len(records):
        raise ValueError('Grupos o duplicados incompatibles')
    restricciones = leer(ROOT / 'output/auditoria_roboflow_v4_v002_001/restricciones_202_grupos.json')
    if sha(ROOT / restricciones['origen']) != restricciones['sha256']:
        raise ValueError('Cambió la restricción de los 202 grupos anteriores')
    destino = raiz() / 'inicial'
    destino.mkdir(parents=True, exist_ok=False)
    (destino/'dataset.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False)+'\n' for r in derivar(records, [])), encoding='utf-8')
    (destino/'estado.json').write_text(json.dumps(resumen(records, []), ensure_ascii=False, indent=2), encoding='utf-8')
    (destino/'manifest.json').write_text(json.dumps(dict(fuente_coco_sha256=COCO_SHA, fuente_candidato_sha256=sha(BASE/'dataset_candidato.jsonl'),
        imagenes_verificadas=262, cajas_fuente=180, grupos=grupos, restricciones_202=restricciones,
        decisiones_humanas=0, entrenamiento_autorizado=False,
        sha256={n:sha(destino/n) for n in ('dataset.jsonl','estado.json')}), ensure_ascii=False, indent=2), encoding='utf-8')
    return destino


@login_required(login_url='/admin/login/')
@permission_required('produccion.view_analisisproduccion', raise_exception=True)
@require_http_methods(['GET', 'POST'])
def revision(request):
    try:
        records = fuente(); historia = generaciones()
        if request.method == 'POST':
            if not request.user.has_perm('produccion.change_inspeccioncalidad'):
                return HttpResponseForbidden('No tiene permiso para adjudicar Calidad')
            if len(request.body) > 500_000:
                return JsonResponse({'error':'Solicitud demasiado grande'}, status=400)
            payload = json.loads(request.body)
            if not isinstance(payload, dict) or type(payload.get('image_id')) is not int:
                raise ValueError('Identificador de imagen inválido')
            return JsonResponse(guardar(payload['image_id'], payload, request.user.get_username()))
        ctx = contexto(request)
        # No se envían rutas locales al navegador.
        imagenes = [{k:r[k] for k in ('image_id','sha256','width','height','group_id','proposed_partition','source_annotations_cap')} for r in records]
        ctx.update(modulo='calidad', datos=dict(imagenes=imagenes, historia=historia, estado=resumen(records,historia), conflictos=sorted(CONFLICTOS)),
                   puede_revisar=request.user.has_perm('produccion.change_inspeccioncalidad'))
        return render(request, 'demo/revision_tapa_v4.html', ctx)
    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        return JsonResponse({'error':'Datos o historial incompatibles. Revise los campos y la integridad de las fuentes.'}, status=400)
    except RuntimeError as e:
        return JsonResponse({'error':str(e)}, status=409)


@login_required(login_url='/admin/login/')
@permission_required('produccion.view_analisisproduccion', raise_exception=True)
@require_safe
def imagen(request, image_id, tipo):
    if tipo not in ('original', 'contexto'):
        raise Http404
    r,p = imagen_fuente(image_id)
    if tipo == 'contexto':
        # Vista ya generada en la auditoría anterior; no se alteran RAW.
        p = ROOT / 'output/auditoria_roboflow_v4_v002_002/galeria' / f'imagen_{image_id:04d}.jpg'
        if not p.is_file():
            raise Http404
    return respuesta_archivo(request, p)


@login_required(login_url='/admin/login/')
@permission_required('produccion.view_analisisproduccion', raise_exception=True)
@require_safe
def descarga(request, numero, nombre):
    historia = generaciones()
    if nombre not in ('decision.json','dataset.jsonl','estado.json','manifest.json') or numero not in range(1,len(historia)+1):
        raise Http404
    return respuesta_archivo(request, raiz() / 'versiones' / f'{numero:06d}' / nombre)
