# Roboflow v4 adquirido y auditado · Calidad v002

18/11/2026 · America/La_Paz. Esta entrega sustituye el estado de adquisición pendiente del informe `_001`, que se conserva como historial. No se entrenó, ejecutó inferencia ni alteró código operativo, referencias humanas o evaluaciones anteriores.

## 1. Adquisición e identidad verificadas

Archivo proporcionado por el usuario: `pruebas_ia/Bottle Defect Detection.v4i.coco.zip`, 22.456.325 bytes. SHA-256:

```text
1ee2254353fd3323c03154e878c31924dbafa03ae0df751763b6e85a43f7dc70
```

README.dataset.txt acredita proyecto Spark Intelligence/bottle-defect-detection y CC BY 4.0. README.roboflow.txt identifica v4, 262 imágenes y COCO; fecha declarada de exportación: 06/12/2023 20:02 GMT. La versión de dataset publicada es 13/07/2023. No confundir fecha de exportación con sesión física de captura. La [publicación oficial](https://universe.roboflow.com/spark-intelligence-scqhh/bottle-defect-detection/dataset/4) coincide en versión, licencia y 262 imágenes; su split original es 100 % train.

El ZIP y extracción RAW quedan en `datasets/publicos_calidad_botellas/raw/roboflow_bottle_v4/`. Se validaron 266 miembros, 22.388.595 bytes descomprimidos, rutas, tamaños y ausencia de enlaces/traversal antes de extraer. No se ejecutó contenido del ZIP ni se modificó el original del usuario. ACQUISITION.json conserva hash y evidencia; no se cambió el registro histórico de fuentes que aún decía autenticación requerida.

Licencia confirmada a nivel de publicación/README: CC BY 4.0, atribución a Spark Intelligence y enlace a la licencia, indicando las derivaciones. No acredita por sí sola cada procedencia individual de terceros; las alertas específicas se conservan aparte y no se declara infracción sin evidencia.

## 2. Contenido real y calidad geométrica

| Clase original | Cajas RAW | Imágenes con esa clase | Interpretación admisible |
|---|---:|---:|---|
| cap | 180 | 114 | Objeto tapa visible; no certifica colocación correcta ni ausencia de daño |
| no-cap | 146 | 144 | Cuello/hueco sin tapa según fuente; no una tapa física ni defecto industrial confirmado |
| crumbled | 120 | 120 | Caja de envase arrugado/aplastado según fuente; no parche de abolladura |
| not-crumbled | 203 | 140 | Caja de envase sin arrugado según fuente; no conformidad global |
| label | 266 | 228 | Etiqueta del envase; no clase de rayadura |
| Total | **915** | **262 únicas** | Una imagen puede contener varias clases/objetos |

La supercategoría Defects-in-water-bottles no tiene instancias. Resoluciones: 107 imágenes 640×640, 114 imágenes 1080×1920 y 41 imágenes 1280×720. Las 262 imágenes se decodifican y sus dimensiones coinciden con COCO.

El importador existente rechazó el RAW por **seis cajas fuera de límites**, sin crear una importación parcial silenciosa. Son tres label y tres not-crumbled, en seis imágenes, con exceso de borde de 0,25–0,5 px. Cajas completas en cajas_invalidas.json. No se recortaron coordenadas ni se relajó el validador.

Se creó una derivación explícita de geometría válida en `datasets/publicos_calidad_botellas/staging/roboflow_bottle_v4_geometria_valida_001`: excluye los seis frames completos, no etiquetas aisladas, para evitar convertir objetos omitidos en fondo. Conserva 256 imágenes y 874 cajas, todas con coordenadas originales. El RAW mantiene sus 262/915.

El importador público existente completó `imports/roboflow_bottle_v4_001` sobre esa derivación: 256 imágenes, cero duplicados exactos externos, fuente/clases preservadas y training_eligible=false. DERIVATION_POINTER.json hace explícito que es un subconjunto de la exportación completa, no otra versión oficial. Los valores de RAYADURA/DEFORMACION/TAPA_DEFECTUOSA siguen null porque el esquema histórico del importador es presencia de defectos: esto no elimina las cajas cap/no-cap/body conservadas en source_occurrences.

### No excluir trabajo útil por un error ajeno a la tarea

Las **180 cajas cap son geométricamente válidas**, incluidas las de los seis frames con problemas en otras clases. Para una futura tarea TAPA exclusiva pueden reutilizarse sin excluir automáticamente esos frames por errores de label/not-crumbled. Se guardaron sus coordenadas originales en candidatas_cap_originales.json, sin crear etiquetas nuevas ni aprobar exhaustividad.

En el subconjunto genérico de 256 imágenes quedan: cap 166, no-cap 146, crumbled 120, not-crumbled 191, label 251. La retirada de 41 cajas al excluir seis imágenes es una cuarentena por imagen, no 41 cajas erróneas. La diferencia es importante para no perder innecesariamente las 14 cajas cap válidas de esos frames.

## 3. Geometría, dominio y semántica

Se inspeccionaron ejemplos de cada clase, disponibles en clases_y_cajas_v4.jpg y en la galería de las 262 imágenes. Los previews conservan proporción y las cajas son las de la fuente, no predicciones. No se declara una adjudicación humana nueva de cada caja.

- cap delimita tapas completas en ejemplos de botellas individuales y tapas pequeñas en escenas industriales. Hay blancos, azules y otros contextos, no solo el fondo negro de v26. De sus 180 cajas, 31 tienen lado mínimo <16 px al proyectar a entrada 640; rango 8,07–144,10 px, mediana 44,05 px. Las pequeñas no se descartan automáticamente.
- no-cap delimita la boca/cuello o hueco. No se convierte a TAPA. Tampoco la presencia de una etiqueta no-cap acredita obligatoriedad de tapa tras una estación confirmada.
- crumbled y not-crumbled delimitan envases/cuerpos. Pueden preparar una clase ENVASE con protocolo de extensión explícito, pero no se mezclan directamente con las cajas de daño localizado dent de Mendeley. Hay 323 cajas de cuerpo candidatas; tres not-crumbled tienen el error geométrico indicado, por lo que solo 320 están dentro de límites en RAW.
- crumbled incluye botellas aplastadas y reutilizadas: una deformación visible no demuestra defecto de fabricación. not-crumbled tampoco acredita ausencia de rayadura, daño de tapa u otros defectos.
- label es región de etiqueta, no damage/rasguño.

V4 **no distingue tapa rota, floja o mal colocada como clases específicas**. cap significa presencia, no Good Cap; por tanto no aporta automáticamente negativos de TAPA_DEFECTUOSA. Broken Cap/Loose Cap/Good Cap siguen procediendo de v26, donde algunas cajas Loose/Ring delimitan hueco/anillo en vez de tapa completa.

## 4. Procedencia individual y exclusiones

La publicación y el ZIP acreditan la licencia declarada del dataset, pero los nombres/marcas muestran mezcla de contextos y posibles terceros. Hay 12 imágenes cuyos nombres sugieren stock/web (por ejemplo COLOURBOX o nombres de imágenes redistribuidas). Se registran como alerta de procedencia, no como infracción demostrada ni motivo para descartar todo v4. Algunas escenas contienen marcas de video; no se presume titularidad individual sin revisar.

registro_exclusiones_y_pendientes.json distingue:

1. Seis frames en cuarentena geométrica para el import genérico; ningún RAW borrado.
2. Doce alertas nominales de terceros para revisar antes de entrenamiento.
3. Pendientes semánticos por tarea: no-cap, label, crumbled y not-crumbled no equivalen automáticamente a los objetivos finales.
4. Otros grupos de imágenes web sin sesión conocida quedan en revisión de fuente, no se usan para inflar independencia.

La prueba de derechos pendiente de las 25 imágenes adjudicadas no se resuelve con la licencia de v4. Sus 244 cajas, autores, decisiones e historial permanecen intactos y separados.

## 5. Duplicados, similitud y restricción de los 202 grupos

Los 262 SHA-256 son distintos entre sí y no coinciden con ninguno de los 8.502 registros anteriores. Inventario canónico total: **8.764 imágenes únicas por SHA**, de las cuales 8.739 corresponden a los tres datasets públicos y 25 a la referencia humana con derechos pendientes. El total de importaciones públicas de geometría válida es menor: 8.733, porque seis imágenes v4 están en cuarentena genérica. Ninguna de estas cifras implica que todas sean entrenables para todas las clases.

Se reutilizó el algoritmo de semejanza existente: pHash ≤2, dHash ≤4, diferencia de color/gris ≤0,025, fracción de píxeles cambiados ≤0,04 y aspecto ≤0,03. Se analizaron únicamente relaciones nuevas v4–v4 y v4–anteriores; no se rehízo el análisis previo anterior–anterior.

- 60 parejas candidatas de semejanza dentro de v4.
- Cero parejas aceptadas por ese criterio entre v4 y fuentes anteriores. No demuestra ausencia absoluta de parentesco ni reemplaza trazabilidad física.
- Al unir variantes de nombre previo a .rf., secuencias numéricas y fechas nominales VLC, resultan **14 componentes v4 provisionales**.
- Los **202 componentes anteriores permanecen indivisibles** y no se modificaron sus archivos/particiones. Sumando v4 son 216 componentes públicos de restricción; con el grupo humano separado, 217.

Los proxies de nombre/fecha VLC representan relación conservadora de archivos, no fecha de captura certificada. No se adjudicaron session_id físicos. Si la revisión encuentra parentesco adicional deben fusionarse componentes, nunca dividir variantes para mejorar un resultado.

## 6. Combinación fijada por tareas y propuesta de particiones

La política de combinación y exclusiones está definida en propuesta_combinacion_y_particiones.json. **La asignación es propuesta y no está aprobada para entrenamiento**: faltan revisión de grupos/procedencia y protocolo de mapeo. No se presenta una partición final falsa solo porque el ZIP ya llegó.

| Tarea | Datos reutilizables | Límite |
|---|---|---|
| TAPA física | 180 cajas cap / 114 imágenes v4; hasta 272 Good/Broken v26 candidatas | Revisar extensión, parciales y exhaustividad; Loose/Ring/No Cap no se renombran como tapa completa |
| ENVASE | 323 cajas crumbled/not-crumbled candidatas (320 dentro de límites) y baseline COCO | Aprobar convención de cuerpo/cuello; preservar derechos pendientes de las 101 cajas humanas |
| TAPA_DEFECTUOSA | V26 Broken/Loose: 178 instancias en 171 imágenes | V4 no aporta subtipos de defecto; cap no es negativo confirmado; No Cap necesita contexto |
| DEFORMACION | Mendeley dent: 8.029 cajas; v4 crumbled: 120 cajas de objeto | No juntar lesión localizada y caja completa como el mismo objetivo detector; no inferir causa industrial |
| RAYADURA/SCUFF | Mendeley scuff: 10.893 cajas | Aprobar alcance de rozadura/abrasión; v4 label no aporta rayaduras |

No se generó un YOLO de cinco clases rellenando desconocidos como negativos. La tarea o cabeza de pérdida debe respetar qué se anotó en cada fuente. Para ENVASE/TAPA, las clases fuente y su alcance se mantienen hasta aprobar el mapeo; para superficie se conserva taxonomía nativa/gravedad.

### Reparto candidato sin dividir grupos

Se conserva la propuesta anterior de 5.816/1.271/1.390 imágenes públicas train/validation/test, con 202 grupos. Para estudiar v4 sin mezclar variantes:

| Partición candidata | Grupos v4 | Imágenes RAW | Imágenes tras cuarentena genérica |
|---|---|---:|---:|
| Train | v4g01 + v4g02 | 173 | 171 |
| Validation | v4g04 | 25 | 22 |
| Test | v4g03 | 41 | 41 |
| Revisión de otras fuentes | restantes diez grupos | 23 | 22 |

Los seis frames fuera de límites quedan aparte; uno pertenece a esos 23 de revisión. En total hay 234 v4 en el reparto candidato, 22 en revisión de fuente y seis en cuarentena. No hay un grupo con imágenes aprendidas en dos particiones; cuarentena nunca es otra partición de aprendizaje. Los 25 humanos continúan separados por derechos pendientes.

Esta es una propuesta de prueba por contexto, **no definitiva ni suficiente para todas las clases**. V4 validation no tiene no-cap ni crumbled, y test no tiene crumbled. No se calcularían recall/F1 de esas clases en un split sin positivos. Se debe ajustar por tareas al revisar los grupos, no al observar resultados de modelos.

V4 concentra 112/120 crumbled en un solo componente de 114 imágenes; los otros ocho están en pequeños grupos con alertas de origen. No existe evidencia para evaluar un clasificador de deformación v4 con positivos independientes en las tres particiones sin revisar/aportar fuentes. V26 conserva el problema previo de validation Good=0 y solo tres Loose positivos. V4 cap no arregla ese problema porque presencia no equivale a tapa correcta.

La propuesta por fuente se conserva como benchmark experimental; la independencia física de envases/sesiones y su representatividad industrial no están certificadas.

## 7. Qué modelos entrenar primero, cuando se autorice

1. **Detector físico TAPA** como prioridad funcional de Calidad. Ahora hay 180 cajas fuente cap reales, con escala y escenas variadas; no hace falta capturar de nuevo para preparar su entrenamiento. Revisión mínima: convención de caja, muestras difíciles, grupos/procedencia y exhaustividad. Mantener separadas las 272 Good/Broken candidatas de v26 hasta aprobar su geometría. No iniciar con una mezcla ciega de 452 cajas.
2. **Benchmark de abolladuras/superficie Mendeley**, independiente del detector de tapas. Tiene más positivos y grupos; mantener dent/scuff y gravedad originales, y no mezclar crumbled de botella completa con dent localizado. Es la alternativa con preparación más avanzada si se busca primero un prototipo de superficie.
3. **Estado/defecto de tapa** después de resolver balance de grupos y alcance Good/Broken/Loose/Ring/No Cap. No repetir el clasificador débil anterior ni declarar cap como TAPA_CORRECTA.
4. **RAYADURA bajo definición acordada**: entrenar SCUFF fuente es distinto a prometer toda rayadura industrial. Adhesión y rotura de etiqueta no se añaden como positivos.

Antes de cualquier entrenamiento: adjudicar solo los casos necesarios, confirmar qué grupos pueden usarse, congelar particiones por tarea, definir desconocidos/ignoradas, registrar configuración y aprobar ejecución. La adquisición completada no constituye autorización automática.

No se necesitan nuevas capturas para seguir preparando estos prototipos. Harán falta solo si, tras esta revisión dirigida, faltan ejemplos independientes/negativos del dominio objetivo o se quiere demostrar asociación/seguimiento y defectos temporales en una línea real. Los datasets estáticos no acreditan ese recorrido temporal por sí solos.

## 8. Verificación, archivos y conservación

Se reutilizaron el verificador de identidad y el importador público existentes. Tres pruebas dirigidas del importador aprobaron: identidad/licencia, rechazo de rutas/cajas inválidas y COCO/clases desconocidas. La primera ejecución no pudo crear fixtures por ACL de temporales Windows; se repitieron en directorios aislados del workspace, sin modificar las pruebas ni datos reales. No se repitió la suite completa previamente aprobada.

Chrome cargó la galería de **262 casos y 262 imágenes sin rutas rotas**. Las vistas son anotaciones fuente; no predicciones. Descriptores v4 se guardaron para no repetir cálculos al revisar esta fuente.

Artefactos de entrega:

- adquisicion.json, conteos_v4.json e inventario_v4.json: ZIP y conteos RAW.
- cajas_invalidas.json, derivacion_geometria.json y registro_exclusiones_y_pendientes.json: cuarentena y sus motivos.
- candidatas_cap_originales.json: las 180 cajas cap sin editar.
- grupos_y_similitud_v4.json, parejas_similitud_v4.json, distribucion_grupos_v4.json: relaciones nuevas y restricciones conservadas.
- matriz_clases_actualizada.csv, propuesta_combinacion_y_particiones.json y propuesta_particiones_actualizada.jsonl: alcance y reparto candidato, no aprobado.
- index.html: galería de todos los originales anotados, con acceso al archivo original.
- verificacion_integridad.json y pruebas_importador.json: comprobaciones.

Solo se añadieron RAW/staging/importación v4 y artefactos de auditoría nuevos. Los manifests y auditorías anteriores siguen con sus cifras históricas; no se sobrescribieron. No se modificaron anotaciones originales, las 244 cajas humanas, adjudicaciones, EPP, producción, SQLite operativo, pesos ni código de los módulos. Sin entrenamiento ni inferencia.
