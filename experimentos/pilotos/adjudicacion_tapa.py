"""Registro humano versionado para siete conflictos; no modifica referencias."""
import hashlib
import json
import os
from pathlib import Path
import uuid
from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_safe
from .fuentes import ROOT, REFERENCIAS
from .media import respuesta_archivo
from .portal import contexto

FUENTE=ROOT/'output/auditoria_tapas_v002_001/procedencia_conflictos.json'


def casos():
    return json.loads(FUENTE.read_text(encoding='utf-8'))


def raiz():
    destino=Path(getattr(settings,'TAPA_ADJUDICACIONES_ROOT',ROOT/'output/fase22_tapa_v002_001/decisiones')).resolve()
    if not destino.is_relative_to((ROOT/'output').resolve()):
        raise ValueError('Las adjudicaciones solo se guardan en output experimental')
    return destino


def historial(numero):
    if numero not in range(1,len(casos())+1):raise Http404
    resultado=[];previo=None
    for i,p in enumerate(sorted((raiz()/str(numero)).glob('*.json')),1):
        actual=json.loads(p.read_text(encoding='utf-8'))
        if actual['revision']!=i or actual['hash_anterior']!=previo:
            raise ValueError('Historial de adjudicación inconsistente')
        if actual['box_id']!=casos()[numero-1]['box_id']:
            raise ValueError('Conflicto incompatible con historial')
        resultado.append(actual);previo=hashlib.sha256(p.read_bytes()).hexdigest()
    return resultado


def guardar_decision(numero, *, version, estado, clase, autor, justificacion, usuario):
    if numero not in range(1,len(casos())+1):raise Http404
    if estado not in ('PENDIENTE','ADJUDICADO') or clase not in ('','ENVASE','TAPA','NO_EVALUABLE'):
        raise ValueError('Decisión o clase no válida')
    if not autor.strip() or len(autor)>120 or not justificacion.strip() or len(justificacion)>3000:
        raise ValueError('Indique autor real y justificación (máximo 3000 caracteres)')
    if estado=='ADJUDICADO' and not clase:
        raise ValueError('Seleccione clase o NO EVALUABLE explícitamente')
    if estado=='PENDIENTE' and clase:
        raise ValueError('Un caso pendiente no debe llevar clase adjudicada')
    carpeta=raiz()/str(numero);carpeta.mkdir(parents=True,exist_ok=True)
    lock=carpeta/'revision.lock'
    try:fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    except FileExistsError:raise RuntimeError('Otra revisión en curso; recargue')
    temporal=None
    try:
        os.close(fd);anteriores=historial(numero)
        if version!=str(len(anteriores)):raise RuntimeError('La versión cambió; recargue antes de guardar')
        c=casos()[numero-1]
        previo=carpeta/f'{len(anteriores):06d}.json'
        registro={'revision':len(anteriores)+1,'hash_anterior':hashlib.sha256(previo.read_bytes()).hexdigest() if anteriores else None,
                  'sample_id':c['sample_id'],'box_id':c['box_id'],'clase_original':c['clase_guardada'],
                  'revision_original_sha256':c['revision_sha256'],'bbox_original':c['bbox_xyxy'],
                  'nota_original':c['nota_humana'],'estado':estado,
                  'clase_adjudicada':clase if clase in ('ENVASE','TAPA') else None,
                  'evaluabilidad_adjudicada':False if clase=='NO_EVALUABLE' else None,
                  'autor':autor.strip(),'cuenta_usuario':usuario,'fecha_utc':timezone.now().isoformat(),
                  'justificacion':justificacion.strip(),'segunda_revision_independiente':'NO_ACREDITADA',
                  'aplicado_a_anotaciones':False,'habilita_entrenamiento':False}
        temporal=carpeta/(uuid.uuid4().hex+'.tmp')
        with temporal.open('x',encoding='utf-8') as f:json.dump(registro,f,ensure_ascii=False,indent=2)
        destino=carpeta/f'{len(anteriores)+1:06d}.json'
        if destino.exists():raise RuntimeError('No se sobrescriben decisiones anteriores')
        os.rename(temporal,destino)
    finally:
        if temporal is not None and temporal.exists():temporal.unlink()
        lock.unlink(missing_ok=True)


@login_required(login_url='/admin/login/')
@permission_required('produccion.view_analisisproduccion',raise_exception=True)
@require_http_methods(['GET','POST'])
def revision(request):
    if request.method=='POST':
        if not request.user.has_perm('produccion.change_inspeccioncalidad'):
            return HttpResponseForbidden('No tiene permiso para adjudicar referencias de Calidad')
        try:
            numero=int(request.POST.get('caso',''))
            guardar_decision(numero,version=request.POST.get('version',''),estado=request.POST.get('estado',''),clase=request.POST.get('clase',''),autor=request.POST.get('autor',''),justificacion=request.POST.get('justificacion',''),usuario=request.user.get_username())
        except ValueError as e:return HttpResponse(str(e),status=400)
        except RuntimeError as e:return HttpResponse(str(e),status=409)
        return redirect('/demo/calidad/adjudicacion/#caso-'+str(numero))
    lista=[]
    for n,c in enumerate(casos(),1):
        h=historial(n)
        lista.append({'numero':n,**c,'historial':h,'version':len(h),'estado':h[-1]['estado'] if h else 'PENDIENTE'})
    ctx=contexto(request);ctx.update(modulo='calidad',casos=lista,adjudicados=sum(c['estado']=='ADJUDICADO' for c in lista),pendientes=sum(c['estado']=='PENDIENTE' for c in lista),puede_revisar=request.user.has_perm('produccion.change_inspeccioncalidad'))
    return render(request,'demo/adjudicacion_tapa.html',ctx)


@login_required(login_url='/admin/login/')
@permission_required('produccion.view_analisisproduccion',raise_exception=True)
@require_safe
def imagen(request,numero,tipo):
    if numero not in range(1,len(casos())+1) or tipo not in ('original','caja'):raise Http404
    c=casos()[numero-1]
    if tipo=='original':
        ruta=REFERENCIAS/'images'/f'{c["sample_id"]}.png'
    else:ruta=ROOT/'output/auditoria_tapas_v002_001/imagenes'/f'conflicto_{numero:02d}.jpg'
    return respuesta_archivo(request,ruta)
