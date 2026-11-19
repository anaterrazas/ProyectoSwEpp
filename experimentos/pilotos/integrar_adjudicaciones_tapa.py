"""Integra decisiones humanas en una copia nueva, sin entrenar ni inferir."""
from copy import deepcopy
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys

from .fuentes import ROOT, REFERENCIAS
from .primera_evaluacion import conflictos_semanticos


def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def aplicar_decisiones(anotacion, decisiones):
    """Solo clases/evaluabilidad explícitas; no geometría, notas, enlaces ni IDs."""
    nueva=deepcopy(anotacion);vistas=set()
    for d in decisiones:
        if d['estado']!='ADJUDICADO' or not d.get('autor','').strip() or not d.get('justificacion','').strip() or not d.get('fecha_utc'):
            raise ValueError('Decisión pendiente o sin identificación/justificación/fecha')
        if d['sample_id']!=nueva['sample_id'] or d['box_id'] in vistas:raise ValueError('Muestra o decisión repetida incompatible')
        vistas.add(d['box_id'])
        boxes=[b for b in nueva['boxes'] if b['box_id']==d['box_id']]
        if len(boxes)!=1:raise ValueError('Caja adjudicada inexistente o duplicada')
        b=boxes[0]
        if b['class_name']!=d['clase_original'] or b['bbox_xyxy']!=d['bbox_original'] or b.get('notes','')!=d['nota_original']:
            raise ValueError('La decisión no corresponde a la anotación original')
        if d.get('clase_adjudicada') in ('ENVASE','TAPA'):
            if d.get('evaluabilidad_adjudicada') is not None:raise ValueError('Decisión de clase/evaluabilidad contradictoria')
            b['class_name']=d['clase_adjudicada']
        elif d.get('clase_adjudicada') is None and d.get('evaluabilidad_adjudicada') is False:
            b['not_evaluable']=True
        else:raise ValueError('Clase adjudicada inválida')
    return nueva


def ejecutar(salida,copia):
    import os
    os.environ['DJANGO_SETTINGS_MODULE']='experimentos.pilotos.settings'
    import django;django.setup()
    from .adjudicacion_tapa import casos,historial,raiz
    salida=salida.resolve();copia=copia.resolve()
    if not salida.is_relative_to(ROOT/'output') or not copia.is_relative_to(REFERENCIAS.parent) or copia==REFERENCIAS:
        raise ValueError('Solo salidas experimentales independientes')
    if salida.exists() or copia.exists():raise FileExistsError('No sobrescribir resultados o datasets')
    # Verificar cadenas y cada decisión contra la revisión de origen.
    decisiones=[];archivos_decision=[]
    for n,c in enumerate(casos(),1):
        h=historial(n)
        if not h or h[-1]['estado']!='ADJUDICADO':raise ValueError(f'Conflicto {n} no resuelto')
        d=h[-1];p=raiz()/str(n)/f'{d["revision"]:06d}.json'
        for key,val in [('sample_id',c['sample_id']),('box_id',c['box_id']),('clase_original',c['clase_guardada']),('revision_original_sha256',c['revision_sha256'])]:
            if d[key]!=val:raise ValueError(f'Procedencia incompatible en conflicto {n}')
        original=sorted((REFERENCIAS/'revisions'/c['sample_id']).glob('*.json'))[-1]
        if sha(original)!=d['revision_original_sha256']:raise ValueError('Hay una revisión original posterior o incompatible')
        decisiones.append(d);archivos_decision.append({'caso':n,'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p),'revisiones_verificadas':len(h)})
    # Congelar antes los originales, las decisiones y las evaluaciones previas.
    protegidos={}
    for folder in [REFERENCIAS,ROOT/'output/experimental_pilotos',ROOT/'output/auditoria_tapas_v002_001',ROOT/'output/fase22_tapa_v002_001',ROOT/'produccion',ROOT/'monitoreo',ROOT/'seguridad',ROOT/'config',ROOT/'Modelos']:
        for p in folder.rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.sqlite3','.sqlite3-wal','.sqlite3-shm'):
                protegidos[p.relative_to(ROOT).as_posix()]=sha(p)
    protegidos['db.sqlite3']=sha(ROOT/'db.sqlite3')
    # Reutilizar el escritor, validador, hashes y agrupación del anotador existente.
    spec=importlib.util.spec_from_file_location('anotador_tapa_integracion',REFERENCIAS.parent/'annotate.py')
    manual=importlib.util.module_from_spec(spec);sys.modules[spec.name]=manual;spec.loader.exec_module(manual)
    fuente=manual.Dataset(REFERENCIAS)
    nuevas={}
    for sid in {d['sample_id'] for d in decisiones}:
        a=fuente.latest(sid);b=aplicar_decisiones(a,[d for d in decisiones if d['sample_id']==sid])
        fuente.validate_annotation(sid,b);nuevas[sid]=b
    salida.mkdir(parents=True);copia.mkdir()
    shutil.copy2(REFERENCIAS/'manifest.json',copia/'manifest.json')
    for folder in ['images','revisions','grouping_revisions']:
        if (REFERENCIAS/folder).exists():shutil.copytree(REFERENCIAS/folder,copia/folder)
    ds=manual.Dataset(copia);integraciones=[]
    for sid,b in sorted(nuevas.items()):
        b['author']='sistema.integracion_adjudicaciones'
        b['notes']=(b.get('notes','')+'\nIntegración automática de decisiones humanas: no es una nueva anotación humana ni acredita segunda revisión independiente.').strip()
        creada=ds.save(sid,b)
        integraciones.append({'sample_id':sid,'revision_nueva':creada['revision'],'revision_original_sha256':creada['previous_revision_sha256'],
                              'revision_nueva_sha256':sha(copia/'revisions'/sid/f'{creada["revision"]:06d}.json'),
                              'autor_integracion':creada['author'],'tipo':'DERIVACION_AUTOMATICA_DE_DECISIONES_HUMANAS'})
    records=[{'sample_id':sid,'source':frame,'annotation':ds.latest(sid)} for sid,frame in ds.frames.items()]
    reporte=ds.report(verify=True);conteos=Counter();evals=Counter();vis=Counter();porvideo={}
    for ref in records:
        sid=ref['sample_id'];ant=fuente.latest(sid);nueva=ref['annotation'];antes={b['box_id']:b for b in ant['boxes']}
        assert len(ant['boxes'])==len(nueva['boxes'])
        for b in nueva['boxes']:
            original=antes[b['box_id']]
            for k in original:
                if k not in ('class_name','not_evaluable'):assert b[k]==original[k]
            conteos[b['class_name']]+=1
            if b.get('not_evaluable') is False:evals[b['class_name']]+=1
            v=ref['source']['video_id'];porvideo.setdefault(v,Counter())[b['class_name']]+=1
            if b['class_name']=='TAPA':
                cat='NO_EVALUABLE' if b.get('not_evaluable') else 'OCLUIDA' if b.get('occluded') else 'PARCIAL' if b.get('partial') else 'TOTALMENTE_VISIBLE'
                vis[cat]+=1
    assert sum(conteos.values())==244
    conflictos=conflictos_semanticos(records)
    procedencia={'decisiones':archivos_decision,'decisiones_humanas_completas':decisiones,'integraciones':integraciones,'copia_dataset':copia.relative_to(ROOT).as_posix(),
                 'anotaciones_originales_modificadas':False,'segunda_revision_independiente':'NO_ACREDITADA','exportacion_entrenamiento':False}
    manual.write_new(salida/'procedencia_integracion.json',procedencia)
    manual.write_new(salida/'referencias_adjudicadas.json',{'records':records,'alcance':'COPIA_DERIVADA_NO_TEST_INDEPENDIENTE'})
    manual.write_new(salida/'auditoria_dataset.json',reporte)
    manual.write_new(salida/'resumen.json',{'frames':len(records),'cajas':dict(conteos),'cajas_evaluables':dict(evals),'visibilidad_tapas':dict(vis),'por_video':{k:dict(v) for k,v in porvideo.items()},
        'conflictos_semanticos_pendientes':conflictos,'decisiones_integradas':len(decisiones),'revisiones_derivadas':len(integraciones),'suficiente_entrenamiento_segun_anotador':reporte['sufficient_for_training'],
        'entrenamiento_autorizado':False,'metricas_ia_nuevas':False})
    for d in archivos_decision:
        if sha(ROOT/d['path'])!=d['sha256']:raise RuntimeError('Una decisión cambió durante integración')
    cambios=[p for p,h in protegidos.items() if sha(ROOT/p)!=h]
    if cambios:raise RuntimeError('Originales modificados: '+str(cambios))
    manual.write_new(salida/'protegidos_antes.json',protegidos)
    manual.write_new(salida/'verificacion_integridad.json',{'archivos_protegidos_intactos':len(protegidos),'alterados':cambios,'decisiones_verificadas':7,'cajas_verificadas':244,'inferencias':0,'entrenamientos':0})
    print((salida/'resumen.json').read_text(encoding='utf-8'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--salida',type=Path,required=True);p.add_argument('--copia',type=Path,required=True)
    a=p.parse_args();ejecutar(a.salida,a.copia)
