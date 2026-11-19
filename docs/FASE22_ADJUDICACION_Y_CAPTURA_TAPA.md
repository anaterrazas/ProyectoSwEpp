# Fase 2.2 · Adjudicación y plan de captura TAPA

18/11/2026 · America/La_Paz. Continuación de la auditoría anterior, sin repetir extracción de imágenes ni mediciones. No hubo entrenamiento ni inferencia. Los originales y las evaluaciones permanecen congelados.

## Estado de adjudicación

No se encontraron revisiones nuevas en la copia del anotador preparada en Fase 2.1. Al entregar esta fase hay **0 conflictos adjudicados y 7 pendientes**. No se interpretaron notas o imágenes como decisiones humanas nuevas.

La galería con registro de decisiones está en **http://127.0.0.1:8010/demo/calidad/adjudicacion/** y se abre desde Calidad, «Adjudicar los siete conflictos». Muestra original, caja superpuesta, clase original, nota, autor y revisión de origen.

| Caso | Fuente | Frame | Clase original | Nota humana original | Estado inicial |
|---|---|---:|---|---|---|
| 1 | prueba2 | 120 | ENVASE | tapa roja | PENDIENTE |
| 2 | prueba2 | 240 | ENVASE | tapa roja | PENDIENTE |
| 3 | prueba2 | 330 | ENVASE | tapa roja suelta | PENDIENTE |
| 4 | tapas | 100 | ENVASE | tapa amarilla | PENDIENTE |
| 5 | tapas | 250 | ENVASE | tapa amarilla | PENDIENTE |
| 6 | tapas | 300 | ENVASE | tapa amarilla | PENDIENTE |
| 7 | tapas | 350 | ENVASE | tapa amarilla | PENDIENTE |

Cada formulario exige decisión explícita, autor real y justificación. Puede confirmar ENVASE, adjudicar TAPA, declarar NO EVALUABLE o mantener pendiente. Ninguna opción está preseleccionada como resolución. NO EVALUABLE conserva clase adjudicada null, no crea una clase de detección ni una tapa inexistente.

Las decisiones se anexan en `output/fase22_tapa_v002_001/decisiones/<caso>/<version>.json`, separadas de las anotaciones. Guardan clase original/adjudicada, box_id, hash y caja de revisión original, autor declarado, cuenta usada, fecha UTC, justificación, estado y hash de la versión anterior. Se controla bloqueo y versión obsoleta; no se sobrescriben decisiones. Se puede volver a pendiente mediante una nueva versión. El historial queda visible por conflicto.

Las correcciones de geometría requieren el anotador existente en la copia de trabajo (localhost:8792); se deja pendiente la adjudicación si depende de ese ajuste. No se fusionan registros ni se aplican cambios a originales automáticamente. Una decisión de clase no equivale a referencia final de entrenamiento: todavía debe revisarse coherencia con otras cajas, duplicaciones y enlaces.

La cuenta piloto tiene ahora el permiso específico `produccion.change_inspeccioncalidad` en SQLite de laboratorio para registrar decisiones; una cuenta con solo consulta puede ver pero no guardar. Autor real se pide aparte porque una cuenta compartida no identifica por sí sola al revisor. Segunda revisión independiente permanece NO_ACREDITADA; no basta cambiar el nombre declarado.

## Visibilidad de las 136 cajas, sin etiquetas nuevas

Se reutilizaron los atributos humanos de la auditoría, con grupos de prioridad explícita. Si hay un atributo desconocido se clasifica la agrupación como DUDOSA; después se prioriza NO EVALUABLE, OCLUIDA, PARCIAL y TOTALMENTE VISIBLE. El registro conserva los flags originales y cada box_id; no altera datos.

| Grupo derivado de lo anotado | Cajas | Utilidad según protocolo |
|---|---:|---|
| Totalmente visible | 1 | Candidata a detección si clase y caja son correctas; no acredita calidad de colocación |
| Parcial sin oclusión marcada | 127 | Aprovechable si el objeto TAPA es reconocible y se delimita su extensión visible |
| Ocluida | 8 | No descartar automáticamente; aprovechar la parte visible reconocible y conservar atributo |
| No evaluable | 0 marcadas | Si la revisión concluye que no se reconoce el objeto, usar región ignorada o exclusión según exportador, nunca fondo automático |
| Dudosa por atributos desconocidos | 0 | Cero desconocidos no significa cero dudas semánticas; los casos dudosos que surjan deben quedar pendientes |

Las 8 ocluidas también son parciales: por eso el conteo original partial=true es 135, mientras el grupo parcial exclusivo es 127. No sumar categorías solapadas como observaciones adicionales.

Hay 11 avisos de posible desenfoque en tapas.mp4. No cambian automáticamente la evaluabilidad humana. Revisar primero esos 11 casos y ejemplos representativos de la convención partial, porque 135/136 están marcados parciales. Si una caja es realmente visible completa pero el flag representa otro concepto, la corrección debe ser humana en una copia/versionado, no una normalización silenciosa.

**Protocolo de caja:** TAPA es el objeto físico visible, colocado o suelto; no se reconstruye la forma oculta ni se incluye el cuello como tapa. Marcar parcial/oclusión según extensión visible y causa. Una boca vacía no se anota TAPA. Si el objeto no es reconocible, no inventar caja. Un enlace a ENVASE no significa TAPA_CORRECTA, y no tener enlace no significa tapa suelta.

Esta entrega no representa una segunda adjudicación visual independiente de las 136 cajas: conserva y organiza lo ya revisado. Los grupos e IDs están en `output/fase22_tapa_v002_001/visibilidad_referencias.json`.

## Plan concreto de captura: mínimo operativo propuesto

Este es un objetivo inicial de planificación, no un umbral de suficiencia estadística ni autorización automática para entrenar. Debe confirmarse la línea/SKU y la estación con el responsable antes de capturar.

**Primer lote propuesto:** 9 sesiones reales identificadas, repartidas inicialmente 5 para train, 2 validation y 2 test. Un clip o varios por sesión, preservando siempre la agrupación. Seleccionar inicialmente 20–40 imágenes con información distinta por sesión: 180–360 imágenes como objetivo de trabajo, sin rellenar cuotas con frames casi iguales. Si el presupuesto no lo permite, reducir el alcance declarado; no declarar independencia que no existe.

No son sesiones ya capturadas ni identidades oficiales. Los espacios propuestos están en `plan_sesiones_propuesto.csv`. Se reservan antes de seleccionar frames y no se rellenan metadatos desconocidos. Si se detectan objetos físicos compartidos, similitud o procedencia común entre bloques, reagruparlos y conseguir sesiones adicionales.

| Cobertura necesaria | Qué capturar | Qué registrar/anotar |
|---|---|---|
| Tapa colocada correctamente | Envase después del tapado, cuello visible; frontal y oblicua | TAPA física y ENVASE; colocación confirmada por responsable, separada de la etiqueta de detección |
| Mal colocada | Ejemplos confirmados de inclinación, descentrado o colocación incompleta | Geometría visible, criterio de defecto aprobado y duda si no basta la imagen; no deducir solo por perspectiva |
| Suelta | Tapas interior/exterior, al lado de envases y aisladas | TAPA independiente; condición suelta y propietario desconocido cuando corresponda |
| Ausencia posterior al tapado | Cuello identificable en etapa confirmada, con obligación de tapa documentada | Estado de ausencia por envase/intervalo; ninguna caja TAPA sobre la boca vacía |
| Colores y tamaños | Variantes reales del dominio y tapas más pequeñas/lejos | SKU/tipo/color/tamaño cuando se conozcan; cubrir escala <16, 16–32 y >32 px al tamaño de entrada |
| Perspectivas | Frontal, lateral, oblicua y superior cuando existan en la vista de trabajo | Vista/cámara, condiciones de visibilidad; no mezclar tipos de escena como si fueran misma cobertura |
| Oclusión | Asas, otros envases, manos o elementos de máquina presentes en captura | Parte visible y oclusión; enlace solo si hay evidencia |
| Desenfoque y reflejos | Movimiento real, cambios de foco y brillo dentro del dominio | Dificultad/evaluabilidad; regiones ilegibles no son negativos |
| Confusores | Asas, anillos de seguridad, cuellos, piezas amarillas y reflejos | Exhaustividad humana de TAPA y regiones ignoradas; no convertir omisiones de anotación en fondo |

Cada bloque debe tener positivos TAPA y escenas negativas realmente revisadas. Para comparar por condición, validation y test deben incluir evidencia adjudicada de esa condición en más de una sesión; si falta, no reportar rendimiento para ella. No inferir ausencia de tapa por el nombre de un archivo, una nota sin etapa o una detección faltante.

## Metadatos mínimos por nueva captura

- Archivo original y SHA-256; duración/FPS/PTS; fecha de captura real y session_id proporcionado por quien captura.
- Línea/SKU, cámara/vista, estación y alcance del dominio; autor responsable de metadatos.
- Permiso/procedencia y derechos de uso confirmados. No reemplazar los null actuales por supuestos.
- Para ausencia: etapa posterior al tapado confirmada, tapa requerida y evidencia visible con timestamps; si falta algo, NO EVALUABLE.
- Identidad física cuando pueda acreditarse y relación con otras capturas; los IDs de ByteTrack no sirven como identidad humana de referencia.
- Revisor, versión de anotación, protocolo, estado de exhaustividad y regiones ignoradas.

Se incluye una plantilla vacía en `plantilla_captura.json`, con todos los datos no conocidos en null y estado NO_CAPTURADA. No se usa como manifiesto de datos reales.

## Propuesta de distribución y uso de los datos actuales

Los dos videos actuales continúan como un componente conocido UNASSIGNED, útil para desarrollo/adjudicación. No se reparten sus 25 frames entre entrenamiento y prueba ni se presentan como test independiente después de ajustar. Los 136 objetos anotados son observaciones repetidas, sin identidades físicas acreditadas.

La propuesta 5/2/2 se aplica a grupos de nuevas sesiones, no a porcentajes de frames. Clips de una misma sesión permanecen juntos. Si sesiones distintas comparten objeto físico relevante o procedencia/similitud que impida independencia, forman un solo componente. Las particiones se congelan mediante manifiestos con hashes antes de ajustar modelo o umbral.

El primer detector tendrá una clase física TAPA y usará ENVASE del baseline congelado. Las condiciones colocada/suelta y estados de defecto son metadatos de análisis o futuras tareas: no crear una clase localizada TAPA_AUSENTE. Preservar las tapas parciales/ocluidas útiles y tratar desconocidos con soporte de regiones ignoradas; no exportarlos como fondo silenciosamente.

## Criterios para autorizar entrenamiento

1. Los siete conflictos están adjudicados por humanos o excluidos/ignorados explícitamente en la referencia de trabajo, con motivo y trazabilidad; una nota no basta como resolución.
2. Convención de TAPA, visibilidad y cajas aplicada de forma consistente; revisión prioritaria de los 11 avisos y de flags partial representativos. Casos dudosos pendientes no se usan como negativos.
3. Capturas con procedencia/derechos y sesiones identificadas; particiones por componentes verificadas, sin fuga entre train/validation/test. Validation/test tienen positivos y negativos revisados y cobertura de condiciones que se pretenda evaluar.
4. Hashes, clases, coordenadas, vínculos y regiones ignoradas pasan validación automática; referencia congelada con versiones y revisores. Exportador compatible con ignoradas o exclusiones explícitas por frame.
5. Segunda revisión independiente de la referencia reservada, sin predicciones anteriores como verdad. El criterio de aceptación y el alcance del piloto se acuerdan antes de mirar el test.
6. Plan de ejecución aprobado: inicialización local, pesos nuevos separados, semilla/configuración/versiones y presupuesto fijados; confianza/NMS elegidos en validación; test reservado sin ajuste posterior.
7. Autorización explícita para iniciar el entrenamiento tras presentar el cumplimiento de estas puertas. El lote propuesto de imágenes no sustituye esta revisión.

La evaluación separará detección TAPA, asociación tapa-envase, seguimiento y clasificación de defectos. Medirá TP/FP/FN e IoU ≥0,50 por clase/sesión y PR/AP cuando sea calculable. No declarar precisión industrial ni agregar resultados EPP. Rayadura y deformación siguen fuera de disponibilidad.

## Verificación y cambios realizados

57 pruebas automatizadas aprobaron. Nueve nuevas prueban el registro de adjudicación con fixtures temporales: autenticación y permisos, CSRF, guardado HTTP, datos obligatorios, versión obsoleta, historial preservado, escape de texto, NO EVALUABLE sin clase y acceso limitado a imágenes. No se guardó ninguna decisión humana real en estas pruebas.

Chrome confirmó siete casos, 14 imágenes sin errores, siete formularios con CSRF y sin decisiones preseleccionadas. Diseño móvil a 390 px sin desbordamiento; inicio, EPP, Calidad e historial continúan respondiendo. Evidencia en `output/fase22_tapa_v002_001/verificacion_chrome.json` y capturas PNG.

Archivos nuevos: `experimentos/pilotos/adjudicacion_tapa.py`, `test_adjudicacion_tapa.py`, `templates/demo/adjudicacion_tapa.html`, este documento y artefactos de fase22. Cambios de laboratorio: rutas nuevas en `urls.py`, enlace exclusivo de Calidad en `portal.py` e inicializador de la cuenta local con permiso de revisión de Calidad. No se modifica ningún motor, vista o plantilla de EPP ni código operativo de producción.

Las decisiones son otra fuente: no se han aplicado a la copia del anotador, al dataset original ni a evaluaciones anteriores. El informe de estado de adjudicación en output es una instantánea de entrega; la página muestra el estado actual tras cada guardado humano. No se entrenó, ejecutó inferencia ni modificó SQLite operativo, pesos, videos o referencias originales.
