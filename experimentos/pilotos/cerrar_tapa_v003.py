"""Congela adjudicaciones reales en un candidato v003; no entrena ni infiere."""
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path


def leer(p):
    return json.loads(p.read_text(encoding='utf-8'))


def sha(p):
    with Path(p).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def nuevo(p, data):
    with p.open('x', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, allow_nan=False)


def jsonl(p, records):
    with p.open('x', encoding='utf-8') as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False, allow_nan=False)+'\n')


def analizar(records, historia, conflictos):
    """Cuenta últimas decisiones por imagen; nunca cuenta guardados como muestras."""
    actuales = {d['image_id']:d for d in historia}
    resultado = deepcopy(records)
    cajas = []; problemas = []; resueltos = {}; particiones = defaultdict(lambda:dict(imagenes=0, TAPA=0, ENVASE=0, excluidas=0, nuevas=0, grupos=set(), cobertura=Counter()))
    cobertura = Counter(); visibilidad = defaultdict(Counter)
    grupos = {}; hashes = set(); duplicados = []
    for r in resultado:
        i = r['image_id']; d = actuales.get(i)
        decisiones = {b['annotation_id']:b for b in d['decisiones']} if d else {}
        if len(decisiones) != len(d['decisiones'] if d else []):
            raise ValueError('Decisiones duplicadas')
        destinos = grupos.setdefault(r['group_id'], set()); destinos.add(r['proposed_partition'])
        if r['sha256'] in hashes:
            duplicados.append(i)
        hashes.add(r['sha256'])
        estado = d['exhaustividad'] if d else 'SIN_REVISION'
        cobertura[estado] += 1
        p = particiones[r['proposed_partition']]; p['imagenes'] += 1; p['grupos'].add(r['group_id']);p['cobertura'][estado]+=1
        efectivas = []
        for a in r['source_annotations_cap']:
            dec = decisiones.get(a['id'])
            clase = dec['clase'] if dec else ('PENDIENTE' if a['id'] in conflictos else 'TAPA')
            if dec and (dec['clase_original'] != 'cap' or dec['bbox_original'] != a['bbox']):
                raise ValueError('La decisión cambia o no corresponde a la geometría original')
            vis = dec['visibilidad'] if dec else 'NO_REVISADA'
            item = dict(annotation_id=f'v4:{a["id"]}', source_annotation_id=a['id'], image_id=i,
                        source_class='cap', class_name=clase, bbox_xywh=deepcopy(a['bbox']),
                        visibilidad=vis, revision_global=d['revision_global'] if dec else None,
                        human_reviewed=bool(dec), autor=d['autor'] if dec else None,
                        fecha_utc=d['fecha_utc'] if dec else None,
                        justificacion=dec['justificacion'] if dec else None,
                        excluded_from_positive_labels=clase in ('NO_EVALUABLE','PENDIENTE'),
                        eligible_for_training=False,
                        review_status=('PENDIENTE' if clase=='PENDIENTE' else 'ADJUDICADA') if dec else 'ORIGINAL_NO_REVISADA')
            efectivas.append(item)
            if a['id'] in conflictos:
                resueltos[a['id']] = dict(image_id=i, clase=clase, visibilidad=vis,
                                         revision=d['revision_global'] if dec else None,
                                         guardada=bool(dec), resuelto=bool(dec and clase!='PENDIENTE'))
        if d:
            for b in d['nuevas_cajas']:
                efectivas.append(dict(annotation_id=b['id'], image_id=i, class_name=b['clase'], bbox_xyxy=b['bbox_xyxy'],
                    visibilidad=b['visibilidad'], revision_global=d['revision_global'], human_reviewed=True,
                    autor=d['autor'], fecha_utc=d['fecha_utc'], justificacion=b['justificacion'],
                    excluded_from_positive_labels=False, eligible_for_training=False, review_status='AGREGADA_POR_PERSONA'))
                p['nuevas']+=1
        counts = Counter(b['class_name'] for b in efectivas)
        for b in efectivas:
            if b['class_name'] in ('TAPA','ENVASE'):
                p[b['class_name']]+=1
            else:
                p['excluidas']+=1
            visibilidad[b['class_name']][b['visibilidad']]+=1
        # Incidencias de esta auditoría, respaldadas por las notas humanas reales.
        if i in (38,165) and d and estado=='COMPLETA' and counts['TAPA']==0:
            problemas.append(dict(image_id=i, codigo='TAPA_DESCRITA_SIN_CAJA_TAPA',
                revision=d['revision_global'], evidencia_humana=d['justificacion'],
                detalle='La nota humana describe tapa visible y la imagen figura COMPLETA, pero no tiene una caja TAPA efectiva. No se inventa la caja ni se cambia la declaración humana.'))
        if i==9 and d and estado=='PENDIENTE':
            problemas.append(dict(image_id=i, codigo='TEXTO_COMPLETO_ESTADO_PENDIENTE', revision=d['revision_global'], evidencia_humana=d['justificacion'], detalle='El texto declara revisión completa; el selector guardado sigue PENDIENTE. Se conserva el selector.'))
        if estado=='NO_EVALUABLE' and counts['TAPA']:
            problemas.append(dict(image_id=i, codigo='POSITIVO_LOCAL_EN_IMAGEN_NO_EVALUABLE', revision=d['revision_global'], evidencia_humana=d['justificacion'], detalle='Hay TAPA adjudicada localmente y una declaración NO EVALUABLE global. Conservar ambas; falta delimitar su alcance antes de usarla para evaluar o entrenar.'))
        r.update(effective_annotations_v003=efectivas, coverage_human=estado,
                 human_revision=d['revision_global'] if d else None,
                 training_approved=False, partition_approved=False, negative_confirmed=None,
                 status='BLOQUEADO_POR_COBERTURA_E_INDEPENDENCIA')
        cajas.extend(efectivas)
    if 24 not in actuales:
        problemas.append(dict(image_id=24, codigo='REVISION_NO_GUARDADA', detalle='No existe decisión de imagen 24 en las generaciones reales verificadas.'))
    if any(len(s)!=1 for s in grupos.values()):
        raise ValueError('Partición divide un grupo completo')
    if duplicados:
        raise ValueError('Duplicados exactos en particiones candidatas')
    totales = Counter(b['class_name'] for b in cajas)
    historial_igual = []; vistos={}
    for d in historia:
        key=json.dumps({k:d[k] for k in ('image_id','autor','justificacion','exhaustividad','decisiones','nuevas_cajas')}, sort_keys=True, ensure_ascii=False)
        if key in vistos:
            historial_igual.append(dict(revision=d['revision_global'], mismo_contenido_que=vistos[key]))
        else:
            vistos[key]=d['revision_global']
    report=dict(version='TAPA_v003_candidato_001', estado='NO_PREPARADO_PARA_ENTRENAMIENTO_EXPERIMENTAL',
        imagenes=len(records), cajas_fuente=sum(len(r['source_annotations_cap']) for r in records),
        cajas_finales=dict(totales), cajas_fuente_retenidas=sum('source_annotation_id' in b for b in cajas),
        cajas_excluidas_de_positivos=sum(b['excluded_from_positive_labels'] for b in cajas),
        cajas_nuevas=sum('source_annotation_id' not in b for b in cajas),
        tapa_con_revision_humana=sum(b['class_name']=='TAPA' and b['human_reviewed'] for b in cajas),
        tapa_solo_etiqueta_fuente=sum(b['class_name']=='TAPA' and not b['human_reviewed'] for b in cajas),
        conflictos=resueltos, conflictos_pendientes=sorted(a for a in conflictos if not resueltos.get(a,{}).get('resuelto')),
        revisiones_globales=len(historia), imagenes_revisadas=len(actuales),
        cobertura_declarada=dict(cobertura), visibilidad_por_clase={k:dict(v) for k,v in visibilidad.items()},
        particiones={k:{**v,'grupos':sorted(v['grupos']),'cobertura':dict(v['cobertura'])} for k,v in particiones.items()},
        incidencias=problemas, revisiones_repetidas_conservadas=historial_igual,
        grupos_indivisibles=len(grupos), cruces_de_grupo=0, duplicados_exactos=0,
        independencia_de_sesiones='NO_CERTIFICADA', negativos_inferidos=0, entrenamiento_autorizado=False,
        inferencias_ejecutadas=0, entrenamientos_ejecutados=0,
        alcance='Solo candidato Roboflow v4, no suma Mendeley, v26 ni las 244 referencias propias.',
        bloqueos=['No hay revisión guardada de imagen 24.',
                  'Imágenes 38 y 165 declaradas COMPLETA describen tapas visibles sin sus cajas TAPA.',
                  'La exhaustividad de los conjuntos reservados no está acreditada; imágenes sin revisión no son negativos.',
                  'Independencia y procedencia individual de grupos sin certificar.',
                  'Segunda revisión independiente no acreditada.'])
    return resultado,cajas,report


def informe(s):
    filas='\n'.join(f'| {a} | {v["image_id"]} | {v["clase"]} | {v["visibilidad"]} | {v["revision"]} |' for a,v in sorted(s['conflictos'].items()))
    particiones='\n'.join(f'| {k} | {v["imagenes"]} | {v["TAPA"]} | {v["ENVASE"]} | {v["excluidas"]} |' for k,v in s['particiones'].items())
    return f'''# Cierre de adjudicación · TAPA v003

**NO PREPARADO PARA ENTRENAMIENTO EXPERIMENTAL.** Se generó una copia candidata nueva con las decisiones reales, sin entrenar ni inferir. La integridad técnica y la separación por grupos se verificaron; el cierre semántico/exhaustivo y la independencia siguen bloqueados.

## Decisiones guardadas

Se verificaron {s['revisiones_globales']} generaciones, correspondientes a {s['imagenes_revisadas']} imágenes, no diez muestras independientes. Los siete conflictos tienen decisiones explícitas; ninguno queda PENDIENTE de clase. Se preservan también las revisiones repetidas 2 y 3 de imagen 9, y 10 de imagen 223: no se eliminan ni suman cajas por cada guardado.

| Anotación | Imagen | Clase adjudicada | Visibilidad | Última revisión |
|---|---|---|---|---|
{filas}

Además, la caja 203 de imagen 60 está adjudicada TAPA / TOTAL. NO EVALUABLE en 204 y 773 se usa en sus notas para excluir regiones que no son una tapa; en 134 y 324 se declara duda visual. Se conservan esos motivos distintos y sus visibilidades originales; no se traducen a ausencias ni etiquetas negativas.

## Conteos del candidato v003

- TAPA: **{s['cajas_finales'].get('TAPA',0)}**: {s['tapa_con_revision_humana']} con adjudicación humana nueva y {s['tapa_solo_etiqueta_fuente']} conservadas de la fuente sin nueva revisión. No son 173 tapas humanas validadas.
- ENVASE: **{s['cajas_finales'].get('ENVASE',0)}**, provenientes de las reclasificaciones 31, 123 y 567. Este conteo corresponde solo al candidato de tapas; no es el total de envases de todas las fuentes.
- Excluidas de positivos: **{s['cajas_excluidas_de_positivos']}**, anotaciones 134, 204, 324 y 773. Siguen en la trazabilidad como NO EVALUABLE, no se borran.
- Cajas nuevas manuales: **{s['cajas_nuevas']}**. No hay cajas omitidas recuperables de estas diez versiones: todas guardaron `nuevas_cajas: []`.
- Se conservan las {s['cajas_fuente']} cajas fuente: 173 + 3 + 4 = 180. No se modifican las 915 anotaciones RAW ni las 244 referencias propias.

## Exhaustividad: declaración humana frente a comprobación

- COMPLETA: 3 imágenes, 38, 165 y 223.
- INCOMPLETA: 0 declaraciones guardadas. Esto no significa que no existan omisiones.
- NO EVALUABLE: 3 imágenes, 42, 60 y 95.
- PENDIENTE: imagen 9; su nota dice revisión completa pero el selector guardado es PENDIENTE.
- SIN REVISIÓN: 255 imágenes, incluida **24**. No existe una generación de esa imagen: su revisión no está persistida en estos registros.

Las notas de imágenes **38 y 165** dicen que hay una tapa visible, pero su única caja fuente fue adjudicada ENVASE, sin añadir caja TAPA. Por eso su declaración COMPLETA es inconsistente con las cajas disponibles para detección. Se conserva la declaración humana y se añade una incidencia separada, sin inventar coordenadas ni corregir su estado automáticamente.

Imagen 60 contiene la TAPA 203 confirmada localmente y una declaración NO EVALUABLE global, asociada en la nota a la caja inválida de etiqueta 204. Falta aclarar el alcance; no se descarta automáticamente la caja válida ni se aprueba toda la imagen. Imagen 223 describe boca sin tapa; se conserva su texto, sin crear TAPA_AUSENTE ni un negativo automático y sin asumir una estación posterior al tapado.

## Distribución provisional

| Partición | Imágenes | TAPA | ENVASE | Excluidas de positivos |
|---|---:|---:|---:|---:|
{particiones}

Las particiones mantienen los 14 grupos completos y no presentan duplicados exactos ni cruces de grupo. Se conserva por hash la restricción de los 202 grupos anteriores. Eso demuestra separación estructural, no independencia de sesiones. No hay evidencia nueva para certificar independencia/procedencia individual del material web/stock. Los grupos conservan su destino provisional, sin aprobación para entrenar. Las 25 referencias propias siguen separadas y fuera del entrenamiento.

## Comprobaciones y artefactos

Se validan hashes de cada generación y la cadena de decisiones; cada generación se compara con la derivación de las decisiones existentes hasta ese momento, no solo su hash. Se comprueban clases, visibilidad, identificadores, coordenadas, autor, cuenta, fecha y justificación, así como las cajas nuevas (si las hubiera). Las 262 imágenes se verifican contra sus hashes, el COCO y ZIP RAW contra los valores conocidos y las cajas fuente contra COCO.

El dataset es una representación por referencias inmutables (`samples.jsonl` y `annotations.jsonl`), **no una exportación YOLO lista para entrenamiento**. Cada muestra mantiene la ruta de imagen, hash, grupo, destino provisional y referencia humana. Se guardan por separado decisiones, historial completo, exclusiones, incidencias y manifiesto de archivos. Todas las muestras y cajas mantienen entrenamiento deshabilitado.

La verificación de integridad compara la línea base de 26.361 archivos protegidos y una congelación adicional de Fases 2.5 y 2.6. No se modifica EPP, producción, SQLite operativo, pesos, referencias originales ni evaluaciones anteriores.

## Siguiente paso mínimo

1. Guardar realmente la revisión de imagen 24 en la herramienta existente.
2. En 38 y 165, añadir manualmente las cajas TAPA que la revisora describe, o corregir explícitamente el alcance/estado si corresponde. No basta reclasificar la botella.
3. Aclarar el estado de imagen 9 y el alcance NO EVALUABLE de 60, sin cambiar las decisiones válidas ya realizadas.
4. Cerrar exhaustividad del subconjunto reservado y acreditar independencia/procedencia de sus grupos. Las imágenes sin referencia suficiente siguen fuera de una aprobación de entrenamiento/evaluación.

No hacen falta nuevas etiquetas inventadas ni repetir las siete adjudicaciones. La segunda revisión independiente sigue no acreditada. No se solicita nueva captura en esta fase. No se calculan métricas de IA.
'''


def ejecutar(salida, dataset):
    os.environ['DJANGO_SETTINGS_MODULE']='experimentos.pilotos.settings'
    import django
    django.setup()
    from . import revision_tapa_v4 as v
    salida=salida.resolve();dataset=dataset.resolve()
    if not salida.is_relative_to(v.ROOT/'output') or not dataset.is_relative_to(v.ROOT/'datasets/calidad_botellas/v003'):
        raise ValueError('Solo salidas nuevas experimentales v003')
    if salida.exists() or dataset.exists():
        raise FileExistsError('No sobrescribir datasets ni informes previos')
    records=v.fuente();historia=v.generaciones()
    if not historia:
        raise ValueError('No hay adjudicaciones reales')
    records_by_id={r['image_id']:r for r in records}
    protegidos=leer(v.ROOT/'output/auditoria_datasets_calidad_v002_001/protegidos_antes.json')
    adicionales={}
    for folder in (v.BASE,v.raiz()):
        for p in folder.rglob('*'):
            if p.is_file():
                adicionales[p.relative_to(v.ROOT).as_posix()]=sha(p)
    historial_archivos=[]
    for n,d in enumerate(historia,1):
        r=records_by_id[d['image_id']]
        if d['imagen_sha256']!=r['sha256'] or d['fuente_coco_sha256']!=v.COCO_SHA:
            raise ValueError('Procedencia de decisión incompatible')
        v.texto(d['cuenta_usuario'],'cuenta autenticada',150)
        dt=datetime.fromisoformat(d['fecha_utc'])
        if dt.utcoffset() is None:
            raise ValueError('Fecha sin zona horaria')
        normal=v.validar({**d,'expected_sha256':d['imagen_sha256']},r)
        for key,val in normal.items():
            if d[key]!=val:
                raise ValueError(f'Decisión incompatible con validador: {key}')
        f=v.raiz()/'versiones'/f'{n:06d}'
        snapshot=[json.loads(s) for s in (f/'dataset.jsonl').read_text(encoding='utf-8').splitlines()]
        if snapshot!=v.derivar(records,historia[:n]):
            raise ValueError(f'La generación {n} no coincide con sus decisiones')
        if leer(f/'estado.json')!=v.resumen(records,historia[:n]):
            raise ValueError('Resumen histórico incompatible')
        for name in ('decision.json','dataset.jsonl','estado.json','manifest.json'):
            p=f/name;historial_archivos.append(dict(path=p.relative_to(v.ROOT).as_posix(),sha256=sha(p)))
    coco=leer(v.RAW/'_annotations.coco.json')
    cap_por_imagen=defaultdict(list)
    for a in coco['annotations']:
        if a['category_id']==1:
            cap_por_imagen[a['image_id']].append(a)
    for r in records:
        if r['source_annotations_cap']!=cap_por_imagen[r['image_id']]:
            raise ValueError('Las cajas fuente difieren de RAW')
        v.imagen_fuente(r['image_id'])
    archivo=v.ROOT/'datasets/publicos_calidad_botellas/raw/roboflow_bottle_v4/dataset.zip'
    if sha(archivo)!='1ee2254353fd3323c03154e878c31924dbafa03ae0df751763b6e85a43f7dc70':
        raise ValueError('ZIP fuente modificado')
    restricciones=leer(v.ROOT/'output/auditoria_roboflow_v4_v002_001/restricciones_202_grupos.json')
    if sha(v.ROOT/restricciones['origen'])!=restricciones['sha256']:
        raise ValueError('Cambió la restricción de los 202 grupos')
    samples,boxes,report=analizar(records,historia,v.CONFLICTOS)
    # Todas las verificaciones preceden la publicación de la copia candidata.
    cambios=[p for p,h in {**protegidos,**adicionales}.items() if not (v.ROOT/p).is_file() or sha(v.ROOT/p)!=h]
    if cambios:
        raise ValueError('Archivos protegidos modificados: '+str(cambios))
    if v.generaciones()!=historia:
        raise RuntimeError('Se guardaron decisiones nuevas durante la consolidación; repetir con salida nueva')
    salida.mkdir(parents=True);dataset.mkdir(parents=True)
    jsonl(dataset/'samples.jsonl',samples);jsonl(dataset/'annotations.jsonl',boxes)
    nuevo(dataset/'adjudicaciones_ultimas.json',list(v.ultimas(historia).values()))
    nuevo(dataset/'historial_completo.json',historia)
    nuevo(dataset/'exclusiones.json',[b for b in boxes if b['excluded_from_positive_labels']])
    nuevo(dataset/'incidencias.json',report['incidencias'])
    nuevo(dataset/'particiones.json',dict(particiones=report['particiones'],grupos_indivisibles=14,cruces=0,restricciones_202=restricciones,approved=False,independencia='NO_CERTIFICADA'))
    nuevo(salida/'resumen.json',report)
    (salida/'INFORME.md').write_text(informe(report),encoding='utf-8')
    nuevo(salida/'trazabilidad.json',dict(fecha_utc=datetime.now(timezone.utc).isoformat(),historial_archivos=historial_archivos,
        fuente_coco_sha256=v.COCO_SHA,fuente_candidato_sha256=sha(v.BASE/'dataset_candidato.jsonl'),
        dataset=dataset.relative_to(v.ROOT).as_posix(),historial_original_modificado=False,revision_global_congelada=len(historia),
        referencia_propia='CONSERVADA_POR_SEPARADO_NO_INCLUIDA',licencia_exportacion='CC BY 4.0 registrada; procedencia individual con alertas previas sin nueva certificación'))
    nuevo(salida/'verificacion_integridad.json',dict(archivos_linea_base_verificados=len(protegidos),archivos_adicionales_verificados=len(adicionales),
        alterados=cambios,imagenes_verificadas=len(records),generaciones_verificadas=len(historia),cajas_RAW_conservadas=915,
        inferencias=0,entrenamientos=0))
    files={p.name:sha(p) for p in dataset.iterdir() if p.is_file()}
    nuevo(dataset/'manifest.json',dict(version='TAPA_v003_candidato_001',formato='REFERENCIAS_INMUTABLES_NO_EXPORT_ENTRENAMIENTO',
        entrenamiento_autorizado=False,estado=report['estado'],imagenes=len(samples),cajas=dict(report['cajas_finales']),sha256=files,
        fuente_coco_sha256=v.COCO_SHA,revision_global=len(historia),fuente_candidato_sha256=sha(v.BASE/'dataset_candidato.jsonl')))
    nuevo(salida/'manifest.json',dict(dataset_manifest=dataset.relative_to(v.ROOT).as_posix()+'/manifest.json',dataset_manifest_sha256=sha(dataset/'manifest.json'),
        sha256={p.name:sha(p) for p in salida.iterdir() if p.is_file()},estado=report['estado']))
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--salida',type=Path,required=True);p.add_argument('--dataset',type=Path,required=True)
    a=p.parse_args();ejecutar(a.salida,a.dataset)
