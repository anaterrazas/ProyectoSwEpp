"""Edición humana de geometría sobre copia JSON; reutiliza medios/permisos LAB."""
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from django.http import Http404, HttpResponseForbidden, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods, require_safe

from .fuentes import ROOT
from .media import respuesta_archivo
from .portal import contexto
from .revision_tapa_v4 import sha, leer, texto

AUDIT=ROOT/'output/fase210_geometria_tapa_v003_001'
PROTOCOLO=ROOT/'docs/PROTOCOLO_TAPA_GEOMETRIA_v1.md'


def sello(registro):
    return hashlib.sha256(json.dumps({k:v for k,v in registro.items() if k!='registro_sha256'},sort_keys=True,ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest()


def catalogo():
    return leer(AUDIT/'catalogo.json')


def caso(numero):
    if type(numero) is not int or numero not in range(len(catalogo())):
        raise Http404
    r=catalogo()[numero]
    if r['case_id']!=numero:
        raise ValueError('Catálogo incompatible')
    return r


def raiz():
    p=Path(getattr(settings,'TAPA_GEOMETRIA_ROOT',AUDIT/'decisiones')).resolve()
    if not p.is_relative_to((ROOT/'output').resolve()):
        raise ValueError('Solo salida experimental')
    return p


def historial():
    result=[];previous=None
    for n,p in enumerate(sorted(raiz().glob('[0-9]'*6+'.json')),1):
        r=leer(p)
        if r.get('registro_sha256')!=sello(r):raise ValueError('Registro alterado')
        source=caso(r['case_id'])
        if p.name!=f'{n:06d}.json' or r['revision']!=n or r['previous_sha256']!=previous:
            raise ValueError('Historial inconsistente')
        if r['source_sha256']!=source['sha256'] or r['bbox_original_xyxy']!=source['bbox_original_xyxy'] or r['protocolo_sha256']!=sha(PROTOCOLO):
            raise ValueError('Referencia o protocolo incompatible')
        result.append(r);previous=sha(p)
    return result


def validar(r,payload):
    if not isinstance(payload,dict) or payload.get('source_sha256')!=r['sha256']:
        raise ValueError('Hash de imagen incompatible')
    if payload.get('protocolo_sha256')!=sha(PROTOCOLO) or payload.get('confirma_protocolo') is not True:
        raise ValueError('Confirme el protocolo geométrico v1')
    decision=payload.get('decision')
    if decision not in ('CONSERVAR','AJUSTADA','NO_EVALUABLE','PENDIENTE'):
        raise ValueError('Decisión no válida')
    bbox=payload.get('bbox_xyxy')
    if decision in ('CONSERVAR','AJUSTADA'):
        if not isinstance(bbox,list) or len(bbox)!=4 or any(type(n) not in (float,int) or not math.isfinite(n) for n in bbox):
            raise ValueError('Coordenadas inválidas')
        x,y,xx,yy=bbox
        if not (0<=x<xx<=r['width'] and 0<=y<yy<=r['height']):
            raise ValueError('Caja fuera de imagen o sin área')
        if decision=='CONSERVAR' and bbox!=r['bbox_original_xyxy']:
            raise ValueError('CONSERVAR exige las coordenadas originales')
        if decision=='AJUSTADA' and (bbox==r['bbox_original_xyxy'] or payload.get('edicion_humana_explicita') is not True):
            raise ValueError('AJUSTADA requiere una edición manual explícita distinta del original')
    elif bbox is not None:
        raise ValueError('Un caso pendiente/no evaluable no lleva caja adjudicada')
    vis=payload.get('visibilidad')
    if vis not in ('TOTAL','PARCIAL','OCLUIDA','DUDOSA','NO_EVALUABLE'):
        raise ValueError('Seleccione visibilidad explícita')
    return dict(decision=decision,bbox_xyxy=bbox,visibilidad=vis,
                autor=texto(payload.get('autor'),'autor real',120),justificacion=texto(payload.get('justificacion'),'justificación'))


def guardar(numero,payload,usuario):
    r=caso(numero);data=validar(r,payload)
    image=(ROOT/r['source_image']).resolve()
    if not image.is_relative_to((ROOT/'datasets/publicos_calidad_botellas').resolve()) or sha(image)!=r['sha256']:
        raise ValueError('Imagen fuente incompatible')
    base=raiz();base.mkdir(parents=True,exist_ok=True);lock=base/'revision.lock'
    try:fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    except FileExistsError:raise RuntimeError('Otro guardado en curso; recargue')
    temp=None
    try:
        os.close(fd);h=historial()
        if type(payload.get('version')) is not int or payload['version']!=len(h):
            raise RuntimeError('Versión obsoleta; recargue antes de guardar')
        n=len(h)+1
        d=dict(**data,case_id=numero,revision=n,source_sample_id=r['source_sample_id'],source_class=r['source_class'],
               source_sha256=r['sha256'],bbox_original_xyxy=r['bbox_original_xyxy'],
               previous_sha256=sha(base/f'{n-1:06d}.json') if h else None,
               protocolo_sha256=sha(PROTOCOLO),cuenta_usuario=usuario,fecha_utc=datetime.now(timezone.utc).isoformat(),
               entrenamiento_autorizado=False,segunda_revision_independiente='NO_ACREDITADA')
        d['registro_sha256']=sello(d)
        temp=base/('.'+uuid4().hex+'.tmp')
        with temp.open('x',encoding='utf-8') as f:
            json.dump(d,f,ensure_ascii=False,indent=2,allow_nan=False);f.flush();os.fsync(f.fileno())
        os.rename(temp,base/f'{n:06d}.json')
        return d
    finally:
        if temp and temp.exists():temp.unlink()
        lock.unlink(missing_ok=True)


def derivada():
    h=historial();latest={d['case_id']:d for d in h};records=[]
    for r in catalogo():
        d=latest.get(r['case_id'])
        records.append({**r,'human_revision':d,
            'bbox_humana_xyxy':d['bbox_xyxy'] if d else None,
            'estado_humano':d['decision'] if d else 'PENDIENTE','training_approved':False})
    return dict(protocolo_sha256=sha(PROTOCOLO),revision=len(h),records=records,entrenamiento_autorizado=False,
                estado='AJUSTES_Y_TEST_PENDIENTES',fuente_modificada=False)


@login_required(login_url='/admin/login/')
@permission_required('produccion.view_analisisproduccion',raise_exception=True)
@require_http_methods(['GET','POST'])
def revision(request):
    try:
        if request.method=='POST':
            if not request.user.has_perm('produccion.change_inspeccioncalidad'):
                return HttpResponseForbidden('No tiene permiso para ajustar Calidad')
            if len(request.body)>50000:raise ValueError('Solicitud demasiado grande')
            p=json.loads(request.body)
            if not isinstance(p,dict):raise ValueError('Solicitud inválida')
            d=guardar(p.get('case_id'),p,request.user.get_username())
            return JsonResponse(dict(revision=d['revision'],decision=d['decision']))
        h=historial()
        safe=[{k:r[k] for k in ('case_id','source','source_sample_id','source_class','width','height','group_id','sha256','bbox_original_xyxy','audit_status','audit_note')} for r in catalogo()]
        ctx=contexto(request);ctx.update(modulo='calidad',datos=dict(casos=safe,historial=h,version=len(h),protocolo_sha256=sha(PROTOCOLO)),
            puede_revisar=request.user.has_perm('produccion.change_inspeccioncalidad'))
        return render(request,'demo/geometria_tapa.html',ctx)
    except (ValueError,TypeError,KeyError):return JsonResponse({'error':'Datos o historial inválidos. Verifique coordenadas, campos, protocolo y referencias.'},status=400)
    except RuntimeError as e:return JsonResponse({'error':str(e)},status=409)


@login_required(login_url='/admin/login/')
@permission_required('produccion.view_analisisproduccion',raise_exception=True)
@require_safe
def imagen(request,numero):
    r=caso(numero);p=(ROOT/r['source_image']).resolve()
    if not p.is_relative_to((ROOT/'datasets/publicos_calidad_botellas').resolve()) or sha(p)!=r['sha256']:
        raise Http404
    return respuesta_archivo(request,p)


@login_required(login_url='/admin/login/')
@permission_required('produccion.view_analisisproduccion',raise_exception=True)
@require_safe
def exportar(request):
    response=JsonResponse(derivada(),json_dumps_params={'ensure_ascii':False})
    response['Content-Disposition']='attachment; filename="tapa_geometria_copia_experimental.json"'
    return response
