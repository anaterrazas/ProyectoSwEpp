# Fase 2.9 · Consolidación de fuentes para TAPA

## Decisión

**Hay una ampliación real aprovechable sin nuevas capturas: 272 imágenes/ROI de v26 con tapa física visible.** Se preparó además un índice combinado de **284 imágenes y 284 cajas fuente**: 272 de v26 y las 12 candidatas de v4. Esto no equivale a 284 cajas estrictas ajustadas, con test independiente aprobado.

El estado es **CANDIDATO AMPLIADO**, no cierre del dataset TAPA estricto con evaluación independiente. No se entrenó ni se ejecutaron inferencias. La principal limitación ya no es encontrar más imágenes: falta acordar una convención de caja compatible y cerrar una referencia de prueba con procedencia e independencia justificadas.

## Distribución por fuente y compatibilidad

| Fuente | Disponible | Incluido en el índice nuevo | Interpretación |
|---|---|---:|---|
| Mendeley v1 | 7.907 imágenes / 28.413 cajas de defectos | 0 | No tiene una clase de tapa completa acreditada; sus cajas no se convierten en TAPA. |
| Roboflow v26 | 570 imágenes / 606 cajas | 272 imágenes / 272 ROI | 218 Good Cap y 54 Broken Cap: contienen tapas físicas, conservando geometría fuente con contexto. |
| Roboflow v4 | 262 imágenes / 915 cajas RAW | 12 imágenes / 12 cap | Núcleo de seis pares ya cribado; procedencia individual y uso como test aún pendientes. |
| Referencias propias adjudicadas | 25 imágenes / 244 cajas, 143 TAPA y 101 ENVASE | 0 | No hay nueva confirmación de autorización; siguen separadas. |

No se suman las 173 TAPA candidatas de v003 indiscriminadamente: parte de sus imágenes tienen omisiones o problemas de alcance. Tampoco se suman las 623 imágenes de otra versión de Roboflow, duplicados de archivos ZIP, recortes ni miniaturas como nuevas muestras.

## Auditoría de Mendeley

Se reutilizó la auditoría anterior y se consultaron metadata y clases nativas. La metadata describe explícitamente regiones de defectos, no regiones de envase/tapa. Se verificó su integridad mediante la línea base protegida, sin repetir anotaciones ni las revisiones públicas existentes.

Las familias son dent, scuff, adhesion, producto sobre botella y rotura de etiqueta, con gravedad marginal/inaceptable. Ninguna constituye por sí misma una caja de tapa física. Esto **no significa que las fotos no contengan tapas**: significa que no hay una etiqueta de localización compatible que pueda reaprovecharse directamente sin añadir una referencia humana. Las imágenes sin etiqueta TAPA no se consideran negativos. La fuente se conserva para superficie y para una eventual anotación de tapas si hiciera falta; no se descarta ni se altera.

## Auditoría ampliada de v26

Se comprobaron SHA-256 y dimensiones de las 570 imágenes importadas y sus originales RAW, geometría de las 606 cajas y hashes de los tres COCO. Se inspeccionaron **las 272 regiones Good/Broken** mediante 14 hojas de recortes con contexto, seis hojas de escenas completas y ampliaciones dirigidas. No se ejecutó ningún detector.

En esta inspección las 272 regiones contienen una tapa física visible, con una tapa por escena y sin otras tapas evidentes sin referencia. No son nuevas adjudicaciones humanas ni nuevas coordenadas. Predominan primeros planos con fondo oscuro. Las imágenes Broken Cap conservan piezas dañadas y vistas inclinadas: no se interpreta Broken como ausencia física de tapa.

**Convención de geometría:** muchas cajas incluyen la tapa, el anillo y una parte visible del cuello; algunas vistas oblicuas añaden contexto del hombro. No son cajas de un cuello vacío, pero tampoco una referencia uniforme del contorno exclusivo de la tapa. Se separa `ROI_CAP_CON_ANILLO_Y_CONTEXTO_DE_CUELLO` de `CAP_COCO_FUENTE_V4`. No se recortaron ni corrigieron sus coordenadas automáticamente y no se publicó un export YOLO mezclando esas convenciones como si fueran idénticas.

Material excluido del núcleo positivo v26:

- **No Cap: 162 cajas.** Delimitan boca/cuello, no tapa. No se convierten en defectos TAPA_AUSENTE ni en negativos automáticos de imagen completa.
- **Loose Cap: 124 cajas.** En los ejemplos revisados su región se centra en hueco/cuello y no garantiza tapa completa; no se incorpora esa caja como TAPA. Que una imagen muestre físicamente una tapa no hace válida esa ROI para localizar toda la tapa.
- **Broken Ring: 48 cajas.** Delimitan anillo/fragmento, no tapa completa.

Son 334 cajas no mapeadas. No equivalen a 334 imágenes excluidas: se seleccionan 272 imágenes y quedan 298 fuera del núcleo. **Siete de las seleccionadas tienen también una caja Loose Cap**; se conserva esa anotación de origen en trazabilidad y se usa como candidata únicamente su caja Broken Cap que sí contiene la tapa física. No se duplican objetos por tener dos etiquetas fuente.

La correspondencia física de las 272 ROI es aprovechable para un prototipo con convención de origen. No se afirma que sus 272 límites sean válidos para un objetivo estricto que excluya todo cuello. Para ese objetivo falta homologar geometría; no debe ocultarse renombrando las clases.

## Integridad, similitud y grupos

Se verificaron nuevamente los píxeles de las 284 candidatas y se compararon **40.186 pares**, reutilizando las huellas y umbrales estrictos del auditor. Hay **284 hashes únicos**, seis pares similares internos y ningún par aceptado entre los grupos propuestos ni entre las dos fuentes. Eso es un resultado bajo estos umbrales, no prueba de ausencia de toda relación ni independencia de objeto físico.

v26 aporta dos grupos positivos, conservados de la restricción de 202 grupos públicos: nombres de captura **20220701** y **20220704**, con 137 y 135 imágenes seleccionadas. La fecha es un proxy del nombre, no una certificación de sesión ni un ID de botella. No se dividen tomas de un mismo grupo; los miembros de otras clases se excluyen del núcleo positivo y no se reutilizan en otro destino. La membresía completa de origen se conserva en un manifiesto complementario.

v4 aporta seis grupos completos de dos variantes cada uno. Se mantienen juntos; no se consideran doce orígenes. Las 12 imágenes no se presentan como prueba independiente. Las particiones históricas de otros experimentos no se modifican: esta es una propuesta nueva.

## Particiones nuevas propuestas

| Destino provisional | Fuente y grupo | Imágenes | Cajas candidatas |
|---|---|---:|---:|
| Entrenamiento | v26, proxy 20220701 | 137 | 137 |
| Validación de desarrollo | v26, proxy 20220704 | 135 | 135 |
| Reserva sin test independiente aprobado | v4, seis grupos | 12 | 12 |
| **Test independiente aprobado** | **No disponible** | **0** | **0** |

No se fuerza una división 70/15/15 cortando secuencias. Hay ocho grupos candidatos en total, pero solo dos proxies de fecha del dominio de primeros planos; los otros seis son motivos visuales de v4. Ningún destino está habilitado para entrenamiento. Esta distribución permite plantear un experimento de desarrollo entre fechas, no declarar un test final de video.

## Diversidad y suficiencia

- v26 aporta **272 tapas blancas**, 218 etiquetadas Good Cap y 54 Broken Cap por la fuente. Se conserva esa etiqueta auxiliar, pero no se habilita clasificación de defectos ni conformidad global.
- v4 añade tapas azules, verdes y turquesa, fotos de producto, fondo blanco, botellas en el suelo y perspectivas laterales. Solo son doce fotos de seis motivos; su peso en el conjunto es pequeño.
- Predomina en v26 la vista frontal cercana, con algunas vistas inclinadas y oblicuas. No se inventan etiquetas numéricas por perspectiva u oclusión.
- A resolución de referencia 640, el lado menor de las ROI fuente v26 va de **167,07 a 316,11 píxeles**; en las doce cap v4, de **31,05 a 88,59**. El primer rango incluye contexto y no mide exclusivamente el plástico de la tapa.
- El núcleo ampliado no cubre tapas diminutas en líneas, multienvase, oclusiones relevantes ni fondos de producción. Tener 272 fotos parecidas no equivale a 272 situaciones independientes.

**Sí hay volumen para estudiar un primer prototipo de localización de ROI de tapa con datos existentes.** No hay todavía base suficiente para cerrar el objetivo de detección física estricta con prueba independiente de video. Estos dos alcances se mantienen separados: no se cambia silenciosamente el objetivo del usuario para declarar éxito.

## Licencias y procedencia

Se conserva la licencia CC BY 4.0 documentada de las publicaciones, autores y URLs exactas de la evidencia local anterior. Se incorpora la adquisición real de v4, sin reescribir el registro histórico anterior que decía que faltaba el export. No se infieren permisos nuevos ni se atribuye autoría individual a anotadores no identificados.

Las alertas de marcas de terceros de v4 siguen en la auditoría previa. El núcleo de doce evita esas marcas observadas, pero eso no certifica origen ni independencia. Las referencias propias siguen fuera: su autoría de anotaciones no acredita los derechos de sus videos.

## Entrega y siguiente paso mínimo

El candidato nuevo está en `datasets/calidad_botellas/v003/tapa_multifuente_candidato_001/`. Contiene un índice de 284 muestras, el núcleo nativo v26 de 272, la reserva v4 de doce, fuentes/licencias, anotaciones originales, exclusiones y grupos. Se conservan por separado las convenciones, hashes e identificadores. Es un dataset por referencias inmutables; no un export de entrenamiento ya autorizado.

La galería `index.html` permite revisar las 272 ROI y sus escenas sin construir otra herramienta ni repetir la adjudicación de las 25 referencias.

Para cerrar la preparación con el menor trabajo adicional:

1. **Fijar el contrato de caja TAPA** usando los ejemplos entregados: ROI con contexto nativo o contorno exclusivo. Si se exige contorno, hacer una revisión dirigida de geometría en la fuente antes de mezclarla, sin modificar RAW; si se acepta ROI, identificar expresamente ese alcance del primer modelo.
2. **Cerrar el conjunto de prueba reservado**, con procedencia, agrupación y referencia compatibles. Resolver primero los seis motivos v4 existentes; no presentarlos como prueba independiente mientras eso falte. La falta de un test aprobado no se resuelve repartiendo las 272 fotos entre tres carpetas.
3. Mantener el resto de v4 en cuarentena por imagen/grupo hasta corregir exhaustividad. No es necesario corregir todo v4 ni volver a anotar Mendeley para aprovechar v26.

No se solicitan nuevas capturas ahora: los bloqueos inmediatos son convención y referencia de evaluación, no falta total de material. Si el alcance final requiere demostrar comportamiento en línea y las fuentes existentes no permiten acreditar esa referencia, habrá que obtenerla antes de afirmarlo. No se inventa una solución de datos ya completada.
