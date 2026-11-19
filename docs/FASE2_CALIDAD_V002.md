# Fase 2 Calidad v002: auditoría, plan y primer avance

Fecha: 18/11/2026 · America/La_Paz. Alcance exclusivo de Calidad experimental. El diagnóstico se presentó antes de modificar código. No hubo entrenamiento, inferencia nueva, cambios de etiquetas ni activación de capacidades en producción.

## Diagnóstico técnico

La plataforma ya separa EPP y Calidad mediante catálogo de capacidades, permisos, paneles y artefactos. Calidad tiene tres capas que deben seguir diferenciadas:

1. `experimentos/pilotos/detectar_calidad.py` y `evaluacion.py`: localización ENVASE sobre las referencias humanas y comparación IoU.
2. `experimentos/pilotos/ejecutar_calidad.py`: detector COCO y ByteTrack, video/evidencias/JSONL; no localiza tapas ni clasifica defectos.
3. `datasets/calidad_botellas/v002/experiments/individual_v001/`: adaptadores, comparación de detectores, tracker de observaciones actuales, ROI cuerpo/cuello, controles técnicos y veto previo a clasificar. Es investigación reutilizable, no validación integral.

El panel `/demo/calidad/` ya reproduce originales, simulación y evidencias, enlaza galería y trazabilidad y conserva las capacidades pendientes. No necesita reconstrucción. La gestión operativa de lotes/inspecciones no se modifica para esta fase.

### Modelos y pesos existentes

| Componente | Capacidad real | Estado |
|---|---|---|
| YOLO11s COCO, `individual_v001/weights/yolo11s.pt` | bottle 39 → ENVASE, confianza 0,30, entrada 640 | Baseline seleccionado experimentalmente; no detector TAPA |
| YOLO11n COCO, `yolo11n.pt` | Botellas en comparaciones previas | Alternativa evaluada exploratoriamente; no se cambia el baseline |
| Faster R-CNN MobileNetV3 320, pesos locales en individual_v001 | Clase bottle de COCO | Alternativa comparada; no detector TAPA |
| TinyCapCNN, `day1_v001/artifacts/cap_model.pt` | Clasificación binaria TAPA_DEFECTUOSA, entrada 96×96 | No genera bounding boxes ni distingue las tres clases de colocación |
| `Modelos/best.pt` | Equipos de protección | Pertenece a EPP; no se reutiliza como detector Calidad |

Hashes de pesos encontrados en el ámbito revisado: `output/calidad_fase2_v002_001/auditoria_datos.json`. No se cargaron pesos para inferencia ni se entrenó. Los resultados previos de comparación no se reescriben.

TinyCapCNN tiene un ensayo anterior de 50 referencias: train 18 (11 positivas/7 negativas), validation 15 (todas positivas) y test 17 (10 positivas/7 negativas). Test: TP 7, TN 3, FP 4, FN 3; F1 66,67 %, exactitud 58,82 %, igual al baseline mayoritario. No aporta especificidad calibrable en validation ni generalización acreditada a la línea. El prototipo de clasificación por ROI/escena completa no sustituye la inspección individual ni se convierte automáticamente a TAPA_CORRECTA/TAPA_AUSENTE/TAPA_MAL_COLOCADA.

### Referencias humanas revisadas

Se comprobó la instantánea conservada contra la última revisión original de cada muestra: las 25 coinciden. Los 25 PNG coinciden con sus hashes. Estado reviewed en los 25 casos, sin acreditación de segundo revisor independiente.

- ENVASE: 108 cajas, de las cuales 107 evaluables y 1 no evaluable.
- TAPA: 136 cajas; 59 con enlace humano a envase y 77 sin enlace.
- Total: 244 cajas, distribuidas en 15 frames de prueba2 y 10 de tapas.
- No confundir esos atributos/cajas con etiquetas de defectos o trayectorias temporales.

Los siete conflictos existentes persisten exactamente, incluidos box_id y notas:

| Video | Frame | Clase guardada | Nota humana |
|---|---:|---|---|
| prueba2 | 120 | ENVASE | tapa roja |
| prueba2 | 240 | ENVASE | tapa roja |
| prueba2 | 330 | ENVASE | tapa roja suelta |
| tapas | 100 | ENVASE | tapa amarilla |
| tapas | 250 | ENVASE | tapa amarilla |
| tapas | 300 | ENVASE | tapa amarilla |
| tapas | 350 | ENVASE | tapa amarilla |

No se corrige la clase usando la nota automáticamente: requiere adjudicar objeto y geometría, conservando versión padre y autor. La octava FN del baseline es una caja mínima que necesita revisar evaluabilidad. El resultado previo ENVASE 99 TP/39 FP/8 FN/2 ignoradas permanece como concordancia mecánica provisional. No se publican métricas nuevas ni se reinterpretan las 136 tapas como FN: su detector no se ejecutó.

Los atributos de visibilidad están muy sesgados a parcial/ocluido; revisar convención de caja visible frente a amodal antes de exportar entrenamiento. Reviewed y exhaustive no resuelven por sí solos las contradicciones semánticas.

### Datos existentes que no son intercambiables

- `detection_manual_v001/dataset`: cajas ENVASE/TAPA, versiones humanas y exportaciones. Fuente inicial para localización, pendiente de adjudicación y cobertura independiente.
- `day1_v001/dataset`: clasificación binaria por imagen, sin cajas TAPA equivalentes. Sus 50 referencias no se convierten en ejemplos de detección sin anotación específica.
- `v002/images`, `reviews`, `labels`, `metadata`, `incoming`: datos y revisiones con procedencia y licencias heterogéneas. La existencia de una imagen no acredita su uso para entrenar. La auditoría histórica excluyó imágenes de licencia desconocida y mantiene fotografías propias en preimportación; no se revocan esas exclusiones.
- Observaciones/crops/predicciones históricas: evidencia de ejecución, nunca verdad humana ni nuevas etiquetas.

## Arquitectura de implementación incremental

```text
Video original + hash + PTS
        |
Detector ENVASE             Detector TAPA independiente, pendiente
        |                              |
Observaciones actuales y tracking separado por clase/ejecución
        |                              |
Perfil de línea/SKU + cuello visible + geometría/ambigüedad + evidencia temporal
        |
Asociación propuesta o abstención, nunca asignación forzada
        |
ROI cuello/tapa observada o ROI geométrica identificada como candidata
        |
Evaluabilidad por tarea y modelos de inspección con alcance evaluado
        |
NO EVALUABLE / decisión experimental trazable + revisión humana
        |
Panel Calidad y artefactos existentes; EPP permanece independiente
```

El cuello geométrico del 38 % superior ya existe, pero no es una tapa detectada ni acredita compatibilidad con el dominio del clasificador. Reutilizarlo como ROI candidata, con ese origen explícito. No generar una caja TAPA desde un recorte.

Los IDs serán locales a ejecución y clase; no identidad física de la botella ni identidad global entre cámaras. Una observación sin ID confirmado debe conservarse, sin fabricar un track. Detección, asociación, clasificación y persistencia tendrán métricas y referencias independientes.

La futura asociación debe exigir tapa detectada y perfil de geometría evaluado: región superior/cuello plausible, cobertura suficiente, exclusividad de enlace y margen de ambigüedad entre envases próximos. Una tapa suelta no se fuerza al envase más cercano. Primero candidatos geométricos explícitamente no validados; solo después evaluación con enlaces humanos adjudicados y comportamiento temporal. El score de detección no se convierte en confianza de asociación o probabilidad calibrada de calidad.

VISIBLE/PARCIAL/NO_EVALUABLE deben conservar origen y tarea. Un control de resolución/desenfoque favorable no permite inventar una etiqueta humana VISIBLE. La ausencia de detección TAPA no acredita TAPA_AUSENTE. Para evaluar esa clase faltan cuello verificable, obligación de tapa y etapa posterior al tapado confirmadas, además de evidencia humana de ausencia y un modelo evaluado.

## Plan priorizado y puertas de avance

| Orden | Tarea | Condición de avance |
|---|---|---|
| 1 | Auditar modelos, referencias y conflictos | Completado en esta entrega; originales intactos |
| 2 | Contrato individual y adaptación de observaciones existentes | Completado como preparación estructural, no como detector nuevo |
| 3 | Adjudicar siete conflictos y caja mínima | Nuevas revisiones humanas versionadas; convención de caja y evaluabilidad explícitas |
| 4 | Preparar dataset detector ENVASE/TAPA | Licencia/procedencia, cajas completas por alcance, enlaces opcionales conocidos/desconocidos y partición por video/sesión |
| 5 | Revisar suficiencia de datos y autorizar entrenamiento | Negativos humanos válidos, dominio/escala cubiertos, prueba reservada y configuración previa |
| 6 | Entrenar/evaluar detector de tapas | Pesos nuevos versionados, localización por clase, FP/FN y regiones ignoradas; sin tocar pesos anteriores |
| 7 | Asociación y recortes reales | Enlaces evaluados y abstención ante oclusión/ambigüedad; luego integración de capacidades reales en Calidad |
| 8 | Inspección de defectos | Modelos y referencias por tarea, revisión y dominio; incorporación progresiva sin cambiar EPP ni el inicio |

No se entrenará directamente con los 25 frames como si fueran train/validation/test independientes: son videos conocidos y correlacionados, ya usados en evaluación y desarrollo. Para detector de tapas faltan sesiones reservadas, diversidad de escala/color/rosca, vistas laterales y oblicuas, tapas puestas/sueltas, envases próximos, oclusiones, reflejos y desenfoque. Se requieren negativos confirmados/exhaustivos y regiones desconocidas excluidas; no se deducen negativos de anotaciones ausentes.

No se fija un número arbitrario de imágenes que garantice suficiencia. La decisión debe basarse en cobertura por sesión/SKU y curvas de rendimiento, sin seleccionar umbrales sobre el test reservado. No se solicita en esta entrega una anotación masiva ni se generan etiquetas automáticas.

RAYADURA/DEFORMACION necesitan ejemplos de fabricación y negativos revisados del mismo dominio. Botellas aplastadas o material reciclado no equivalen automáticamente a deformación de fabricación. TAPA_CORRECTA y TAPA_MAL_COLOCADA requieren definición de colocación aceptable y evidencia visible. No se habilitan esas clases solo añadiendo nombres al catálogo.

## Primer avance implementado y verificado

Se añadieron únicamente:

- `experimentos/pilotos/calidad_individual.py`: contrato de preparación de inspección, validación de cajas/scores/procedencia, IDs locales, ROI candidata explícita y estados pendientes por clase. No importa motores de IA ni invoca Django o SQLite.
- `experimentos/pilotos/test_calidad_individual.py`: siete pruebas de preservación, abstención, aislamiento de objetos, procedencia, rechazo de observaciones inválidas, IDs y recortes que no alteran la imagen. Fixtures técnicos identificados; no son datos ni predicciones de evaluación.
- Este documento y `output/calidad_fase2_v002_001/` con auditoría, representación derivada y verificaciones.

Se adaptó la simulación histórica existente, no se volvió a procesar el video: 399 filas, 1.087 observaciones y 39 IDs temporales. Se comprobó igualdad exacta de cajas, scores e IDs. El JSONL nuevo es una representación estructural, no una inferencia, referencia humana ni mejora de rendimiento.

`tapas_observadas=null` indica detector no disponible; no es una lista vacía de tapas ausentes. Ningún envase recibe tapa asociada ni conformidad. Las cinco clases de inspección tienen predicción y score null, estado NO DISPONIBLE, y la inspección global NO EVALUABLE. La clasificación binaria heredada se conserva aparte, sin mapearla a clases nuevas.

45 pruebas automatizadas aprobadas: siete nuevas y 38 regresiones del portal, referencias, evaluación y reglas EPP. Django no detectó incidencias. No se probaron precisión de TAPA ni asociación nueva porque todavía no existen esas capacidades evaluadas.

No se activó el contrato en la interfaz como función validada: el panel Calidad conserva sus capacidades y límites anteriores. El contrato prepara una entrada de observaciones para futuros adaptadores; aún no implementa detector de tapas, algoritmo de asociación, tracker nuevo ni clasificador de los cinco defectos. Los componentes futuros se integrarán únicamente en Calidad tras su evaluación, usando el catálogo y servicio de artefactos existentes.

## Evidencia y conservación

- `auditoria_datos.json`: 25 imágenes, conflictos persistentes, particiones de clasificación y pesos encontrados.
- `observaciones_preparadas.jsonl`: representación derivada de los registros históricos, sin imágenes ni anotaciones nuevas.
- `verificacion_adaptador.json`: conteos, procedencia y alcance sin inferencia.
- `protegidos_antes.json` / `verificacion_integridad.json`: conservación de datos, módulos operativos y evaluaciones.

No se alteraron videos, fotografías, revisiones humanas, pesos, datasets, evaluaciones previas, EPP, producción o SQLite operativo. No hubo migraciones, cambios de usuarios ni nuevos resultados de IA. El bloqueo para la siguiente mejora funcional es detector TAPA y referencia adjudicada, no la página principal del sistema.
