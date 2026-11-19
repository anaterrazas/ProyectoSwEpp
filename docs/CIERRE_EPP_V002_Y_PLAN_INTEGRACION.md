# Cierre experimental EPP v002 y diagnóstico de integración

Fecha: 18/11/2026 · America/La_Paz. Alcance: revisión documental y del código existente. No se ejecutó inferencia nueva, entrenamiento, migración, servidor ni cambio de configuración. Este documento no sustituye ni modifica evaluaciones anteriores.

## Dictamen del producto

El proyecto dispone de aplicación Django, laboratorio aislado, reproducción de fuentes, artefactos de inferencia, revisión EPP y herramientas de evaluación. Puede preparar una demostración conjunta de capacidades experimentales, con resultados y limitaciones visibles. Todavía no está listo para demostrar control automático fiable de seguridad y calidad de tapa después del tapado.

EPP es el módulo más avanzado: detección y seguimiento ejecutados realmente, referencia humana de 33 fotogramas y comparación de umbrales, asociación, persistencia y videos completos. Su cierre es de laboratorio supervisado; no acredita cumplimiento ni validación industrial.

Calidad tiene un baseline de localización ENVASE, herramientas de seguimiento y un clasificador experimental de tapa distinto del detector. No dispone de detector TAPA evaluado en este baseline ni de evaluación fiable de tapa correcta/ausente/mal colocada. El principal bloqueo del recorrido conjunto está aquí, no en la interfaz común.

No se asigna porcentaje global de avance: falta un alcance de aceptación y una descomposición aprobada que permitan calcularlo.

## 1. Consolidación de la evidencia EPP

| Etapa conservada | Evidencia | Interpretación |
|---|---|---|
| Diagnóstico y primera ejecución temporal | `seguridad_epp_v002_001` | Dos fuentes, originales, tracking, observaciones y videos; métricas iniciales sin referencia no equivalen a las posteriores |
| Primera comparación humana | `evaluacion_epp33_v002_001` | 33 imágenes aisladas, 203 cajas: PERSONA 74, CASCO 55, CHALECO 74 |
| Auditoría de errores y configuraciones | `auditoria_errores_epp33_v002_001` | 83 casos priorizados: 44 FN chaleco, 20 FN casco y 19 FP persona; seis configuraciones y candidata híbrida post hoc |
| Comparación temporal final | `comparacion_videos_epp_v002_001` | 374 fotogramas completos; base existente verificada y nueva inferencia EPP candidata; personas/tracks compartidos exactamente |

Las dos fuentes son `media/videos/trabajadores.mp4` (122 fotogramas, 4,88 s) y `pruebas_ia/trabajadores.mp4` (252, 10,08 s). El duplicado trabajador_prueba no añade muestra. Los clips son conocidos y los fotogramas temporalmente correlacionados: no hay validación independiente ni un test nuevo tras seleccionar umbrales.

### Modelos y parámetros congelados

| Componente | Archivo / catálogo | Parámetros |
|---|---|---|
| PERSONA | `yolo11n.pt`, COCO persona 0 | Confianza 0,30; entrada 640; CPU; ByteTrack |
| EPP | `Modelos/best.pt`, 14 clases | Hardhat 3 → CASCO, Safety Vest 13 → CHALECO; NO-Hardhat 8 y NO-Safety Vest 10 como señales negativas explícitas |
| Base | Mismos pesos | Confianza 0,30 |
| Candidata de laboratorio | Mismos pesos | Solo Safety Vest 0,15; casco, persona y clases negativas 0,30 |
| Postprocesado | NMS por clase | IoU NMS 0,50; distinto conceptualmente del IoU de evaluación 0,50 |
| Asociación y eventos | `seguridad/piloto.py`; umbral específico en ejecutor experimental | Centro en región anatómica, abstención ante ambigüedad/conflicto; persistencia 2 s; intervalo máximo 0,5 s |

SHA-256 de pesos y tracker, sin cambios:

```text
yolo11n.pt
0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1
Modelos/best.pt
2b33d4d016f9751c5a25f4a72ce050e0a7e4e140b11c1669978d7154003a4f61
bytetrack.yaml instalado
395701d947a749179dee3e327b1181b730c4ca98e7cac5a2ab05280aae573b8b
```

Versiones registradas en las ejecuciones: Ultralytics 8.4.212, Torch 2.15.0, OpenCV 5.0.0.93, NumPy 2.5.4. El manifiesto `modelos_y_parametros.json` y el `plan.json` temporal conservan la configuración. No confundir la clase Person interna del modelo EPP con el detector PERSONA separado utilizado en la comparación.

### Métricas por alcance

Primera evaluación de imágenes aisladas, base:

| Clase | TP / FP / FN | Precisión | Recall | F1 |
|---|---|---:|---:|---:|
| PERSONA | 51 / 19 / 23 | 72,86 % | 68,92 % | 70,83 % |
| CASCO | 35 / 7 / 20 | 83,33 % | 63,64 % | 72,16 % |
| CHALECO | 30 / 1 / 44 | 96,77 % | 40,54 % | 57,14 % |

Comparación final: mismas 33 referencias, pero predicciones de procesamiento continuo con personas filtradas por seguimiento:

| Configuración | Clase | TP / FP / FN | Precisión | Recall | F1 |
|---|---|---|---:|---:|---:|
| Ambas | PERSONA | 53 / 12 / 21 | 81,54 % | 71,62 % | 76,26 % |
| Ambas | CASCO | 35 / 7 / 20 | 83,33 % | 63,64 % | 72,16 % |
| Base | CHALECO | 30 / 1 / 44 | 96,77 % | 40,54 % | 57,14 % |
| Candidata | CHALECO | 43 / 1 / 31 | 97,73 % | 58,11 % | 72,88 % |

La diferencia de PERSONA entre etapas no demuestra mejora por el umbral de chaleco: cambia el tratamiento de las salidas de personas. No sumar TP/FP/FN de ambas etapas: reutilizan referencias. La candidata recupera 13 chalecos, conserva 31 FN y no aumenta el FP agregado de chaleco en este conjunto explorado.

La asociación se mide aparte. En la comparación temporal muestreada, CASCO tiene 28/55 enlaces completos correctos; CHALECO pasa de 20/74 a 31/74. La híbrida previa sobre imágenes aisladas tenía 18/74 → 29/74: es otro alcance de ejecución y debe conservarse por separado. Mejorar localización no asegura reconocer al propietario.

En videos completos, CHALECO pasa de 56 a 116 observaciones en el corto y de 229 a 334 en el largo. Son observaciones repetidas, no objetos únicos ni TP certificados fuera de las 33 referencias. Se registran 4 y 10 IDs, con 3 y 12 interrupciones respectivamente. Hay indicios de fragmentación: P3 del corto aparece emparejada a IDs 5/7; P2 del largo a 2/20. No hay trayectorias humanas exhaustivas para calcular IDF1, MOTA o cambios de identidad certificados.

Ambas configuraciones generan cero candidatos persistentes. Las señales negativas duran como máximo 0,12 s, inferiores a 2 s. Cero candidatos no prueba ausencia de incumplimientos ni una tasa nula de falsas alarmas. No se dispone de métricas de incumplimiento, falsas alarmas/minuto ni persistencia correcta.

Se conservan 19 estados de casco NO_EVALUABLE, cero ausencias humanas confirmadas y la inconsistencia conocida de visibilidad en epp_largo_000100/P2. Falta segunda revisión independiente. El estado heredado CUMPLE describe presencia asociada de un equipo; no se debe presentar como conformidad global del trabajador.

### Funcionalidades EPP y pendientes

Implementado y con evidencia previa: inferencia local; seguimiento; asociación anatómica con abstención; candidatos por persistencia; reporte y evidencia; reproducción original/resultado; decisiones humanas con observación obligatoria, historial y control de versión; autenticación, permisos y CSRF. La ausencia de candidatos reales en estos clips limita la demostración del recorrido de revisión: su comportamiento está probado con fixtures técnicos, que no deben presentarse como alertas reales.

Pendiente: resolver omisiones de chaleco/persona, asociación bajo oclusión y proximidad, continuidad de IDs, evaluación de ausencias confirmadas e intervalos, adjudicación de referencias y generalización. Configuración candidata permanece exclusivamente en laboratorio. El informe temporal registra 22 pruebas aprobadas, reproducción de ambos MP4, 132 imágenes sin errores y 534 archivos protegidos intactos; son comprobaciones de aquella entrega, no pruebas nuevas de esta consolidación.

## 2. Estado del módulo Calidad

### Software existente frente a capacidad demostrada

La aplicación contiene productos, criterios, lotes, análisis y registros de inspección/revisión, además de conteo y videos. El catálogo incluye BOTELLA, CAJA y BOLSA; esto acredita estructura de software, no detección ni clasificación validadas para cada tipo.

El laboratorio tiene reproductor `/calidad/`, ejecutor `ejecutar_calidad.py`, detector `detectar_calidad.py`, referencias y comparador. El panel actual de Calidad es un visor de fuentes; no equivale a una consola integral de inferencia y adjudicación. La biblioteca `individual_v001` contiene seguimiento, regiones geométricas y un veto previo a clasificación por dominio/visibilidad. Esas regiones no constituyen detecciones de tapas.

Modelo de localización evaluado: `datasets/calidad_botellas/v002/experiments/individual_v001/weights/yolo11s.pt`, COCO bottle 39 → ENVASE, confianza 0,30, entrada 640, CPU. SHA-256:

```text
85a76fe86dd8afe384648546b56a7a78580c7cb7b404fc595f97969322d502d5
```

Existe clasificador experimental en `datasets/calidad_botellas/v002/experiments/day1_v001/artifacts/cap_model.pt`, distinto de un detector TAPA. El reporte de la simulación registra SHA-256:

```text
548886556125f43ef232d21274643907b65d6c4bb7c5353f6c51eca6c13c96b1
```

Ese clasificador no acredita localización ni discriminación validada de tapa correcta, ausente y mal colocada. No se promueve otro detector disponible en experimentos a modelo aceptado por existir su archivo.

### Evidencia real y límites

Evaluación de 25 fotogramas: 15 de prueba2.mp4 y 10 de tapas.mp4. Referencia actual: 107 ENVASE evaluables, 1 ENVASE no evaluable y 136 TAPA. Las versiones históricas de anotación no son muestras adicionales. Reviewed no demuestra segundo revisor independiente.

Se obtuvieron 140 predicciones ENVASE: 99 TP, 39 FP, 8 FN y 2 ignoradas. Concordancia mecánica: precisión 71,74 %, recall 92,52 %. Estas cifras son provisionales: siete cajas ENVASE tienen notas que describen tapas y siete de los ocho FN corresponden a esos conflictos; la octava es una caja mínima cuya evaluabilidad requiere revisión. No se reetiquetó nada. No interpretar los siete como omisiones confirmadas de envases.

TAPA no se ejecutó como detector: sus 136 cajas no son 136 FN medidos. Hay 59 enlaces humanos tapa-envase y 77 tapas sin enlace; no hay evaluación de asociación predicha. No se midieron defectos ni seguimiento contra referencia temporal. RAYADURA y DEFORMACION permanecen NO DISPONIBLE.

Simulación anterior en botellasSinTapa.mp4: 399 fotogramas, 1.087 observaciones y 39 IDs temporales, no 39 botellas físicas. Cero llamadas al clasificador; observaciones bloqueadas por dominio/etapa no confirmados y condiciones de visibilidad. Resultado NO EVALUABLE. El nombre del archivo no confirma ausencia de tapa después del tapado. Este caso demuestra abstención, no rendimiento del clasificador.

Falta confirmar línea/SKU, etapa posterior al tapado, perfil de envase y convención de defectos; detector TAPA evaluado; asociación tapa-envase; clasificación de colocación y referencia suficiente; seguimiento y conteo sin duplicaciones. Cajas y otros envases requieren perfiles propios y evaluación específica; quedan fuera de la aceptación actual.

## 3. Arquitectura propuesta, todavía no implementada

Se recomienda evolución modular del Django existente, con ejecución experimental aislada. No se justifica introducir microservicios ni infraestructura nueva para esta demostración.

```text
Portal Django: acceso, permisos, selección de fuente y consulta de ejecuciones
                              |
                     Registro de ejecución
            fuente/hash + configuración/modelo + estado + artefactos
                     /                         \
         Adaptador EPP                       Adaptador Calidad
   PERSONA/CASCO/CHALECO                  ENVASE/TAPA según disponibilidad
    tracking y asociación                  tracking y asociación propios
    reglas por área/EPP                    perfil de línea/SKU/etapa
    candidato de seguridad                 inspección de tapa o NO_EVALUABLE
    revisión de seguridad                  revisión de calidad
                     \                         /
             Medios, evidencias y trazabilidad compartidos
```

El diagrama expresa una propuesta. Hoy hay piezas comunes, pero no un contrato único de ejecución/resultados que conecte todos los artefactos y pantallas automáticamente.

| Componente | Reutilización propuesta | Separación necesaria |
|---|---|---|
| Acceso y permisos | Django y sesiones del laboratorio | Permisos por dominio; el visor Calidad hoy utiliza permiso de consulta EPP, dependencia que conviene separar |
| Fuentes y reproducción | Alias de solo lectura, hashes, MIME y Range autenticado | No mezclar medios de laboratorio con MEDIA_ROOT operativo |
| Ejecución | Estado pendiente/procesando/completada/error; configuración congelada | Adaptadores y catálogos explícitos; no asumir salida común de modelos diferentes |
| Evidencia | Referencia a video, frame/tiempo, caja, modelo, score y hash | Score no equivale a probabilidad de cumplimiento o conformidad |
| Identidad temporal | Contrato común de ID local | IDs acotados a ejecución/video/módulo; sin identidad global entre cámaras o dominios |
| Revisión | Patrón de decisión, observaciones, autor, fecha y versión | Tipos de decisión y reglas separados; no compartir automáticamente etiquetas de ausencia |
| Métricas | Registro de alcance, denominador y referencia | Detección, asociación, tracking, evento y defecto nunca se agregan en un único porcentaje |
| Persistencia | Manifiestos/resultados versionados y almacenamiento de evidencia | Base de laboratorio aislada; sin escritura ni migraciones operativas |

Contrato mínimo futuro: execution_id, módulo y versión, source_sha256, imagen/frame/tiempo, pesos_sha256, parámetros, estado de ejecución, detecciones observadas, track_id local, asociaciones con evidencia, estado evaluable/NO_EVALUABLE y motivo, candidato/decisión humana, artefactos y referencia de evaluación. La revisión debe añadirse de forma versionada sin sobrescribir predicciones congeladas. No confundirlo con el JSON mutable de revisión que ya existe en la aplicación: es un requisito de integración propuesto.

Mantener reglas EPP dentro de seguridad y reglas de envases dentro de Calidad. La capa común transporta evidencia y estado; no deduce cumplimiento a partir de detecciones ausentes. Fuentes de cámara en vivo, control de capacidad, recuperación de trabajos y latencia quedan pendientes: las pruebas actuales usan videos locales.

## 4. Prioridades y puertas de aceptación

| Prioridad | Tarea propuesta | Evidencia de terminación |
|---|---|---|
| P0 | Congelar cierre y publicar acceso local a resultados existentes | Base/candidata distinguibles, enlaces reproducibles y parámetros visibles; originales sin cambios |
| P0 | Definir alcance de demostración | Aprobación explícita: EPP supervisado y Calidad como diagnóstico ENVASE/abstención; no prometer tapa validada |
| P0 | Preparar guion y estados visibles con herramientas existentes | Se explica cada NO_EVALUABLE, no hay conformidad por falta de detección; ejemplos técnicos claramente separados |
| P1 | Especificar contrato de ejecución y separación de permisos | Revisión de diseño y mapeo de artefactos actuales, antes de desarrollar integración |
| P1 | Resolver bloqueos de Calidad | Adjudicación de siete contradicciones y caja mínima, etapa/SKU confirmados y estrategia explícita para TAPA; no nuevas cajas masivas en esta iteración |
| P1 | Mejorar el recorrido EPP | Decisión técnica sobre omisiones y fragmentación, con detección/asociación/evento separados y revisión humana preservada |
| P2 | Implementar adaptadores comunes, tras autorizar desarrollo | Pruebas de permisos, aislamiento, contratos, reintentos y evidencias; sin fusionar motores de decisión |
| P2 | Evaluación reservada y temporal suficiente | Nuevas sesiones reservadas y revisión independiente cuando se autorice ampliar evidencia; sin reutilizar estos 33 como test independiente |
| P3 | Decidir entrenamiento específico o ampliar tipos de envase | Justificación por errores persistentes, plan de datos por sesión y aprobación separada; pesos originales conservados |

La adjudicación de referencias y la evidencia adicional son deudas para validar el producto; no se piden ni ejecutan nuevas anotaciones en este cierre. No puede eliminarse esa limitación con una integración de pantallas.

## 5. Plan de demostración integral

**Preparación, sin nuevos modelos.** Usar laboratorio Django existente (`experimentos.pilotos.settings`, SQLite y medios propios), fuentes de solo lectura y artefactos ya calculados. Confirmar arranque, cuenta local sin revelar credenciales, rutas autenticadas, reproducción y aislamiento. No reejecutar inferencia para mostrar resultados que ya existen.

**Recorrido EPP.** Abrir `/monitoreo/`, mostrar original y base/candidata de ambos videos en su galería existente; explicar umbrales, TP/FP/FN en las 33 referencias, asociación y pérdidas de ID. Aclarar que los resultados comparativos de la candidata son artefactos externos del laboratorio y su incorporación automática al reporte Django no está implementada. Mostrar cero candidatos reales; para enseñar decisiones/historial usar únicamente un fixture técnico identificado, en copia aislada y con autorización de esa preparación, nunca fabricarlo como evento del modelo.

**Recorrido Calidad.** Abrir `/calidad/` y la galería de 25 referencias. Mostrar localización ENVASE y errores/conflictos. Mostrar simulación bloqueada como abstención correcta ante evidencia insuficiente. Indicar TAPA no ejecutada como detector y defectos no disponibles; no mostrar un rechazo automático ni un resultado conforme de tapa.

**Cierre de la demostración.** Entregar enlaces a informes, métricas por alcance, pesos/configuraciones y pendientes. La demostración se acepta si los medios se reproducen, fuentes/resultados son trazables, las limitaciones son visibles y los dominios permanecen independientes. No exige ni acredita umbrales industriales de IA.

Para una demostración posterior que incluya realmente tapa correcta/ausente/mal colocada se necesitan etapa y perfil confirmados, localización/inspección disponibles, referencias semánticamente consistentes y comparación reproducible. Hoy ese recorrido no está listo. No se promete una fecha sin resolver esas dependencias.

## 6. Evidencias consultadas

- [Primera evaluación EPP](../output/experimental_pilotos/evaluacion_epp33_v002_001/INFORME_EPP33.md)
- [Auditoría EPP y configuraciones](../output/experimental_pilotos/auditoria_errores_epp33_v002_001/INFORME_AUDITORIA.md)
- [Comparación temporal final](../output/experimental_pilotos/comparacion_videos_epp_v002_001/INFORME_VIDEOS_EPP.md)
- [Galería EPP y videos comparativos](../output/experimental_pilotos/comparacion_videos_epp_v002_001/index.html)
- [Evaluación de detección Calidad](../output/experimental_pilotos/evaluacion_deteccion_v002_001/INFORME.md)
- [Galería Calidad](../output/experimental_pilotos/evaluacion_deteccion_v002_001/index.html)
- [Laboratorio y verificaciones previas](MONITOREO_LABORATORIO.md)
- [Simulaciones anteriores](RESULTADOS_PILOTOS.md)

Los documentos anteriores describen su propia etapa histórica; sus pendientes no invalidan trabajos completados después. Este cierre añade únicamente diagnóstico y propuesta, sin modificar su contenido ni activar capacidades.

Verificación de este cierre: ocho enlaces locales resueltos y 534 archivos protegidos contrastados con su manifiesto previo, sin diferencias SHA-256. Solo se añadió este documento; las pruebas de software citadas pertenecen a las evaluaciones previas y no se reejecutaron para una incorporación exclusivamente documental.
