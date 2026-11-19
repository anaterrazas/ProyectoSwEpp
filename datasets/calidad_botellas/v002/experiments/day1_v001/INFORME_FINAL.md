# Informe final — prototipo experimental de un día

Fecha local de preparación: 16/11/2026, America/La_Paz. Esta fecha no se atribuye a la captura de fotografías antiguas.

## Dictamen

Se entregó una canalización funcional y verificable de preparación, ajuste experimental e inferencia mediante fotografía y MP4, exclusivamente en `v002/experiments/day1_v001/`. **Solo se entrenó TAPA_DEFECTUOSA.** El resultado no supera en exactitud un baseline trivial y no habilita rechazo automático, conformidad global ni generalización a todos los materiales y formatos.

No se entrenó rayadura o deformación porque faltan negativos humanos válidos y una evaluación suficiente. La demostración declara esas clases como no disponibles, con score y predicción null. No utiliza la ausencia de una anotación para generar ceros.

## Auditoría de fuentes y uso legítimo

Se comprobaron nuevamente los SHA-256 de 8.477 imágenes públicas, 19 recortes anteriores y las 11 imágenes originales del ZIP propio; se inspeccionaron individualmente y conservaron los hashes de las 15 nuevas capturas de pantalla. Los recuentos y atribuciones se guardaron en `inspection/source_audit.json` y los archivos de exclusión.

| Fuente / capa | Imágenes | Decisión para este ensayo |
|---|---:|---|
| Mendeley champú v1 | 7.907 | Licencia acreditada; positivos parciales de cuerpo, sin negativos humanos suficientes. No entrenar RAYADURA/DEFORMACION hoy |
| Roboflow caps v26 | 570 | Fuente acreditada; usar únicamente las 50 imágenes con decisión humana de tapa conocida |
| Revisión humana de 100 | 100, ya incluidas en las públicas | Capa de etiquetas, no sumar como fotografías adicionales |
| Nueve decisiones parcialmente revisadas | Subconjunto de esas 100 | No promover encuadre o adhesión a etiquetas confirmadas |
| Fotos propias de fotos.zip | 11 / 4 envases físicos | Preimportación, metadatos incompletos y negativos PET sin evaluabilidad. No usarlas para entrenar ni como prueba confirmada |
| Muestras propias v001 | 19 / 8 tracks / 1 ejecución | Última revisión REVIEWED y NO_EVALUABLE global en las 19. Mantener separadas; no tienen positivos para evaluar defectos EPP |
| botellas (2).zip | 15 | Todas excluidas de entrenamiento y evaluación por procedencia/licencia y anotación no acreditadas |

Se verificó también en las páginas de publicación que [Mendeley v1](https://data.mendeley.com/datasets/kthmmbsh8t/1) y [Roboflow v26](https://universe.roboflow.com/product-defect-detection/bottle-defects-o4gnx/dataset/26) indican CC BY 4.0. Se conserva atribución a Fakhra Aftab/Majida Kazmi y Product Defect Detection, respectivamente, con URL y licencia en cada referencia usada. No se descargaron pesos ni imágenes adicionales de internet. No se atribuye una licencia a las capturas desconocidas por estar incluidas en un ZIP.

La normalización RGB, padding y reducción a 96×96 son transformaciones experimentales en memoria, documentadas en `model.py`; los originales no se alteran. El dataset experimental referencia los bytes originales en lugar de generar copias que se cuenten como fotografías nuevas. No se afirma una licencia nueva sobre el modelo ni se publican fuera del equipo imágenes de procedencia desconocida.

## Inspección individual de las quince imágenes adicionales

La correspondencia exacta entre ID, nombre completo del archivo del ZIP y SHA-256 está en `inspection/additional_inventory.json`; la galería es `inspection/additional_review.html`. Todas mantienen las tres etiquetas en null.

| ID | Observación visual | Motivo adicional de exclusión |
|---|---|---|
| ZIP15-01 | Imagen de producto sobre fondo azul | No hay autor/licencia acreditados; no inferir conformidad |
| ZIP15-02 | Marca Getty Images, crédito CostinT | Derechos no acreditados |
| ZIP15-03 | Marca Getty Images, crédito TokenPhoto; tapa separada | Derechos y etapa de tapado desconocidos |
| ZIP15-04 | Marca Getty Images, crédito ALEAIMAGE; icono de interfaz | Derechos no acreditados y superposición de captura |
| ZIP15-05 | Botella etiquetada; 139×346 px | Origen desconocido y poco detalle |
| ZIP15-06 | Imagen de producto; 144×424 px | Origen desconocido y poco detalle |
| ZIP15-07 | Envase fuertemente aplastado | No se conoce si es posconsumo, manipulación o rechazo de fabricación |
| ZIP15-08 | Envase aplastado; 165×328 px | Causa desconocida y detalle reducido |
| ZIP15-09 | Envase aplastado con tapa separada | No acredita defecto de fabricación ni obligación de tapa |
| ZIP15-10 | Envase aplastado horizontal; 286×163 px | Causa desconocida y detalle reducido |
| ZIP15-11 | Envase aplastado y marca tenue aparente | No se identifica con certeza el banco/autor; no se inventa atribución |
| ZIP15-12 | Envase aplastado con reflejo de estudio | Origen y licencia desconocidos |
| ZIP15-13 | Envase aplastado sobre fondo de colores | Causa y procedencia desconocidas |
| ZIP15-14 | Imagen pequeña de producto sin tapa | No se conoce la etapa; no inferir TAPA_DEFECTUOSA |
| ZIP15-15 | Recipiente grande de presentación comercial | Origen, derechos y etiquetas desconocidos |

No se eliminaron marcas de agua ni se recortaron para eludirlas. No se convirtieron los envases aplastados en ejemplos positivos de DEFORMACION industrial. Hay 15 hashes distintos y ningún duplicado exacto con imágenes públicas, v001 o las 11 propias. El análisis perceptual es solo de candidatos por pHash/dHash, con resultados en `visual_candidates_additional.json`; no prueba identidad física ni crea etiquetas. La auditoría visual anterior de las públicas conserva su evidencia de 571 grupos, revalidada mediante los hashes actuales; no se ejecutó otra búsqueda exhaustiva sobre los millones de pares posibles.

## Agrupación propia corregida

Se utilizó y verificó el manifiesto corregido existente: BOT-001 tiene cinco fotografías (incluye la antigua BOT-003); BOT-002 dos, BOT-004 dos y BOT-005 dos. **Son cuatro envases físicos, no cinco ni once.** La vista 9168 conserva etiquetas desconocidas: pertenecer a la misma botella no copia defectos entre fotografías.

No se crearon sesiones, fechas, cámaras, UUID físicos definitivos ni registros oficiales de esas fotos. La falta de metadatos no se corrigió inventando una sesión común. El nuevo UUID de una carga de demostración identifica un trabajo informático, no una botella física ni una captura autenticada.

## Cobertura de las clases

Etiquetas fuente parciales de las 8.477 públicas:

| Clase | Positivos fuente | Negativos confirmados | Desconocidos |
|---|---:|---:|---:|
| RAYADURA | 2.572 | 0 | 5.905 |
| DEFORMACION | 2.388 | 0 | 6.089 |
| TAPA_DEFECTUOSA | 171 | 0 | 8.306 |

Capa humana de 100, que no se suma a las imágenes anteriores:

| Clase | Positivos humanos | Negativos humanos | Desconocidos |
|---|---:|---:|---:|
| RAYADURA | 16 | 0 | 84 |
| DEFORMACION | 16 | 0 | 84 |
| TAPA_DEFECTUOSA | 36 | 14 | 50 |

Los 19 recortes v001 conservan siete negativos parciales humanos de tapa y doce desconocidos; rayadura y deformación son desconocidas en los 19. Esos negativos parciales pueden coexistir con NO_EVALUABLE global, pero no aportan positivos ni un test completo. Se mantuvieron fuera del ensayo público congelado; no se presentan como una evaluación de precisión/recall de EPP.

Los cuatro positivos preliminares de rayadura/deformación del envase blanco y los dos ceros preliminares PET se conservan como estaban en su fuente, no se elevan a revisión independiente. El validador oficial exige evaluabilidad de región para esos ceros y metadatos de captura que siguen faltando.

Conclusión por clase: TAPA_DEFECTUOSA permite un **ensayo técnico mínimo** con ambos valores humanos conocidos y grupos separados. RAYADURA y DEFORMACION quedan pendientes. Los criterios mínimos de ingeniería (al menos diez imágenes y cinco de cada valor en train/test) se fijaron antes del ajuste y no son una garantía estadística de cobertura industrial.

## Dataset experimental y separación de evaluación

Los manifiestos `dataset/manifest.jsonl`, `train_manifest.jsonl`, `validation_manifest.jsonl` y `test_manifest.jsonl` conservan ID, imagen, SHA-256, fuente, creadores, licencia, clase conocida, componente y partición. El SHA-256 de la decisión humana y del manifiesto quedan registrados.

| Partición | Imágenes | Tapa positiva | Tapa negativa | Grupos de origen |
|---|---:|---:|---:|---:|
| train | 18 | 11 | 7 | 1 |
| validation | 15 | 15 | 0 | 2 |
| test | 17 | 10 | 7 | 1 |

Se respetaron los componentes y particiones propuestos previamente; no se separaron vistas para equilibrar números ni se copiaron fotografías entre carpetas. Los hashes son únicos y no hay componentes compartidos entre train/validation/test. Las etiquetas de cuerpo permanecen null en las 50 filas.

**Límite de independencia:** hay separación de origen respecto al entrenamiento, pero el test solo contiene un grupo, no demuestra que las 17 imágenes sean 17 unidades físicas independientes y ya estuvo expuesto a revisión humana histórica. Se preparó un test reservado frente al ajuste actual, **no un nuevo test EPP ciego**. Este último sigue pendiente y no se simula con fotogramas repetidos. No se usaron videos de prueba para optimizar el modelo.

## Modelo y mediciones reales

TinyCapCNN se ajustó desde cero en CPU, sin descargar pesos, con semilla 20261116, entrada RGB 96×96 con padding, 120 épocas fijas y Adam lr=0,003. BCE ponderada únicamente con proporciones de entrenamiento; umbral fijado en 0,5. No se eligió checkpoint ni se ajustó umbral con validación/test. El dataset completo se carga para inferencia posterior, pero los gradientes y ponderaciones usan solo los 18 ejemplos train; no hay normalización aprendida desde test.

El ajuste medido tardó 2,949 s. Se guardaron pesos, historia de pérdida, configuración y predicciones individuales. No se reentrenó al observar sus fallos.

| Métrica | Train | Validation | Test |
|---|---:|---:|---:|
| Imágenes | 18 | 15 | 17 |
| TP / TN / FP / FN | 11 / 7 / 0 / 0 | 13 / 0 / 0 / 2 | 7 / 3 / 4 / 3 |
| Exactitud | 100,00 % | 86,67 % | 58,82 % |
| Precisión positiva | 100,00 % | 100,00 %* | 63,64 % |
| Recall | 100,00 % | 86,67 % | 70,00 % |
| F1 | 100,00 % | 92,86 % | 66,67 % |
| Especificidad | 100,00 % | No calculable | 42,86 % |
| Tasa de falsos negativos | 0 % | 13,33 % | 30,00 % |

\*La precisión aparente de validación no acredita discriminar negativos: esa partición no tiene ninguno. No permite calibrar especificidad ni escoger un umbral completo.

El baseline mayoritario en test obtiene también 58,82 % de exactitud. **El modelo no lo supera en esa métrica** y produce cuatro falsas alarmas y tres omisiones. La discrepancia con el entrenamiento perfecto es compatible con sobreajuste y cambio de dominio. Las métricas son por imagen correlacionada; no se calculan intervalos de confianza fingiendo independencia ni se declaran rendimiento industrial, mAP, precisión de localización o desempeño de rayadura/deformación.

El modelo no produce cajas, no localiza defectos y no hace seguimiento. Es un clasificador binario de escena cercana de tapa; no fue validado sobre cualquier material, tipo de envase, luz o velocidad. `inspection/test_predictions.html` muestra los 17 resultados, incluidos todos los errores.

## Demostración verificada

Se implementó una aplicación local para cargar JPEG/PNG o MP4, seleccionar una ROI fija o confirmar escena completa, ejecutar el modelo de tapa y descargar predicciones JSON. Las otras dos clases muestran «Sin modelo entrenado. Predicción no disponible». Una respuesta con modelo ausente deja también tapa en null, no genera etiquetas simuladas.

Se procesó el MP4 real existente sin modificarlo: 434 fotogramas, hash de entrada conservado. La ejecución CLI produjo `runs/reference_demo/result.mp4` y `report.json` en 11,267 s; el recorrido por navegador produjo otro resultado completo en 9,217 s. Son tiempos medidos de esas ejecuciones, que incluyen validación y codificación; no una promesa de latencia ni tiempo real. No hay anotaciones de calidad del video para medir su exactitud.

Playwright comprobó carga de MP4, exigencia de ROI/escena, procesamiento de los 434 fotogramas, enlace de trazabilidad y reproducción del H.264 en Chrome (`readyState=4`). Se cargó también la primera imagen del test según su orden del manifiesto y se obtuvo una inferencia real. La captura está en `inspection/demo_browser.png`. La selección de esa imagen no cambió entrenamiento ni umbral.

El video de presentación usa FPS nominal; el JSON conserva los PTS originales por fotograma, por lo que una visualización VFR no debe usarse para medir exposición física. Una ROI es fija y humana, no una detección de envase; en una línea con varios envases no se ha implementado seguimiento ni asignación de defectos a unidades. Una predicción cero no declara conformidad global.

## Pruebas, integridad y límites operativos

Se aprobaron 91 pruebas del proyecto y 33 pruebas existentes de captura foto/video, junto con 11 pruebas específicas del prototipo. La suite inicial tuvo un cierre de conexión HTTP WinError 10053: la prueba pasó aislada y la suite completa repetida terminó con 91/91 sin modificar su código. Un error inicial de la nueva prueba de exclusiones se corrigió en la propia prueba (`get` para un campo opcional); no se cambiaron imágenes, etiquetas, modelo ni métricas para hacerla pasar.

Las comprobaciones nuevas cubren separación por grupos, hashes, etiquetas conocidas, exclusiones, reproducción del checkpoint, métricas desde predicciones persistidas, ausencia explícita de modelos, ROI, límites de escritura y procesamiento completo del video sin una afirmación de exactitud. Los tests de captura usan fixtures únicamente temporales y nunca las incorporan al dataset real. Django se comprobó con SQLite en memoria, multimedia temporal y migraciones desactivadas.

La evidencia máquina final se guarda en `verification.json`; el manifiesto de salidas está en `OUTPUT_SHA256.json`. Los árboles fuente y los archivos anteriores de v002 se comparan por SHA-256, excluyendo únicamente esta carpeta experimental nueva. No se modificaron SQLite, producción, YOLO11n, ByteTrack, datasets públicos, v001 ni las preparaciones previas de v002. No se eliminaron fotografías ni se inventaron fechas, cámaras, sesiones, materiales o licencias.

## Siguiente paso recomendado

Conservar este ensayo como demostración de la canalización, no desplegarlo para rechazo automático. Resolver metadatos y evaluabilidad de las 11 fotos propias; reservar nuevas sesiones y unidades físicas para un test EPP ciego; recoger negativos humanos de cuerpo y positivos/negativos de tapa en varias sesiones. Después decidir si se necesita clasificación por envase o localización de defectos, ampliar cobertura y entrenar una versión nueva con evaluación predefinida. El plazo de un día no convierte material sin derechos, desconocidos o vistas correlacionadas en evidencia válida.
