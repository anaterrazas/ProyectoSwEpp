# Cierre de adjudicación · TAPA v003

**NO PREPARADO PARA ENTRENAMIENTO EXPERIMENTAL.** Se generó una copia candidata nueva con las decisiones reales, sin entrenar ni inferir. La integridad técnica y la separación por grupos se verificaron; el cierre semántico/exhaustivo y la independencia siguen bloqueados.

## Decisiones guardadas

Se verificaron 10 generaciones, correspondientes a 7 imágenes, no diez muestras independientes. Los siete conflictos tienen decisiones explícitas; ninguno queda PENDIENTE de clase. Se preservan también las revisiones repetidas 2 y 3 de imagen 9, y 10 de imagen 223: no se eliminan ni suman cajas por cada guardado.

| Anotación | Imagen | Clase adjudicada | Visibilidad | Última revisión |
|---|---|---|---|---|
| 31 | 9 | ENVASE | TOTAL | 3 |
| 123 | 38 | ENVASE | PARCIAL | 4 |
| 134 | 42 | NO_EVALUABLE | DUDOSA | 5 |
| 204 | 60 | NO_EVALUABLE | TOTAL | 6 |
| 324 | 95 | NO_EVALUABLE | DUDOSA | 7 |
| 567 | 165 | ENVASE | TOTAL | 8 |
| 773 | 223 | NO_EVALUABLE | TOTAL | 10 |

Además, la caja 203 de imagen 60 está adjudicada TAPA / TOTAL. NO EVALUABLE en 204 y 773 se usa en sus notas para excluir regiones que no son una tapa; en 134 y 324 se declara duda visual. Se conservan esos motivos distintos y sus visibilidades originales; no se traducen a ausencias ni etiquetas negativas.

## Conteos del candidato v003

- TAPA: **173**: 1 con adjudicación humana nueva y 172 conservadas de la fuente sin nueva revisión. No son 173 tapas humanas validadas.
- ENVASE: **3**, provenientes de las reclasificaciones 31, 123 y 567. Este conteo corresponde solo al candidato de tapas; no es el total de envases de todas las fuentes.
- Excluidas de positivos: **4**, anotaciones 134, 204, 324 y 773. Siguen en la trazabilidad como NO EVALUABLE, no se borran.
- Cajas nuevas manuales: **0**. No hay cajas omitidas recuperables de estas diez versiones: todas guardaron `nuevas_cajas: []`.
- Se conservan las 180 cajas fuente: 173 + 3 + 4 = 180. No se modifican las 915 anotaciones RAW ni las 244 referencias propias.

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
| train | 173 | 76 | 1 | 1 |
| test | 41 | 41 | 0 | 2 |
| validation | 25 | 36 | 0 | 1 |
| PENDIENTE | 23 | 20 | 2 | 0 |

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
