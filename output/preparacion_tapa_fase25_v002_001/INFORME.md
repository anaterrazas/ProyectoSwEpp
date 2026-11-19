# TAPA · Fase 2.5 · Auditoría y decisión previa al entrenamiento

## Decisión

**NO ENTRENAR todavía.** Se aplicó la condición de parada solicitada: las referencias disponibles no permiten aún una evaluación independiente confiable de todas las tapas de una imagen. La geometría válida no garantiza semántica ni exhaustividad. No se ejecutaron entrenamiento, inferencias nuevas ni integración de un modelo no evaluado.

## Auditoría realizada

Se inspeccionaron visualmente las 180 cajas `cap` de 114 imágenes mediante ocho hojas de recortes, con contextos completos de los casos señalados. Se revisaron resúmenes visuales de los 14 componentes provisionales. Esto es una auditoría técnica, no una adjudicación humana independiente.

| Anotación | Imagen | Observación técnica |
|---|---|---|
| 31 | 9 | Caja sobre botella completa, no tapa. |
| 123 | 38 | Caja sobre botella completa, no tapa. |
| 204 | 60 | Caja sobre etiqueta del cuerpo; tapa azul fuera de la caja. |
| 567 | 165 | Caja sobre botella completa; marca Shutterstock visible. |
| 134 | 42 | Boca/cuello dudoso; requiere adjudicación. |
| 324 | 95 | Boca aparentemente abierta; requiere adjudicación. |
| 773 | 223 | Boca/rosca azul dudosa; requiere adjudicación. |

No se cambiaron estas etiquetas. Las cuatro cajas incorrectas y las tres dudosas mantienen la anotación original y una observación separada. Los otros 173 registros no quedan certificados por no presentar una alerta en esta inspección.

La imagen 24 tiene una sola caja `cap` registrada y otras tapas verdes visibles sin referencia al fondo. Evaluar todo el fotograma con esa referencia penalizaría detecciones potencialmente correctas como falsos positivos. Es necesario definir si la referencia cubre todas las tapas o solamente una región de interés; no se inventaron cajas ni regiones ignoradas.

Las 180 cajas son geométricamente válidas. A resolución 640, 31 tienen lado menor inferior a 16 píxeles; diez están a un píxel o menos del borde. Son indicadores técnicos, no etiquetas de oclusión. No hay atributos humanos suficientes para contar tapas completas, parciales, ocluidas y no evaluables. No se interpretó `iscrowd=0` como visibilidad completa. No se encontraron pares de cajas `cap` con IoU >= 0,50 en una misma imagen en la comprobación guardada.

## Procedencia, grupos y separación

Se reutilizaron la adquisición y la auditoría de similitud anteriores. Licencia de la exportación registrada: CC BY 4.0. La presencia de marcas Picxy, Shutterstock, Alamy y COLOURBOX en determinadas imágenes merece verificar procedencia individual; no equivale por sí sola a una conclusión sobre autorización o infracción.

Los grupos `v4g01` y `v4g04` contienen imágenes heterogéneas de web/producto, no sesiones de captura certificadas. `v4g02` contiene vistas de una botella en un mismo entorno; `v4g03` escenas de línea con objetos pequeños. Los 14 componentes son restricciones conservadoras, no evidencia de 14 sesiones independientes. La auditoría de similitud previa encontró 60 relaciones internas v4 y ninguna relación aceptada con las fuentes anteriores bajo sus umbrales; esto no demuestra independencia de procedencia.

El manifiesto candidato conserva 262 imágenes y las 180 cajas originales, sin copiar ni alterar los archivos fuente. No convierte las 148 imágenes sin cajas `cap` en negativos confirmados. Las seis imágenes excluidas del importador genérico por errores en otras clases se conservan como referencias en este candidato TAPA: eso no aprueba sus etiquetas para entrenar.

Propuesta conservada por grupos completos, **no aprobada**:

| Destino provisional | Grupos | Imágenes |
|---|---|---:|
| Entrenamiento | v4g01, v4g02 | 173 |
| Validación | v4g04 | 25 |
| Prueba | v4g03 | 41 |
| Pendientes | Otros diez componentes | 23 |

No hay cruces de grupo ni duplicados exactos entre estos destinos candidatos. Eso no descarta relaciones de origen no documentadas. Se conserva por hash la restricción de los 202 grupos públicos anteriores. No se mezclan automáticamente Mendeley ni v26: sus regiones de defectos, anillos o huecos no son etiquetas compatibles de tapa física. Las 25 referencias propias permanecen fuera del entrenamiento por su procedencia pendiente.

## Entregables y comprobaciones

- `index.html`: galería priorizada, hojas de las 180 cajas y resumen de grupos.
- `auditoria_180_cajas.json`: observaciones separadas de los registros originales, hashes y señales técnicas.
- `dataset_candidato.jsonl`: dataset experimental por referencias, bloqueado para entrenamiento; no es una exportación YOLO lista para usar.
- `manifiesto_particiones.json`: grupos indivisibles y propuesta no aprobada.
- `decision_entrenamiento.json`: parada explícita; métricas no calculadas.
- `verificacion_integridad.json`: comparación con 26.361 archivos protegidos previos y hashes de las 262 imágenes v4 y COCO original.
- `consolidar_auditoria.py`: consolidación reproducible y comprobaciones mediante aserciones.

No hay modelo, checkpoints, TP/FP/FN, precisión, recall, F1 ni mAP nuevos. Tampoco errores por visibilidad o tamaño del modelo: no se ejecutó inferencia. Los conteos de auditoría no son métricas de detección. No se modificaron EPP, producción, SQLite, pesos ni evaluaciones anteriores.

## Siguiente paso mínimo

1. Adjudicar únicamente los siete casos identificados, conservando originales y creando correcciones versionadas. Aislar sus imágenes completas hasta resolverlos; no borrar solo una caja y convertir el objeto en fondo.
2. Definir el alcance de evaluación (todas las tapas o ROI explícita) y revisar exhaustividad del subconjunto que se reservará para validación/prueba, empezando por la escena 24. Conservar desconocidos como NO EVALUABLE.
3. Confirmar procedencia e independencia de los grupos reservados y revisar sus referencias de visibilidad. Si no puede demostrarse independencia, denominar el resultado exploratorio y resolver esa carencia antes del entrenamiento solicitado.
4. Con ese cierre, generar el export de una clase TAPA y elegir un detector de objetos compatible, registrando pesos iniciales, versiones e hiperparámetros antes de entrenar. No hace falta pedir nuevas capturas ahora: primero resolver estas incidencias concretas con los datos existentes.

La canalización de video existente se mantiene intacta. Su conexión a un modelo TAPA queda pendiente de superar la auditoría y evaluar el modelo; no se activaron asociaciones tapa-envase sin evidencia.
