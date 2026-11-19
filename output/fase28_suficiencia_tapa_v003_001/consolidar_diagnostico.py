"""Publica diagnóstico y propuesta sin corregir ni crear etiquetas humanas."""
import hashlib
import html
import json
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def write(name,data):
    with (OUT/name).open('x',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False,indent=2)

rows=read(OUT/'inspeccion_262.json');byid={r['image_id']:r for r in rows}
history=read(OUT/'historial_congelado.json');latest={d['image_id']:d for d in history}
source=[json.loads(s) for s in (ROOT/'output/preparacion_tapa_fase25_v002_001/dataset_candidato.jsonl').read_text(encoding='utf-8').splitlines()]
groups=read(OUT/'resumen_tecnico.json')['grupos']
assert len(rows)==262 and len(history)==11

# Observaciones técnicas de las 22 hojas y ampliaciones; no son cajas ni
# adjudicaciones humanas y no modifican los datos de entrenamiento.
missing={
 5:'Tapas verdes visibles en botellas del fondo sin cajas específicas.',
 24:'Varias tapas verdes de fondo sin cajas; no existe revisión humana guardada.',
 38:'Tapa de primer plano y tapas de fondo sin cajas TAPA tras reclasificar 123 como ENVASE.',
 42:'Tapa verde visible en botella izquierda sin caja específica; región derecha adjudicada NO EVALUABLE.',
 63:'Tapa verde central sin caja; las otras dos sí tienen cajas.',
 87:'Tapa azul en botella tumbada; cero cajas cap fuente. Marca COLOURBOX visible.',
 89:'Tapa verde sobre botella en cinta izquierda sin caja.',
 90:'Variante de imagen 87, tapa azul sin caja; marca COLOURBOX.',
 95:'Tapa verde izquierda sin caja específica; boca derecha adjudicada NO EVALUABLE.',
 96:'Tapa verde izquierda sin caja.',
 115:'Tapa verde en botella superior de la cinta izquierda sin caja.',
 123:'Segunda botella inclinada tiene tapa azul sin caja.',
 131:'Tapa azul visible; ninguna caja cap. Marca Dreamstime visible.',
 158:'Tapa de botella del extremo derecho sin caja específica.',
 163:'Tapas azules laterales de botellas de fondo sin cajas específicas.',
 165:'Nota humana confirma tapa azul; la única caja fue reclasificada ENVASE y no se agregó TAPA.',
 172:'Tapa verde sobre botella en cinta izquierda sin caja.',
 173:'Tapa verde sobre botella en cinta izquierda sin caja.',
 184:'Tapa verde izquierda sin caja; par automático con 160, que sí tiene una caja.',
 192:'Tapa verde izquierda sin caja.',
 198:'Tapa verde izquierda sin caja.',
 203:'Tapa verde izquierda sin caja.',
 205:'Tapas blancas visibles sin ninguna caja cap.',
 209:'Tapa verde izquierda sin caja.',
 221:'Tapas azules visibles en la línea; cero cajas cap fuente.',
 225:'Tapa blanca de botella derecha sin caja.',
 229:'Tapa azul del envase delantero sin caja; requiere revisar el límite superior del encuadre.',
 235:'Tapa de segunda botella desde la izquierda sin caja.',
 245:'Seis botellas con tapas visibles y una sola caja cap registrada.',
 256:'Tapa verde izquierda sin caja.',
 257:'Cinco botellas con tapas verdes, algunas parciales, y solo dos cajas cap.'}
suspects={62:'Región de tapa fuera del recorte: no convertir en negativo.',
          73:'Desenfoque visible; caja azul plausible pero precisión de borde limitada.',
          202:'Foto recortada al cuerpo/etiqueta: tapa fuera de campo; no es un negativo confirmado.',
          208:'Tapas pequeñas, desenfoque/sobreexposición al fondo; alcance de evaluabilidad sin confirmar.'}
rights={83:'Picxy',84:'Picxy',117:'Adobe Stock',241:'Adobe Stock',131:'Dreamstime',170:'Dreamstime',
        41:'Alamy',91:'Alamy',70:'Shutterstock',165:'Shutterstock',113:'Getty Images',145:'Getty Images',87:'COLOURBOX',90:'COLOURBOX'}
observations=[dict(image_id=i,group_id=byid[i]['group_id'],tipo='OMISION_VISUAL_A_CORREGIR',
    observacion=note,autor_tipo='ASISTENTE_AUDITOR_NO_ADJUDICADOR',es_etiqueta_humana=False) for i,note in sorted(missing.items())]
observations += [dict(image_id=i,group_id=byid[i]['group_id'],tipo='DUDOSA_O_FUERA_DE_CAMPO',observacion=note,
                     es_etiqueta_humana=False) for i,note in sorted(suspects.items())]
write('observaciones_visuales.json',observations)
write('alertas_procedencia_visibles.json',[dict(image_id=i,marca_observada=n,
    autorizacion_individual='NO_CONFIRMADA',conclusion_legal=None) for i,n in sorted(rights.items())])

core_groups=['v4g05','v4g07','v4g09','v4g12','v4g13','v4g14']
assignment={'v4g05':'train','v4g07':'train','v4g09':'train','v4g12':'train','v4g13':'validation','v4g14':'test'}
ids={i for g in core_groups for i in groups[g]}
assert len(ids)==12 and not ids.intersection(missing) and not ids.intersection(rights)
core=[]
for s in source:
    if s['image_id'] not in ids:continue
    assert len(s['source_annotations_cap'])==1
    core.append(dict(image_id=s['image_id'],source_image=s['source_image'],sha256=s['sha256'],
                     group_id=s['group_id'],proposed_partition=assignment[s['group_id']],
                     source_annotations_cap=s['source_annotations_cap'],training_approved=False,
                     partition_approved=False,negative_confirmed=None,
                     visual_screening='UNA_TAPA_COMPATIBLE_SIN_OMISION_EVIDENTE_EN_INSPECCION',
                     human_adjudication=None,origin_independence='NO_CERTIFICADA',
                     scope='PRUEBA_DE_CANALIZACION_PROPUESTA_NO_EVALUACION_DEFENDIBLE_DE_VIDEO'))
with (OUT/'subconjunto_minimo_candidato.jsonl').open('x',encoding='utf-8') as f:
    for r in core:f.write(json.dumps(r,ensure_ascii=False)+'\n')
write('plan_minimo_por_grupos.json',dict(imagenes=12,cajas_TAPA_fuente=12,grupos_completos=6,
    grupos=core_groups,asignacion_propuesta_nueva=assignment,particiones=dict(Counter(r['proposed_partition'] for r in core)),
    grupos_por_particion={'train':4,'validation':1,'test':1},approved=False,
    autoriza_entrenamiento=False,candidatos_para_evaluacion_defendible_video=0,
    motivo='Seis motivos visuales con dos variantes cada uno; validación y prueba tendrían un solo motivo cada una, sin cobertura de tapas pequeñas ni escenas de producción.',
    trabajo_minimo='Confirmar seis pares y su procedencia; conservar etiquetas originales si se confirman. No reanotar 262 imágenes.',
    candidatos_con_fondo_blanco='Las alertas de brillo/global Laplaciano no equivalen automáticamente a exposición o foco defectuosos de la tapa.'))

reconciliation={
 'imagen_9':dict(estado='RESUELTO',revision=11,exhaustividad=latest[9]['exhaustividad'],accion='Se reconoce la decisión nueva; no se cambia v003 congelado en revisión 10.'),
 'imagen_24':dict(estado='NO_RECUPERADA',version_guardada=None,accion='No crear una decisión. El cliente no tiene almacenamiento persistente de borradores.'),
 'imagen_38':dict(estado='PERSISTE_INCONSISTENCIA',revision=latest[38]['revision_global'],nuevas_cajas=len(latest[38]['nuevas_cajas']),exhaustividad=latest[38]['exhaustividad']),
 'imagen_165':dict(estado='PERSISTE_INCONSISTENCIA',revision=latest[165]['revision_global'],nuevas_cajas=len(latest[165]['nuevas_cajas']),exhaustividad=latest[165]['exhaustividad']),
 'imagen_60':dict(estado='ALCANCE_PENDIENTE',revision=latest[60]['revision_global'],detalle='203=TAPA/TOTAL y 204=NO_EVALUABLE/TOTAL, con NO_EVALUABLE global. El positivo local se conserva; no aprobar alcance global automáticamente.')}
write('reconciliacion_actual.json',reconciliation)
decisions=[]
for p in (ROOT/'output').rglob('decision.json'):
    d=read(p)
    decisions.append(dict(path=p.relative_to(ROOT).as_posix(),image_id=d.get('image_id'),sha256=sha(p)))
write('busqueda_revision_24.json',dict(registros_decision_en_output=decisions,registros_imagen24=[r for r in decisions if r['image_id']==24],
    almacenamiento_borradores_cliente='No hay localStorage, sessionStorage ni IndexedDB en el anotador v4; cambios sin guardar viven solo en memoria.',
    alcance='Registros y representaciones locales en el proyecto; no se inspeccionaron carpetas personales ajenas al proyecto.'))

technical=read(OUT/'resumen_tecnico.json')
distribution={}
for partition in ('train','validation','test','PENDIENTE'):
    rr=[r for r in rows if r['proposed_partition']==partition]
    distribution[partition]=dict(imagenes=len(rr),TAPA=sum(r['effective_counts'].get('TAPA',0) for r in rr),
        ENVASE=sum(r['effective_counts'].get('ENVASE',0) for r in rr),NO_EVALUABLE=sum(r['effective_counts'].get('NO_EVALUABLE',0) for r in rr))
result=dict(estado='NO_PREPARADO_PARA_ENTRENAMIENTO_CON_EVALUACION_INDEPENDIENTE',imagenes_integras=262,
    cajas_fuente_geometricamente_validas=180,TAPA_candidatas=173,TAPA_con_nueva_adjudicacion_humana=1,
    ENVASE_adjudicados=3,NO_EVALUABLE=4,cajas_cap_fuente_no_mantenidas_como_TAPA=[31,123,134,204,324,567,773],
    nuevas_cajas_humanas=0,imagenes_con_omisiones_en_criba=len(missing),ids_omisiones=sorted(missing),
    candidatos_visualmente_compatibles_para_revision_reducida=12,cajas_en_ese_nucleo=12,grupos_en_nucleo=6,
    imagenes_aprobadas_para_entrenamiento=0,imagenes_restantes_no_incluidas_en_nucleo=250,
    particiones_actuales=distribution,revision_actual=11,revision_v003_congelada=10,
    hoja_contactos_revisadas=22,imagenes_incluidas_en_criba_visual=262,
    limite_visual='Criba a escala de hoja y ampliaciones dirigidas; no certificación exhaustiva de cada objeto pequeño por revisión humana.',
    clases_disponibles={'TAPA':'CANDIDATA_NO_VALIDADA','ENVASE':'3 RECLASIFICACIONES, NO DATASET EXHAUSTIVO',
                        'TAPA_DEFECTUOSA':'NO_HABILITADA','TAPA_AUSENTE':'SIN_CONTEXTO_POST_TAPADO_CONFIRMADO',
                        'RAYADURA':'NO_DISPONIBLE','DEFORMACION':'NO_DISPONIBLE'},
    recomendacion='Usar núcleo de seis pares para reducir verificación, no como validación del detector en video. Mantener fuera los grupos conflictivos. No autorizar entrenamiento basado en evaluación independiente aún.',
    solicitar_nuevas_capturas_ahora=False,entrenamientos=0,inferencias=0)
write('diagnostico_final.json',result)

cards=''.join(f'<article id="imagen-{r["image_id"]}"><h2>Imagen {r["image_id"]} · {r["group_id"]}</h2><p>{html.escape(r["observacion"])}</p><a href="http://127.0.0.1:8010/demo/calidad/tapa-v4/#imagen-{r["image_id"]}">Revisar en la herramienta existente</a><p><img loading="lazy" src="imagenes/{r["image_id"]:03d}.jpg" alt="Cajas existentes de imagen {r["image_id"]}"></p></article>' for r in observations)
page='<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Auditoría final TAPA v003</title><style>body{font:16px system-ui;background:#101d2d;color:#eef4fc;margin:24px;max-width:1200px}a{color:#9bdcff}article{padding:18px;background:#203147;border-radius:10px;margin:20px 0}img{max-width:100%;height:auto}</style><h1>TAPA v003 · Suficiencia y revisión mínima</h1><p>Observaciones técnicas, no etiquetas humanas nuevas. No se entrenó ni infirió. Las imágenes sin alertas no quedan certificadas automáticamente.</p><a href="INFORME.md">Informe</a><h2>Núcleo propuesto: seis pares, doce imágenes</h2>'
for g in core_groups:
    page+=f'<article><h3>{g} · propuesta {assignment[g]}</h3>'+''.join(f'<img loading="lazy" style="max-width:48%" src="imagenes/{i:03d}.jpg" alt="Candidato {i}">' for i in groups[g])+'</article>'
page+='<h2>Omisiones y zonas a revisar</h2>'+cards+'<h2>Criba sistemática de las 262 imágenes</h2>'+''.join(f'<details><summary>Hoja {n}</summary><img loading="lazy" src="contactos/hoja_{n:02d}.jpg" alt="Hoja de inspección {n}"></details>' for n in range(1,23))+'</html>'
with (OUT/'index.html').open('x',encoding='utf-8') as f:f.write(page)

table='\n'.join(f'| {k} | {v["imagenes"]} | {v["TAPA"]} | {v["ENVASE"]} | {v["NO_EVALUABLE"]} |' for k,v in distribution.items())
report=f'''# Fase 2.8 · Auditoría de suficiencia TAPA v003

**Estado: NO PREPARADO para entrenamiento con una evaluación independiente defendible.** Se encontró un núcleo visual de bajo costo de revisión, pero no evidencia suficiente para afirmar que permita evaluar detección en video. No se entrenó ni se ejecutaron inferencias.

## Qué cambió desde Fase 2.7

- Hay 11 versiones reales. La nueva versión 11 cambia imagen **9 a COMPLETA**; ese bloqueo está resuelto. El v003 anterior permanece congelado en versión 10, sin sobrescribirlo.
- **24:** no existe decisión guardada entre los registros encontrados. Se revisaron los registros locales `decision.json` y el mecanismo de guardado; el cliente no conserva borradores en almacenamiento persistente. No se recuperó una decisión ni se inventó una. Los archivos derivados que contienen la imagen no son adjudicaciones.
- **38 y 165:** siguen COMPLETA con notas que afirman tapas visibles, cero cajas nuevas y sin caja TAPA después de reclasificar sus únicas cajas como ENVASE. Son omisiones pendientes, no decisiones que pueda completar el sistema.
- **60:** 203 confirma una tapa y 204 excluye una etiqueta; el estado global NO EVALUABLE no aclara si afecta solo a la etiqueta o toda la imagen. Se conserva el positivo local y el estado global, sin decidir por la revisora.

Estas últimas imágenes pueden quedar fuera de una primera selección: corregir todo el dataset no es una condición para estudiar un subconjunto distinto. No hace falta repetir los siete cambios de clase.

## Auditoría de las 262 imágenes

Se reutilizaron `inspect_image` y las huellas del auditor existente, y se comprobaron las 262 imágenes contra SHA-256, dimensiones y decodificación. Todas coinciden. Hay 262 hashes únicos y 180 cajas fuente geométricamente válidas. La geometría no valida semántica.

Se compararon 34.191 pares de imágenes. Se reprodujeron los 60 pares de similitud estricta, sin cruces entre los 14 grupos. Hay dos discrepancias de cajas TAPA: **24/38** y **160/184**. Son alertas verificables, no predicciones ni propuestas de coordenadas. El segundo caso muestra una tapa verde anotada en 160 y sin caja en la vista muy similar 184.

Una búsqueda más amplia produjo la alerta entre 248 y 259. Su inspección muestra fotos de botellas/productos distintos; la semejanza de silueta no justifica unir sus grupos. Tampoco se interpretan dos marcas iguales como una misma sesión. Se mantienen los grupos previos.

Se inspeccionaron 22 hojas que incluyen las 262 imágenes y se ampliaron casos dirigidos. Se encontraron **{len(missing)} imágenes con omisiones visuales**, registradas individualmente en `observaciones_visuales.json`, con galería para comprobarlas. Ejemplos: 63 tiene una tapa verde central sin caja; 131 tiene tapa y ninguna caja cap; 123 tiene dos botellas y una sola tapa anotada; 245 muestra seis botellas con tapas y una sola caja; 163 deja tapas laterales sin cajas. Este número es un mínimo de incidencias de la criba, no una certificación de exhaustividad del resto ni un recuento de tapas faltantes.

La secuencia de la cinta pequeña contiene tapas sueltas/piezas verdes y objetos parcialmente visibles; su alcance requiere protocolo. No se convierten bocas, anillos o piezas ambiguas en tapas. Imágenes recortadas al cuerpo como 62 y 202 no son negativos confirmados. Las 114 imágenes de v4g02 conservan cero TAPA positivas tras adjudicación; no interesa revisar manualmente esas 114 antes de aprovechar positivos de otros grupos y no se incorporan automáticamente como negativos.

El detector técnico marcó nueve posibles desenfoques, nueve fondos muy claros y un fondo muy oscuro. Son señales para priorizar. En fotos de producto, un fondo blanco y un Laplaciano global bajo no prueban que la tapa esté desenfocada o mal expuesta; no se rechazaron automáticamente esas imágenes.

## Cajas y clases

- **173 TAPA candidatas**, una con nueva adjudicación humana (203) y 172 conservadas de fuente. No se presentan como 173 cajas humanas nuevamente validadas.
- **3 ENVASE**: 31, 123 y 567; sirven como correcciones de trazabilidad, no como dataset exhaustivo de envases.
- **4 NO EVALUABLE**: 134, 204, 324 y 773, conservadas fuera de positivos. TOTAL de visibilidad no cambia la clase excluida: en 204 y 773 la nota describe etiqueta/boca, no una tapa oculta.
- Cero cajas nuevas humanas y ninguna corrección automática de coordenadas.
- Las decisiones humanas identifican **cinco regiones fuente incompatibles con TAPA**: 31, 123 y 567 son envases; 204 es una etiqueta; 773 es boca/cuello. En 134 y 324 persiste duda visual. Se distinguen esos cinco errores de clase de los dos casos ambiguos; los siete dejan de ser positivos TAPA.
- El núcleo técnico descrito abajo tiene **12 cajas TAPA visualmente compatibles** y geométricamente válidas, sin anotaciones nuevas; eso no acredita una adjudicación humana ni prueba la exhaustividad de objetos pequeños fuera del alcance observado.
- TAPA_DEFECTUOSA, TAPA_AUSENTE como defecto, RAYADURA y DEFORMACION no se habilitan. `no-cap` no prueba defecto posterior al tapado.

## Particiones vigentes: conservadas, no aprobadas

| Partición actual | Imágenes | TAPA | ENVASE | NO EVALUABLE |
|---|---:|---:|---:|---:|
{table}

Se verificó por hash la restricción de los 202 grupos anteriores. La auditoría no añade imágenes ni desplaza ninguna entre particiones históricas. Los 14 componentes son grupos conservadores de archivo/similitud, no 14 sesiones certificadas. v4g01 y v4g04 mezclan imágenes de web/producto; v4g03 mezcla al menos dos entornos de línea visibles. Ausencia de duplicados exactos no prueba independencia de fuente.

## Núcleo mínimo de bajo costo encontrado

**12 imágenes, 12 cajas, 6 grupos completos:** v4g05 (11,75), v4g07 (40,259), v4g09 (65,88), v4g12 (102,204), v4g13 (126,231), v4g14 (142,171). Cada par muestra una variante de un motivo visual, una tapa anotada y ninguna omisión evidente en esta inspección. Las cajas tienen lado menor de aproximadamente 31 a 89 píxeles a resolución 640. No hay ejemplos de tapas pequeñas de línea ni multienvase en este núcleo.

La propuesta nueva, separada de las particiones históricas, asigna cuatro grupos completos a entrenamiento (**8 imágenes / 8 tapas**), uno a validación (**2 / 2**) y uno a prueba (**2 / 2**). Se entrega en `subconjunto_minimo_candidato.jsonl` y `plan_minimo_por_grupos.json`, con aprobación deshabilitada. No incluye las referencias propias con derechos pendientes, ni los grupos de imágenes conflictivas.

Esto **no es un mínimo estadístico universal ni un conjunto suficiente para evaluar un detector de video**. Solo hay seis motivos visuales, y validación/prueba tendrían un motivo cada una con dos variantes correlacionadas. Puede reducir a seis pares la verificación inicial del recorrido de datos, pero una ejecución sobre ese núcleo mediría principalmente memorización y transferencia entre fotos de producto, no generalización a una línea. Ninguna imagen queda aprobada para entrenar en este informe.

## Procedencia y bloqueos

La exportación v4 tiene licencia CC BY 4.0 registrada y verificada en la auditoría previa; se conserva esa evidencia. La criba encontró marcas de terceros, incluidas Picxy, Adobe Stock, Dreamstime, Alamy, Shutterstock, Getty Images y COLOURBOX. Son alertas concretas de procedencia individual, no una conclusión legal ni prueba de que todo el dataset carezca de derechos. No se inventan enlaces o autorizaciones.

El núcleo evita las imágenes con esas marcas observadas, pero **no ver una marca no acredita derechos ni independencia**. Falta documentar el origen de los seis motivos para certificar separación independiente. Además, un test de un solo motivo es estadísticamente insuficiente para sostener precisión/recall generalizables. La cobertura no puede inferirse de hashes, clases o semejanza.

## Camino más corto recomendado

1. Mantener en cuarentena los grupos conflictivos y el grupo de 114 imágenes sin TAPA positiva, sin borrarlos ni dedicarles una nueva anotación masiva.
2. Utilizar la galería de los **seis pares** para confirmar conjuntamente cajas existentes, alcance de TAPA y procedencia. No hace falta dibujar de nuevo cajas que ya sean correctas ni revisar manualmente las 262 imágenes.
3. Si solo se desea verificar la canalización, acordar explícitamente ese alcance restringido del núcleo; no llamarlo evaluación independiente del detector de video. Este informe no ejecuta ni autoriza entrenamiento.
4. Para un entrenamiento respaldado por evaluación del objetivo real, cerrar exhaustividad y procedencia de grupos de escenas relevantes adicionales antes de reservar validación/prueba. No se fija un número mágico de imágenes: deben existir suficientes escenas realmente distintas y cobertura de tamaños/contextos. Los datos actuales ofrecen escenas potenciales, pero no están aún certificadas. Priorizar los grupos existentes antes de solicitar nuevas capturas.

La imagen 9 está resuelta. 24,38,165 y60 siguen pendientes para el cierre global, pero no bloquean por sí mismas estudiar el núcleo que las excluye. El bloqueo restante de ese núcleo es su alcance estadístico/de dominio y la independencia/procedencia, no aquellas cuatro imágenes. Se mantienen NO EVALUABLE y desconocidos; no se inventan negativos ni métricas.
'''
with (OUT/'INFORME.md').open('x',encoding='utf-8') as f:f.write(report)
print(json.dumps(result,ensure_ascii=False))
