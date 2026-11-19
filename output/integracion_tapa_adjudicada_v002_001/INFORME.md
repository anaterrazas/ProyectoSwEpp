# Integración de adjudicaciones TAPA · Calidad v002

18/11/2026 · America/La_Paz. Sin entrenamiento, inferencia ni nueva anotación. Se reutilizaron decisiones humanas, historial, escritor y validador existentes.

## Decisiones verificadas y persistencia

Se encontraron siete archivos de decisión, una versión por caso, todos ADJUDICADO. Autor declarado Ana; fechas UTC entre 2026-11-18T14:31:58.822975+00:00 y 2026-11-18T14:36:31.333164+00:00. Las siete decisiones son ENVASE → TAPA. No hay conflictos pendientes entre los siete casos.

Se verificaron secuencia/hash padre del historial, sample_id, box_id, clase y caja originales, nota original y hash de revisión de origen. Cada decisión contiene autor, fecha y justificación. Se congeló además el hash de cada archivo y se comprobó nuevamente al terminar. No se modificaron decisiones guardadas ni se reinterpretaron sus textos.

Las justificaciones de los casos 1–2 describen tapa colocada; el caso 3, tapa suelta. Se conservan como evidencia humana textual, sin convertirlas automáticamente en nuevas clases de defecto. Los casos 4 y 5 conservan respectivamente el texto «roja amarilla» y el sufijo «Copiar»: no afectan a la decisión explícita TAPA, pero no deben utilizarse para derivar color automáticamente. No se solicita repetir adjudicación de clase por esos detalles editoriales.

Ninguna decisión acredita segunda revisión independiente. La variación de escritura ana/Ana no acredita otra persona. La clase adjudicada permite localizar el objeto; no demuestra TAPA_CORRECTA o calidad de cierre.

## Copia experimental integrada

Dataset nuevo:

`datasets/calidad_botellas/v002/experiments/detection_manual_v001/dataset_tapa_adjudicado_fase23_001`

Se copiaron las 25 imágenes, manifiesto e historial original y se anexaron siete revisiones nuevas mediante el escritor existente. Las versiones anteriores no se reemplazaron. Las revisiones anexadas identifican `sistema.integracion_adjudicaciones` como autor técnico y explican que son una derivación automática de decisiones humanas, no una nueva revisión humana. Los autores/fechas humanos originales se conservan íntegros en `procedencia_integracion.json` y sus archivos fuente.

Cambios de contenido de cajas: únicamente class_name de las siete autorizadas. Se preservaron las 244 cajas, coordenadas, notas, flags de visibilidad/evaluabilidad, identidades y enlaces. Las cajas reclasificadas no eran padres de otras tapas y no producen duplicaciones geométricas de alto solapamiento con las tapas existentes en sus frames. El validador verificó todas las revisiones, hashes, coordenadas y enlaces de la copia.

El campo aplicado_a_anotaciones de las decisiones fuente se conserva sin editar: no se aplicaron a los originales. Su integración en esta copia está documentada separadamente con hash de decisión y de revisión nueva. No se exportaron etiquetas YOLO de entrenamiento ni se copiaron exportaciones antiguas que pudieran quedar obsoletas.

La página Django de adjudicación sigue mostrando las decisiones humanas; el anotador de localhost:8792, si continúa abierto, conserva la copia anterior de Fase 2.1. No confundir esa copia con el dataset nuevo indicado arriba. No se reiniciaron servidores ni se cambió la aplicación para esta integración.

## Auditoría actualizada de las 244 cajas

| Concepto | Antes | Copia adjudicada |
|---|---:|---:|
| Imágenes | 25 | 25 |
| ENVASE | 108 | 101 |
| TAPA | 136 | 143 |
| Total cajas | 244 | 244 |
| Conflictos ENVASE con nota de tapa señalados | 7 | 0 |

| Fuente | Imágenes | ENVASE | TAPA |
|---|---:|---:|---:|
| prueba2.mp4 | 15 | 101 | 125 |
| tapas.mp4 | 10 | 0 | 18 |

Evaluabilidad registrada: ENVASE 100 evaluables y 1 no evaluable; TAPA 143 evaluables. No se infirió nueva evaluabilidad al cambiar la clase. Visibilidad TAPA agrupada sin doble conteo: 1 totalmente visible, 131 parciales sin oclusión y 11 ocluidas. Las ocluidas también conservan su flag parcial; no se eliminaron ejemplos.

Continúa el aviso geométrico de la caja ENVASE mínima del frame 0 de prueba2. No se corrigió porque no forma parte de las siete decisiones. Los diez frames de tapas conservan el aviso histórico de posible desenfoque de imagen; la auditoría anterior señalaba once crops de tapas, un indicador distinto. No se repitieron mediciones ni se confundieron ambos denominadores.

Los siete cambios resuelven el conflicto de clase, no todas las limitaciones de calidad. Se conserva la falta de IDs físicos y segunda revisión independiente. Las métricas anteriores pertenecen a referencias anteriores; no se reutilizan como métricas de la nueva copia ni se cuentan 143 FN TAPA por no disponer todavía de detector.

## ¿Se puede entrenar ya?

**Todavía no se recomienda autorizar un entrenamiento evaluable.** La copia ya tiene referencias de clase corregidas y puede servir como base de desarrollo, pero el validador existente devuelve suficiente_entrenamiento=false.

Bloqueos concretos actuales:

1. Ambos session_id son desconocidos. El agrupador conserva ambos videos y los 25 frames en un único componente UNASSIGNED. Train, validation y test tienen cero muestras asignadas; no existe evaluación independiente reservada.
2. Procedencia/derechos de uso de ambos videos siguen sin confirmar. Es un dato que debe aportar el responsable; no se deduce por estar el archivo en el proyecto.
3. No se acredita segunda revisión independiente, en especial para una futura referencia de evaluación reservada.
4. Cobertura estrecha: dos clips conocidos y observaciones correlacionadas. La auditoría previa no tenía tapas con lado mínimo <16 px al tamaño 640 y concentraba colores, fondos y vistas en pocas escenas. No repetir fotogramas para inflar la cantidad.
5. Antes de exportar debe fijarse el alcance TAPA y tratamiento de ignoradas. El exportador genérico actual considera elegibles 24 frames porque uno tiene ENVASE no evaluable; no eliminarlos o convertirlos en negativos silenciosamente. Un futuro export TAPA exclusivo puede revisar ese criterio por clase si se conserva exhaustividad TAPA, sin fingir que ya se ha implementado.

El mensaje genérico del anotador menciona anotación/revisión como requisitos: aquí las 25 últimas anotaciones sí están reviewed y los siete conflictos ya se resolvieron. No se pide repetirlas. Los bloqueos decisivos ahora son procedencia, agrupación, evaluación reservada y cobertura.

No existe una cifra de 143 cajas que garantice suficiencia o equivalga a 143 tapas físicas. El objetivo de nueve sesiones de la propuesta anterior es planificación de cobertura, no una condición numérica universal.

## Siguiente paso mínimo, reutilizando los videos existentes

**Primero completar una ficha de procedencia/sesión de los videos, no volver a anotar ni entrenar.** Confirmar origen, fecha o sesión identificable, derechos y relaciones entre secuencias para prueba2 y tapas, y determinar si produccion.mp4, botellasSinTapa.mp4 o produccion_prueba_02.mp4 aportan sesiones realmente distintas y tapas visibles del dominio objetivo. No reauditar sus bytes o extraer frames antes de conocer esa independencia.

Después, reservar **dos grupos completos de captura independientes del desarrollo y entre sí**, uno para validación y otro para test, reutilizando los otros videos si su procedencia y contenido lo permiten. Esto es el mínimo lógico de tres grupos para separar desarrollo/validación/prueba, no suficiencia estadística ni validación industrial. Más de una sesión por partición sigue siendo preferible. Si los videos existentes no aportan esos grupos, capturar únicamente los que falten.

Anotar solo el material nuevo de esos grupos, cubriendo TAPA colocada y suelta, confusores/negativos revisados, tamaños y visibilidad relevantes; reservarlos antes de ajustes. No es obligatorio reunir todavía todas las clases de defecto para entrenar localización física TAPA. Confirmar etapa posterior al tapado sí es indispensable para etiquetar ausencia como defecto, pero no para dibujar una tapa física visible. No anotar una boca vacía como TAPA.

Puerta de autorización posterior: derechos y sesiones confirmados, particiones sin fuga, referencia de evaluación revisada independientemente, positivos/negativos e ignoradas definidos, cobertura adecuada al alcance, configuración y criterio de aceptación congelados. Presentar ese resultado antes de pedir autorización explícita de entrenamiento. No entrenar automáticamente al alcanzar un conteo.

## Verificaciones realizadas, sin repetir trabajo previo

- Cuatro pruebas nuevas del integrador aprobadas: solo cambia lo autorizado, preserva originales, rechaza decisiones pendientes/incompletas/incompatibles o duplicadas y no convierte NO EVALUABLE en TAPA.
- Comprobación real de siete decisiones persistidas, siete revisiones derivadas y todas las 244 cajas mediante el validador existente.
- 1.450 archivos protegidos intactos, incluidos anotaciones, decisiones, EPP, producción, SQLite operativo y evaluaciones anteriores cubiertas por el manifiesto. La integración no usa SQLite para escribir.
- No se repitieron pruebas de navegador, anotador o modelos ya aprobadas; no se recalcularon métricas de detección ni se generaron imágenes nuevas.

## Archivos de esta entrega

- `procedencia_integracion.json`: decisiones completas, hashes de cada fuente y mapa a revisiones anexadas.
- `referencias_adjudicadas.json`: instantánea de las 25 referencias y 244 cajas corregidas.
- `auditoria_dataset.json`: informe del validador existente sobre la copia nueva.
- `resumen.json`, `protegidos_antes.json`, `verificacion_integridad.json`: conteos y conservación.
- Código nuevo exclusivamente experimental: `experimentos/pilotos/integrar_adjudicaciones_tapa.py` y `test_integrar_adjudicaciones_tapa.py`.

No se modificaron EPP, producción, SQLite operativo, pesos, originales ni evaluaciones anteriores. No hubo entrenamiento, inferencia, pseudoetiquetado ni cambios humanos inventados.
