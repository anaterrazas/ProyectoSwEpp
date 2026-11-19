# Informe técnico de inspección individual experimental

## Implementación entregada

Se creó una extensión nueva, `individual_v001`, que separa detección, seguimiento, extracción de regiones y clasificación. No se modificaron los módulos previos, datasets, registros, pesos YOLO11n de producción ni el algoritmo ByteTrack instalado. No hubo nuevo entrenamiento.

La selección se hizo **antes de integrar**: cinco configuraciones de dos familias de detección, probadas sobre siete fotogramas reales de cada video. Los resultados y cajas están en `comparison/results.json`; la decisión en `comparison/selection.json`. Se descargaron únicamente pesos oficiales preentrenados YOLO11s y Faster R-CNN dentro de esta versión. Los enlaces, hashes y referencias de licencia quedan en `weights/sources.json` y README.

YOLO11s 640 ofreció mayor cobertura visible en prueba2 (64 observaciones en siete frames; n640 21, n1280 0, s960 61, Faster R-CNN 4). No se eligió por asumir que YOLO siempre funciona: todos los métodos fallaron en detectar envases en las muestras de tapas. Ningún conteo se interpreta como precision, recall o número de envases únicos.

## Resultados comprobados

El video completo prueba2 produjo 3.769 observaciones en 406 frames, con 13 IDs temporales y 3.699 reutilizaciones consecutivas de ID. Se guardaron 26 recortes seleccionados, dos por track, y su observación con PTS, número de frame, ROI, SHA-256, estado técnico y motivos de abstención. Los IDs 1–4 aparecen en los 406 fotogramas como observaciones asociadas; ello demuestra persistencia de asignación, no una certificación de identidad contra anotaciones humanas.

El video completo tapas produjo cero detecciones en 450 frames. Se procesó y codificó por completo para mostrar la limitación, sin crear IDs, recortes o cajas ficticias. La ausencia de detección no se transforma en un resultado favorable de calidad.

En ambos videos se mantuvo la inspección global **NO EVALUABLE**. RAYADURA y DEFORMACION son NO DISPONIBLE. El clasificador experimental de tapa está conectado, pero hubo cero llamadas reales en las referencias: los recortes de prueba2 no acreditan dominio compatible y no hubo aprobación humana de ROI/etapa; tapas no aportó regiones de envases detectados. No se inventaron probabilidades ni resultados CONFORME.

La región azul superior es una **ROI candidata geométrica**, no una tapa localizada por un detector específico. Los recortes inferiores también son candidatos de cuerpo; la oclusión y las cajas parciales pueden impedir su interpretación. La validación técnica no rellena etiquetas humanas. Para más detalle, medidas y comandos, consultar README.

## Trazabilidad

- Cada entrada conserva SHA-256 y ruta del video original, sin modificar sus bytes.
- Cada fotograma conserva índice, PTS y tiempo relativo del primer PTS.
- Cada observación contiene caja original del detector, score de detección, ID temporal cuando esté confirmado y `observed_this_frame=true`.
- ByteTrack asocia observaciones. Solo se muestran aquellas actualizadas en ese frame; las predicciones Kalman sin detección no se dibujan ni se evalúan.
- El identificador compuesto es `(video_sha256, run_id, track_id)`; el ID físico permanece desconocido.
- Se preservan hashes de pesos detector/clasificador, configuración de tracker y comparación previa.
- Los PNG guardados tienen hash y coordenadas; las pruebas reproducen píxeles de recorte desde el frame fuente sin overlays.

No se añaden las observaciones repetidas a un dataset de entrenamiento ni se separan fotogramas correlacionados en particiones. No se crearon sesiones, cámaras, materiales o licencias ficticias de las referencias.

## Métricas y tiempos

Prueba2: duración estimada 13,5469 s; tiempo registrado 51,1004 s. Tapas: duración 9 s; tiempo registrado 35,6414 s. Los tiempos corresponden al procesamiento/almacenamiento indicados en README, no a duración del archivo ni rendimiento garantizado en vivo. La codificación H.264 medida tomó 6,1483 s y 2,4913 s respectivamente.

No existe anotación independiente para calcular exactitud de detección, omisiones, mAP, cambios incorrectos de ID, falsos negativos de calidad o conteo físico. Esas métricas se guardan como null. Que un track conserve un ID no garantiza que nunca se haya asociado a otra unidad; hace falta anotación de trayectorias para medirlo.

## Validación y limitaciones

Las doce pruebas nuevas pasaron, incluidas integraciones sobre los resultados reales. También pasaron las 91 pruebas del proyecto, las 33 de captura foto/video y las 11 del prototipo previo: **147 pruebas distintas aprobadas**. Django no detectó incidencias. Las pruebas de base de datos usaron SQLite en memoria y multimedia temporal, con migraciones desactivadas.

Playwright verificó la galería, 32 imágenes de evidencia y dos videos H.264 con `readyState=4`; la captura real de pantalla está en `viewer_screenshot.png`. Los fotogramas anotados originales de esta ejecución se encuentran en `runs/*/screenshots/`. Las pruebas de tracker con fixtures en memoria no se confunden con la evidencia de estos videos reales.

La comparación final SHA-256 de las once entradas protegidas (árboles de datos/código previos, SQLite, pesos originales y videos fuente) se guarda en `verification.json`. La limitación central permanece: **no hay un detector de envases adecuado para tapas.mp4 ni un clasificador de calidad validado para las regiones de prueba2**. Esta entrega demuestra la canalización y la abstención, no una inspección industrial completa.

## Cambios posteriores recomendados

1. Etiquetar cuadros y correspondencias de envases/cuello/tapa en videos reales del dominio y revisar las detecciones actuales.
2. Confirmar el punto de inspección posterior al tapado y la obligación de tapa; no juzgar como defecto una posición normal de alimentación.
3. Validar localización de tapa/cuello y visibilidad, antes de autorizar el uso del clasificador en ese dominio.
4. Medir detección y seguimiento con referencia independiente y videos completos reservados por sesión.
5. Solo después considerar un entrenamiento nuevo específico del dominio. No alterar producción ni presentar scores del detector como confianza de defecto.
