# Inspección individual experimental EPP v002

## Resultado y límites

Se compararon detectores reales antes de integrar la canalización. El resultado es **parcial y verificable**:

- `prueba2.mp4`: detecciones de envases, asociación temporal con ByteTrack y recortes individuales candidatos de cuerpo y tapa/cuello.
- `tapas.mp4`: el detector elegido no encontró envases en sus 450 fotogramas. Se entrega el video procesado con «SIN ENVASES DETECTADOS — NO EVALUABLE», sin cajas, IDs o recortes inventados.
- El clasificador de tapa está conectado detrás de un control conservador. **No se ejecutó en los videos de referencia**, porque las regiones no acreditan compatibilidad con el entrenamiento, o no existen detecciones a las que asociarlas.
- RAYADURA y DEFORMACION permanecen NO DISPONIBLE. Ningún resultado global es CONFORME.

No se entrenó ningún modelo nuevo ni se modificaron producción, SQLite, ByteTrack, YOLO11n original o datasets anteriores. Se descargaron pesos oficiales preentrenados para comparación, solo dentro de esta carpeta.

## Ver resultados

La galería está en `index.html`. Para servirla localmente desde la raíz del proyecto:

```powershell
& .\venv\Scripts\python.exe -B -m http.server 8791 --bind 127.0.0.1 `
  --directory datasets/calidad_botellas/v002/experiments/individual_v001
```

Abrir `http://127.0.0.1:8791`. Si ya está activo, utilizar esa instancia. La galería contiene videos H.264, capturas, resultados por ID y los recortes reales guardados con su SHA-256. Es un visor de evidencia ya procesada; no agrega cargas a datasets ni entrena modelos.

Archivos principales:

```text
comparison/results.json                 70 resultados: 5 configuraciones × 7 frames × 2 videos
comparison/selection.json               elección previa a integración
comparison/gallery.html                 cajas reales de todas las alternativas
weights/sources.json                    fuentes oficiales y hashes de pesos
runs/prueba2_v001/processed.mp4          406 fotogramas con detecciones e IDs
runs/tapas_v001/processed.mp4            450 fotogramas, sin detecciones inventadas
runs/*/frames.jsonl                     observaciones, PTS y evaluación por objeto/fotograma
runs/*/report.json                      métricas y resúmenes independientes por track
runs/*/crops/track_*/                    body.png, cap_neck_candidate.png y observation.json
runs/*/screenshots/                     fotogramas anotados reales
quality_gate.py                         controles técnicos y compatibilidad
pipeline.py                             canalización experimental
templates/domain_approval.template.json plantilla informativa, no una aprobación real
INFORME_TECNICO.md                       diagnóstico, decisiones y resultados completos
```

## Comparación previa de detectores

Umbral de detección fijo 0,30; siete fotogramas uniformemente espaciados por video. Los tiempos excluyen una llamada de calentamiento por modelo. Se compararon [YOLO11n y YOLO11s](https://docs.ultralytics.com/models/yolo11/) y una familia distinta, [Faster R-CNN MobileNetV3 de Torchvision](https://docs.pytorch.org/vision/stable/models/faster_rcnn).

| Configuración | Observaciones prueba2 | Frames con detección / 7 | Observaciones tapas | s/frame prueba2 |
|---|---:|---:|---:|---:|
| YOLO11n 640 | 21 | 7 | 0 | 0,0306 |
| YOLO11n 1280 | 0 | 0 | 0 | 0,0936 |
| YOLO11s 640 | 64 | 7 | 0 | 0,0660 |
| YOLO11s 960 | 61 | 7 | 0 | 0,1235 |
| Faster R-CNN MobileNetV3 320 | 4 | 2 | 0 | 0,1049 |

Se eligió YOLO11s 640 por la cobertura visible en estos fotogramas y sus cajas alineadas con envases en la revisión visual. **Más cajas no equivale a mayor precisión**, y esa elección no certifica detección confiable de todos los envases. No hay bounding boxes de referencia independientes para medir precision, recall o mAP. Las predicciones reales, incluidas las parciales, se conservan para revisión, sin dibujar cajas manuales como si fueran salidas de los modelos.

Los pesos n originales se leen sin modificarse. Los pesos s se obtuvieron del repositorio oficial Ultralytics; Faster R-CNN de `download.pytorch.org`. Sus URL y SHA-256 están en `weights/sources.json`. Las condiciones de Ultralytics incluyen AGPL/Enterprise; este experimento no convierte los pesos en material con una licencia nueva ni autoriza un despliegue comercial sin revisar las condiciones aplicables.

## Flujo implementado

1. Validar el MP4 y leer los PTS originales mediante la herramienta existente de v002.
2. Ejecutar el detector elegido en **cada fotograma**, sin saltos de seguimiento.
3. Pasar observaciones a ByteTrack, con la implementación y configuración instaladas sin modificar.
4. Dibujar únicamente cajas de detecciones actuales. No dibujar posiciones Kalman sin observación. Una observación todavía sin ID confirmado se muestra como tal, no como una trayectoria ficticia.
5. Derivar candidatos de cuerpo (zona inferior) y tapa/cuello (zona superior) de cada caja observada.
6. Medir tamaño, enfoque, exposición, corte por borde y riesgo de solapamiento. Son alertas técnicas, no etiquetas humanas ni una prueba semántica de visibilidad.
7. Evaluar el veto de dominio y las confirmaciones humanas requeridas antes de llamar al clasificador de tapa.
8. Guardar un par de recortes seleccionados por calidad para cada track confirmado, en PNG sin pérdida, con la observación que los originó. Los demás fotogramas conservan coordenadas y métricas en JSONL, sin multiplicar el dataset con miles de imágenes correlacionadas.

Verde: detección observada con ID temporal. Naranja: detección observada pendiente de confirmar ID. Azul: región geométrica candidata, **no detección independiente de tapa**. Los scores dibujados son del detector de objetos, no probabilidades de defecto.

El ID es temporal y se identifica por `(video_sha256, run_id, track_id)`; no es el identificador de una botella física ni se reutiliza como verdad de identidad entre videos. Puede fragmentarse durante pérdidas u oclusiones. Los fotogramas repetidos y observaciones de una misma trayectoria no son unidades físicas independientes.

## Recortes y compatibilidad del clasificador

La división 38 % superior / 62 % inferior solo propone regiones. Puede incluir asas, hombros, otro envase o una parte cortada; **no acredita dónde empieza la tapa real**. La visibilidad queda UNVERIFIED incluso al superar los controles técnicos. Una detección de envase no autoriza a concluir que su tapa es evaluable.

El clasificador anterior se entrenó sobre primeros planos mayormente de tapas blancas con fondo oscuro, con solo 18 imágenes train y un resultado de prueba débil. Se mantienen sus pesos intactos. Para activarlo se requieren simultáneamente:

- Región con tamaño, nitidez, exposición y bordes aceptables, sin asociación ambigua detectada por los controles.
- Apariencia no rechazada por una comparación con las 18 imágenes de entrenamiento, sin usar el test para fijar el veto.
- Confirmación humana explícita, vinculada al SHA-256 del video: escena compatible, asignación de ROI tapa/cuello revisada, etapa posterior al tapado verificada y tapa obligatoria.

El perfil de apariencia es una heurística de veto no calibrada: **superarlo por sí solo no prueba compatibilidad**. Los umbrales técnicos tampoco certifican evaluabilidad. La plantilla no se rellena automáticamente ni se deben marcar confirmaciones para hacer aparecer predicciones. Si no hay aprobación o la apariencia falla, score y predicción de tapa permanecen null.

En prueba2, las 3.769 regiones candidatas quedaron fuera de la referencia de apariencia y sin aprobación humana; además hubo 499 alertas de borde, 261 de solapamiento y 26 de resolución insuficiente. En tapas no hubo regiones asociadas a envases. Por tanto hubo **cero llamadas reales al clasificador en ambos videos**. El ensayo unitario de la ruta permitida se realizó con una imagen real del entrenamiento y una aprobación de fixture solo en memoria; no es una evaluación exitosa de los videos nuevos.

Aunque una futura región pase el gate y produzca un score real de tapa, la inspección global seguirá NO EVALUABLE mientras los modelos de cuerpo falten. No se declara CONFORME a partir de un score bajo ni se trata «tapa no detectada» como «tapa ausente».

## Métricas completas de las referencias

| Medición | prueba2 | tapas |
|---|---:|---:|
| Fotogramas procesados | 406 | 450 |
| FPS nominales de entrada | 29,9700 | 50 |
| Duración estimada del video | 13,5469 s | 9,0000 s |
| Observaciones de cajas reales | 3.769 | 0 |
| Frames con múltiples detecciones | 406 | 0 |
| Frames sin detección | 0 | 450 |
| IDs temporales confirmados | 13 | 0 |
| Observaciones con ID confirmado | 3.759 | 0 |
| Reutilizaciones de ID en frames consecutivos | 3.699 | 0 |
| Recortes guardados (dos por track) | 26 | 0 |
| Llamadas al clasificador de tapa | 0 | 0 |
| Tiempo de procesamiento registrado | 51,1004 s | 35,6414 s |
| Tiempo acumulado de llamadas al detector | 25,9642 s | 29,2500 s |
| Codificación final H.264 | 6,1483 s | 2,4913 s |

Son mediciones de ejecución en CPU, no desempeño en tiempo real. `processing_seconds` mide desde el comienzo del bucle hasta codificación, escritura de recortes y verificación final; excluye la carga inicial de modelos y el preescaneo de metadatos. La duración del video es un campo separado. La duración estimada suma al último PTS relativo un intervalo nominal; en VFR no debe confundirse con una duración exacta del contenedor. El video visual usa FPS nominal y los PTS originales permanecen en JSONL.

Precision, recall, mAP, errores de identidad y exactitud de calidad se mantienen **no disponibles**: no hay verdad de referencia independiente en estos videos. Las 3.699 reutilizaciones muestran continuidad de IDs asignados, no 3.699 asociaciones verificadas como correctas. Los trece IDs no demuestran trece unidades físicas.

## Ejecutar otra prueba sin sobrescribir

Desde la raíz, emplear nombres de salida nuevos:

```powershell
& .\venv\Scripts\python.exe -B datasets/calidad_botellas/v002/experiments/individual_v001/pipeline.py `
  --input pruebas_ia/prueba2.mp4 `
  --output datasets/calidad_botellas/v002/experiments/individual_v001/runs/prueba2_v002

& .\venv\Scripts\python.exe -B datasets/calidad_botellas/v002/experiments/individual_v001/pipeline.py `
  --input pruebas_ia/tapas.mp4 `
  --output datasets/calidad_botellas/v002/experiments/individual_v001/runs/tapas_v002
```

El detector por defecto es el seleccionado tras comparar. `--detector` solo permite integrar nombres presentes en esa comparación. `--approval` admite un JSON real de revisión de dominio; **no se proporcionó uno para estas referencias**, por lo que no debe inventarse. Las salidas se limitan a `individual_v001/runs/` y no se sobrescriben. No ejecutar `compare.py` o `build_viewer.py` encima de sus evidencias ya existentes; una nueva comparación requiere versión nueva.

## Pruebas

```powershell
& .\venv\Scripts\python.exe -B datasets/calidad_botellas/v002/experiments/individual_v001/test_individual.py
```

Las doce pruebas nuevas cubren datos reales persistidos de comparación, PTS, observaciones actuales, ausencia de cajas predichas sin detección, IDs, reproducción de recortes contra el video, hashes, abstención del clasificador y decodificación de los MP4. Las pruebas unitarias de asociación usan fixtures únicamente en memoria; no se exportan al video ni se presentan como resultados reales.

También se ejecutan las regresiones de captura, el prototipo anterior y las 91 pruebas del proyecto, con SQLite en memoria y medios temporales. Los resultados finales, capturas de navegador e integridad se documentan en `verification.json` e `INFORME_TECNICO.md`.

## Próximo paso

Para `tapas.mp4` se necesita una vista donde los envases/cuello sean observables y/o un detector específico validado con cajas reales de ese dominio. Segmentar amarillo puede proponer tapas, pero no demuestra dónde está cada envase ni su relación de montaje, y no se implementó como sustituto ficticio de un detector de envases. Antes de otro entrenamiento, anotar cajas y correspondencias reales, etapa de inspección y recortes evaluables; reservar videos/sesiones completos para prueba. Para prueba2, revisar exhaustivamente omisiones, duplicados y continuidad de IDs antes de declarar confiable el detector.
