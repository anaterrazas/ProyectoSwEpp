# Dataset manual de detección de envases y tapas · v001

## Resultado de esta fase

Herramienta local funcional y dataset inicial independiente en `datasets/calidad_botellas/v002/experiments/detection_manual_v001/`. No se entrenó, no se cargaron detectores ni clasificadores, y no se copiaron cajas automáticas a anotaciones humanas. No se habilitaron predicciones de calidad. RAYADURA y DEFORMACION permanecen NO DISPONIBLE.

La interfaz está en http://127.0.0.1:8792/ mientras corre el servidor. Las instrucciones y comandos PowerShell están en `COMENZAR.md`. El único intérprete requerido es el entorno virtual existente; no se instalaron nuevas dependencias. Se reutilizó exclusivamente en lectura el validador MP4/PTS `v002/tools/video_dataset.py`, OpenCV, NumPy y ffmpeg ya disponibles.

## Inventario y cobertura inicial

| Fuente original | Resolución | Fotogramas totales del video | Fotogramas extraídos | ENVASE anotados | TAPA anotadas | Revisados |
|---|---|---:|---:|---:|---:|---:|
| pruebas_ia/prueba2.mp4 | 1920 × 1080 | 406 | 15 | 0 | 0 | 0 |
| pruebas_ia/tapas.mp4 | 1280 × 720 | 450 | 10 | 0 | 0 | 0 |
| Total | | 856 | 25 | 0 | 0 | 0 |

Extracción determinista por PTS, aproximadamente cada segundo, incluyendo el último fotograma cuando hay al menos medio intervalo desde la selección anterior. Prueba2: índices 0, 30, 60, …, 390 y 405. Tapas: 0, 50, 100, …, 400 y 449. Los extremos finales están a unos 0,50 y 0,98 segundos de la selección anterior. No se eligieron imágenes mediante predicciones ni se afirma que el muestreo temporal cubra todas las situaciones semánticas.

Los PNG son fotogramas completos decodificados sin compresión con pérdida adicional. Se mantienen videos originales en su ubicación, sin copia ni sobrescritura. Las 25 imágenes se reprodujeron desde los videos y coincidieron con sus hashes en la prueba de integración.

SHA-256 de videos:

- prueba2: `557eef7acddd10c7439ddd8fd85984d59289edee934cb38e2f0dacb9cf4ce0fb`
- tapas: `8a2b94bcf49a24212a443df0dbc7283f5fc1d3dde80cf6c16dea38bd89736a71`

El manifiesto registra ID de video derivado del hash, ruta y nombre originales, hash del MP4, índice base cero, PTS real en segundos, timestamp relativo, dimensiones, SHA del PNG, dHash y una medida técnica de nitidez. Las fechas de preparación son fechas reales de operaciones UTC; fechas de captura, autoría de los videos, sesiones, materiales y licencias no confirmadas permanecen desconocidos. No se atribuyó CC BY ni captura propia a estas fuentes sin evidencia.

## Interfaz y trazabilidad

Se puede dibujar una caja con arrastre, seleccionar su clase, moverla, redimensionarla mediante coordenadas, ampliarla al 100%/200%, cambiar atributos y eliminarla. Un objeto nuevo tiene `partial`, `occluded` y `not_evaluable` en null. ID físico y asociación TAPA → ENVASE son opcionales y humanos. No se reutilizan los trece IDs temporales previos como identidades físicas.

Cada guardado exige autor, hash esperado y versión de partida. Crea un JSON nuevo con fecha UTC y hash de la revisión previa. No se reescriben revisiones antiguas; incluso una eliminación permanece en su historia. Se puede guardar borrador y continuar después de recargar. La herramienta avisa sobre cambios sin guardar y bloquea conflictos entre versiones. Solo debe ejecutarse un servidor por dataset; no es un sistema multiusuario distribuido ni un servicio de autenticación.

Finalizar requiere exhaustividad explícita y resolver los tres atributos de cada objeto. Una imagen sin cajas exige confirmar que realmente no contiene objetos objetivo; un borrador vacío no se convierte en negativo. «Revisado» corresponde al trabajo exhaustivo del anotador, no certifica revisión independiente. La convención visible/amodal y las diferencias entre tapa, asiento de colocación y maquinaria se explican en COMENZAR.md: no se dibujan objetos ausentes ni siluetas ocultas imaginadas.

El servidor escucha solo en 127.0.0.1 y restringe Host, Origin y token de escritura. No expone el árbol de archivos: las imágenes se sirven por sample_id y su hash se comprueba. Las validaciones de ruta, caja, autor, versión y agrupación se ejecutan en el servidor, no solo en JavaScript. Los textos humanos se insertan como texto, sin interpretar HTML.

## Exportación y grupos

YOLO usa clases 0 ENVASE y 1 TAPA y coordenadas normalizadas. La etiqueta TAPA indica presencia del objeto, **no defecto de tapa**. La exportación genera una instantánea nueva con labels TXT y `traceability.json`, que conserva atributos, autor, revisiones, fuentes, hashes y particiones; no mueve imágenes ni genera carpetas de entrenamiento con copias ni ejecuta entrenamiento.

Los borradores se omiten. Un fotograma con algún objeto no evaluable se omite completo en YOLO estándar para evitar que una región ignorada se entrene como fondo. La revisión permanece íntegra en JSON. Los SHA duplicados no se exportan repetidos. Los objetos parciales u ocluidos siguen siendo exportables si una persona confirmó que su extensión visible es delimitable/evaluable y completó el resto de objetos.

| Partición | Fotogramas asignados | ENVASE revisados | TAPA revisadas |
|---|---:|---:|---:|
| train | 0 | 0 | 0 |
| validation | 0 | 0 | 0 |
| test | 0 | 0 | 0 |
| UNASSIGNED | 25 | 0 | 0 |

Todos los frames del mismo video se unen. Las sesiones compartidas, IDs físicos humanos compartidos, SHA idénticos y candidatos dHash ≤4 también unen componentes. Las sesiones desconocidas se agrupan conservadoramente entre sí; por ello actualmente existe **un único componente** con ambos videos. No se inventaron sesiones para separarlos. La asignación explícita afecta un componente completo y las nuevas anotaciones se rechazan si una identidad física produciría fuga entre particiones ya distintas.

Ambos videos ya se usaron para desarrollar y seleccionar el detector experimental. **Ninguno puede presentarse ahora como test final independiente.** Incluso con sesiones conocidas y diferentes, dos videos no bastan por sí solos para tres grupos de origen independientes. Se necesitan nuevas grabaciones y separación verificable por botellas/sesiones; no resolver esta falta sorteando fotogramas.

## Duplicados y calidad

- 0 pares SHA-256 idénticos entre las 25 imágenes.
- 0 pares candidatos con distancia dHash ≤4. Este método simple no garantiza ausencia de duplicados parciales, cambios de encuadre, rotaciones o identidad física compartida. No sustituye la revisión humana.
- 0 PNG dañados o con dimensiones inconsistentes; 25/25 hashes verificados y reproducción exacta desde el video.
- 0 imágenes por debajo de 640 × 480. Una resolución global suficiente no garantiza resolución de una tapa pequeña.
- Los 10 fotogramas de tapas tienen varianza global del Laplaciano <50, un aviso de posible suavidad/desenfoque. No se eliminan ni se consideran automáticamente no evaluables: medir la región concreta de la tapa y comprobar sus bordes durante anotación. Este umbral depende de textura y escala y no está calibrado como criterio industrial.
- 0 advertencias de cajas actualmente porque aún no hay anotaciones. No equivale a una revisión humana de corrección.

Durante anotación se detectan cajas fuera de rango, dimensiones inferiores a 2 píxeles, NaN/inf, clases/IDs inválidos, cajas idénticas, repetición del mismo ENVASE físico en el mismo fotograma, referencias TAPA → ENVASE inválidas e identidades contradictorias. El informe señala regiones menores de 16 píxeles y solapamientos de la misma clase con IoU >0,85 para revisión humana, sin borrarlas.

## Validación ejecutada

**168 pruebas distintas aprobadas:**

| Suite | Pruebas | Resultado |
|---|---:|---|
| Anotación manual nueva | 21 | OK; 4,520 s en la ejecución final |
| Captura foto/video existente | 33 | OK |
| Canalización individual anterior | 12 | OK |
| Prototipo anterior | 11 | OK |
| Proyecto Django y ML | 91 | OK |

La ejecución conjunta inicial registró 20 pruebas nuevas y 147 anteriores en `output/tests/4ef4621049eb4df5b989730b984eb03c/results.json`. Se añadió una prueba específica del export de clase 1 TAPA con asociación humana y atributos de oclusión; se reejecutó toda la suite nueva (21, exit code 0), guardada en `output/tests/manual_final.log`. El total distinto final es 21 + 147, no la suma de todas las reejecuciones.

Django check no detectó incidencias. Las pruebas Django usaron SQLite en memoria, medios temporales y migraciones desactivadas. Los fixtures de las pruebas de captura no se incorporaron al dataset real. En este sandbox Windows, TemporaryDirectory dentro del proyecto produjo inicialmente un fallo de permisos de ACL; las nuevas pruebas usan mkdir con permisos heredados. Los directorios fallidos se limpiaron y la suite final completa pasó. Un primer intento de capturar stderr mediante PowerShell Tee-Object produjo un estado de shell engañoso pese a OK; la comprobación final midió el exit code real del proceso Python: 0.

Playwright verificó en una copia temporal aislada dibujo por ratón, guardado, recarga, edición, finalización, export YOLO, eliminación conservando cuatro revisiones y rechazo de cierre incompleto. Autor de fixture explícito `QA_AUTOMATIZADA_NO_HUMANA`; esa copia se eliminó al terminar y sus cajas no son etiquetas reales. El resumen está en `output/playwright/verification.json`. Las capturas `prueba2_interface.png` y `tapas_interface.png` muestran el dataset real con cero cajas, sin anotaciones simuladas. Un 404 de favicon no afecta el flujo; el 400 de cierre incompleto fue una validación esperada.

La integridad se comparó antes/después mediante hashes agregados y recuentos de archivos en siete ámbitos protegidos: datasets existentes (excluyendo solo esta carpeta nueva), producción, configuración, ML, pruebas_ia, db.sqlite3 y pesos YOLO11n. **Sin diferencias.** Detalle en `output/integrity.json`. No se alteraron las 19 muestras, las once fotografías preauditadas ni decisiones públicas anteriores.

## Dictamen y próximo paso

**Dataset NO preparado para entrenamiento.** Actualmente hay imágenes para anotar, cero cajas humanas confirmadas, cero particiones independientes y derechos/sesiones de captura por documentar. No se midieron precisión, recall ni mAP porque aún no hay ground truth manual de detección. Tampoco se ha validado una decisión de calidad por envase.

El siguiente paso es anotar los 25 fotogramas siguiendo la convención, resolver los objetos ambiguos en tapas y hacer una revisión independiente de cajas y exhaustividad. Después comprobar cobertura real por clase, tamaño de objetos, oclusión, iluminación, tipo de recipiente y sesión. Añadir grabaciones nuevas reservadas de antemano para evaluación, con IDs físicos y procedencia conocidos; disponer de ambas clases en grupos independientes de train/validation/test. Los derechos deben quedar documentados sin presumir autoría propia. No existe una cifra universal de cajas que certifique suficiencia: la revisión debe evaluar diversidad y unidades físicas independientes, no solo observaciones repetidas.

Una futura autorización de entrenamiento requerirá una nueva evaluación de suficiencia basada en esas anotaciones, cobertura por origen y revisión humana. El export actual se mantiene siempre como no aprobado para entrenamiento; no levanta ese requisito automáticamente al alcanzar un número de cajas.
