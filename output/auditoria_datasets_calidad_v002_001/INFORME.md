# Auditoría integral de datasets para Calidad v002

18/11/2026 · America/La_Paz. Se reutilizaron importaciones, revisiones humanas y análisis de similitud anteriores, comprobando nuevamente hashes y anotaciones originales. No se entrenó, ejecutó inferencia ni modificó dataset alguno.

## Decisión y corrección de prioridad

**Sí hay material público útil y con licencia documentada para avanzar sin pedir nuevas capturas ahora.** La limitación de los cinco videos no debe extenderse a estos datasets. Hay datos para preparar prototipos de defectos superficiales y estados de tapa. Todavía no hay un dataset único listo para un detector físico ENVASE/TAPA más los tres defectos, ni evidencia para declarar completado Calidad en video.

La siguiente acción mínima es aprovechar las cajas públicas y recuperar la exportación Roboflow v4, antes de grabar. Para TAPA física debe resolverse la semántica de las cajas; para superficie pueden reutilizarse cajas reales de abolladura/rozadura. No se solicita repetir los 25 fotogramas ni las 100 revisiones públicas ya existentes.

## 1. Inventario físico y versiones

| Fuente | Ubicación | Disponible realmente | Anotación |
|---|---|---:|---|
| Mendeley Plastic Shampoo Bottle, kthmmbsh8t v1 | datasets/publicos_calidad_botellas/raw/mendeley_kthmmbsh8t_v1 y imports/mendeley_kthmmbsh8t_v1_001 | 7.907 imágenes; 28.413 cajas | YOLO TXT, diez clases de defecto/gravedad |
| Roboflow Bottle Defects v26 | raw/roboflow_caps_v26 y imports/roboflow_caps_v26_001 | 570 imágenes; 606 cajas | COCO JSON; cinco clases con instancias |
| Roboflow Bottle Defect Detection v4 | Registro en ml/calidad_botellas/public_sources.json y publicación | 262 publicadas; 0 imágenes/exportaciones locales encontradas | Publicado como detección; archivos no verificables aún |
| Referencia adjudicada v002 | datasets/calidad_botellas/v002/experiments/detection_manual_v001/dataset_tapa_adjudicado_fase23_001 | 25 imágenes; 244 cajas: 101 ENVASE y 143 TAPA | Referencia humana corregida; derechos de videos pendientes |

Se localizaron RAR original Mendeley de 162.131.884 bytes (154,62 MiB) y ZIP Roboflow v26 de 253.699.544 bytes, además de una copia idéntica del ZIP en Descargas. No son imágenes adicionales. La búsqueda de archivos de dataset en el proyecto, Downloads y Documents no encontró una exportación v4 de 262 imágenes. Su ausencia local no implica descartar la fuente: el siguiente paso es obtener su exportación real COCO/YOLO, no inventar sus cajas desde previews.

La cifra histórica **623** corresponde al proyecto/otra versión de Bottle Defects; la página oficial distingue v28 con 623 de **v26 con 570**, que es el ZIP local. No sumar 623 y 570 como fuentes independientes. [Versión oficial 26](https://universe.roboflow.com/product-defect-detection/bottle-defects-o4gnx/dataset/26).

Mendeley contiene imágenes 400×700. Roboflow local contiene imágenes 3840×2160. Los RAW extraídos actuales tienen respectivamente 7.907 JPG + 7.907 TXT + YAML y 570 JPG + tres JSON COCO + dos README. Las importaciones conservan los bytes originales; carpetas raw/imports, miniaturas, recortes, selecciones y modelos anteriores no se cuentan como nuevas muestras.

También existen 19 recortes históricos v001, 100 imágenes públicas revisadas y el subconjunto de 50 del ensayo TinyCapCNN. Las 100/50 son subconjuntos de los mismos 8.477 públicos, no nuevos datos. Los 19 recortes proceden de una ejecución con ocho IDs temporales y todos constan globalmente no evaluables en la auditoría previa; no equivalen a 19 nuevas botellas independientes ni se promueven a referencia de producción.

## 2. Licencias y procedencia verificadas

- **Mendeley v1:** publicación y metadata.json acreditan CC BY 4.0, Fakhra Aftab y Majida Kazmi, DOI 10.17632/kthmmbsh8t.1. La publicación describe cajas de cinco familias de defectos y gravedad marginal/inaceptable. [Publicación oficial](https://data.mendeley.com/datasets/kthmmbsh8t/1).
- **Roboflow v26:** página oficial y README.dataset.txt declaran CC BY 4.0 y Product Defect Detection; README.roboflow.txt acredita 570 imágenes, COCO y ausencia de aumentos en ese export. El ZIP coincide con ACQUISITION.json. PROVENANCE_LICENSE.json conserva un estado histórico AUTHENTICATION_REQUIRED, superado por la descarga real del ZIP; no se altera ese registro antiguo.
- **Roboflow v4:** la publicación confirma CC BY 4.0, Spark Intelligence y 262 imágenes. La licencia de publicación está verificada; integridad, contenido y clases del export local aún no pueden verificarse porque falta el archivo. [Publicación oficial](https://universe.roboflow.com/spark-intelligence-scqhh/bottle-defect-detection/dataset/4).
- **Las 25 imágenes adjudicadas:** anotaciones humanas conservadas, pero no heredan CC BY de otros datasets. Los videos fuente siguen con autorización/procedencia pendientes. No se incorporan automáticamente a entrenamiento junto a las fuentes públicas licenciadas.

CC BY 4.0 permite reutilización/adaptación con atribución, enlace de licencia e indicación de modificaciones; conservar ese crédito en manifiestos y documentación, sin implicar respaldo de los autores. [Licencia oficial](https://creativecommons.org/licenses/by/4.0/). No se inventa identidad de anotadores individuales ni derechos adicionales no documentados.

Evidencia local y URLs en licencias_y_procedencia.json. Los originales, licencias y registros no se reescribieron.

## 3. Hashes, duplicados y contaminación

Se recalcularon los SHA-256 de las 8.477 imágenes importadas y sus ocurrencias RAW: coinciden. Se verificaron 7.910 archivos de anotación originales distintos: 7.907 TXT y tres COCO JSON, con sus hashes de importación. Se comprobaron 29.019 cajas públicas contra dimensiones y se conservaron coordenadas originales, sin cajas ficticias.

Con los 25 frames adjudicados: **8.502 imágenes canónicas, 8.502 SHA-256 distintos y cero duplicados exactos entre estas fuentes**. Las copias RAW/importación/ZIP no incrementan ese total. Esto no significa 8.502 botellas físicas ni independencia visual.

El análisis visual previo, reutilizado después de verificar los hashes actuales, contiene 571 grupos candidatos y 142.922 parejas de semejanza entre las imágenes históricas analizadas. No encontró grupos perceptuales entre fuentes distintas; eso no demuestra ausencia universal de relación. No se repitió una búsqueda perceptual exhaustiva para los 25 frames nuevos; su falta de licencia ya impide mezclarlos como test público.

Se conservan los hallazgos previos: 447 grupos visuales cruzaban particiones originales y 1.352 familias nominales Mendeley aparecían en más de un split original. Los nombres anteriores a `.rf.` permiten agrupar recomprensiones/aumentos aunque sus hashes sean distintos. No se debe confiar en train/valid/test originales como prueba de independencia.

## 4. Clases y cajas reales: qué representan

### Mendeley

| Familia fuente | Cajas | Imágenes con presencia | Compatibilidad |
|---|---:|---:|---|
| dent_marg + dent_unacc | 8.029 | 2.388 | Abolladura localizada; candidata a DEFORMACION, conservando gravedad y alcance |
| scuff_marg + scuff_unacc | 10.893 | 2.572 | Rozadura/abrasión superficial; no equiparar sin protocolo a cualquier RAYADURA |
| adhesion_marg/unacc | 2.301 | 1.066 presencias por clase | Adhesión de etiqueta; no es rayadura automáticamente |
| pob_marg/unacc | 5.926 | 1.048 presencias por clase | Producto sobre botella; fuera de los tres objetivos actuales |
| tear_marg/unacc | 1.264 | 833 presencias por clase | Rotura de etiqueta; no deformación ni rayadura del plástico automáticamente |

Los conteos de imágenes son presencias por familia/clase según origen, no conformidad negativa de otras tareas. No convertir imágenes sin dent/scuff anotado en negativos humanos confirmados del proyecto. Las cajas delimitan defectos, no botellas completas ni tapas. La fuente es plástico de shampoo, generalmente opaco y con etiquetas, diferente a las garrafas transparentes del piloto. Es útil para un benchmark de superficie, no evidencia de generalización automática al otro dominio.

### Roboflow v26

| Clase fuente | Cajas | Imágenes | Alcance |
|---|---:|---:|---|
| Good Cap | 218 | 218 | Estado de tapa según fuente; no conformidad global |
| Broken Cap | 54 | 54 | Daño visible de tapa |
| Loose Cap | 124 | 124 | Colocación floja según fuente; no confundir su ROI con tapa completa |
| Broken Ring | 48 | 47 | Anillo dañado, distinto de tapa completa |
| No Cap | 162 | 162 | Cuello/región sin tapa según fuente; no una caja de TAPA física |

Una imagen puede contener más de una anotación: las 606 cajas no son 606 imágenes. Broken/Loose aportan 178 instancias en 171 imágenes. Good/Broken aportan 272 cajas en 272 imágenes candidatas para revisar localización física.

La hoja roboflow_cajas_fuente.jpg muestra dos ejemplos por clase, sin reetiquetar. Good/Broken suelen abarcar tapa y parte de cuello/anillo. **En ejemplos de Loose Cap la caja se centra en el hueco bajo la tapa y excluye buena parte de ella; Broken Ring delimita solo un fragmento del anillo.** Por tanto, ni las 606 cajas ni las 396 Good/Broken/Loose pueden convertirse sin revisión en 606/396 TAPAS físicas. Esta inspección de ejemplos no adjudica automáticamente cada caja restante.

Los envases del ejemplo parecen plásticos y transparentes, por lo que hay utilidad para cuello/tapa; el fondo oscuro, vista cercana y tapa blanca limitan diversidad frente a garrafas coloreadas y escenas con varios objetos. Los defectos de superficie de Mendeley y el estado de tapa de Roboflow no deben convertirse en una clasificación multiclase exclusiva que aprenda el origen en vez del defecto.

### Qué es detección y qué es clasificación

**Ambos datasets RAW son de detección, con bounding boxes reales.** Los manifests importados conservan esas cajas en source_occurrences, aunque el mapeo histórico del proyecto las redujo a presencia parcial en imagen. No hay que volver a inventar cajas ni descartar las originales.

Las selecciones de 100/50 imágenes y el modelo TinyCapCNN son derivados de clasificación; no añaden cajas. Las 50 etiquetas humanas (36 positivas/14 negativas de tapa) ya se usaron en un ensayo; reutilizarlas como si fueran nuevas observaciones o un test independiente inflaría la evidencia. Los negativos de superficie confirmados siguen faltando en esa capa humana; no rellenarlos desde null.

## 5. Matriz por objetivo y capacidad de avanzar

| Objetivo | Qué puede reutilizarse ahora | Qué falta antes de entrenar esa tarea |
|---|---|---|
| ENVASE | Baseline COCO existente; 101 cajas humanas preservadas | Ninguna fuente pública auditada aporta caja completa ENVASE compatible acreditada; no fabricar una desde defectos. Resolver derechos antes de usar las 25 imágenes |
| TAPA física | 272 cajas Good/Broken candidatas y futura clase cap de v4 si su export lo confirma | Revisar convención tapa/cuello y exhaustividad; Loose/Ring/No Cap no son cajas intercambiables. Conseguir v4 y comprobar duplicados antes de combinar |
| TAPA_DEFECTUOSA | Etiquetas fuente Broken/Loose y Good por ámbito de tapa; 50 revisiones humanas existentes | Mantener subtipos, definir negativo por tarea y no llamar conformidad global a Good. No Cap exige contexto para defecto de ausencia; Ring necesita criterio propio |
| RAYADURA | 10.893 cajas scuff, 2.572 imágenes positivas fuente | Aprobar alcance «rozadura/abrasión» o mantener SCUFF separado. Etiqueta rota/adhesión no equivalen. Revisar negativos/exhaustividad según tarea |
| DEFORMACION | 8.029 cajas dent, 2.388 imágenes positivas fuente | Limitar inicialmente a abolladura y dominio shampoo; mantener gravedad. No prometer toda deformación de cualquier envase |

**Se pueden preparar sin nuevas capturas** un benchmark nativo de defectos de superficie con las diez clases originales y un benchmark de estados/ROI de tapa con las cinco clases fuente. Para pasar a las clases del proyecto se necesitan aprobación de taxonomía y controles de exhaustividad/evaluabilidad; no entrenamiento automático en esta entrega.

Para localización física TAPA, el paso barato es revisar/reutilizar cajas públicas y obtener el export v4, no grabar primero nuevos videos. Es posible que algunas cajas necesiten reajuste humano, pero no es necesario volver a anotar por defecto las 570 imágenes ni las 25 originales.

## 6. Combinación propuesta sin mezclar etiquetas incompatibles

Se creó inventario_canonico.jsonl con 8.502 referencias y propuesta_combinacion.json como diseño lógico, **no un dataset de entrenamiento aprobado ni una copia física adicional**:

1. **Ruta superficie:** Mendeley con cajas fuente y diez clases/gravedades preservadas. Prototipo dent/scuff, manteniendo separadas adhesión/producto/rotura de etiqueta. Si se entrena una taxonomía reducida, el loader debe tratar explícitamente otras clases/desconocidos, no transformarlas silenciosamente en fondo o negativos de defectos.
2. **Ruta estado de tapa:** Roboflow v26 con nombres fuente, cajas/ROI y contexto. Clasificación o detección de regiones de estado; no detector físico TAPA por renombrado. Good Cap solo es negativo candidato para defectos de tapa definidos en ese ámbito, nunca negativo de cuerpo ni conformidad integral.
3. **Ruta TAPA física:** revisar Good/Broken y añadir cap de v4 solo al comprobar archivos reales. Mantener ignorable el resto de regiones no equivalentes; no crear TAPA_AUSENTE sobre una boca vacía. Las imágenes No Cap podrían ser fondos de detector físico solo tras confirmar exhaustividad/ausencia de tapas visibles; eso es distinto de confirmar defecto posterior al tapado.
4. **Referencia de videos:** 25 frames y 244 cajas intactas en cuarentena de derechos; no mezclarlos en entrenamiento público hasta resolver procedencia. Pueden seguir conservados como trabajo histórico, sin declarar autorización.

Cada registro debe retener fuente/versión, licencia/atribución, clase/caja original, decisión de mapeo, alcance, desconocidos, grupo y partición. Una cabeza o tarea no debe usar la ausencia de anotaciones de otra fuente como negativo: Mendeley no anota tapas exhaustivamente y Roboflow no anota rayaduras/deformaciones. No se entrena un YOLO combinado de cinco clases ignorando esto.

## 7. Propuesta de distribución y sus límites

Se revalidó la propuesta de grupos existente, sin mover imágenes ni modificar manifests anteriores:

| Fuente | Train propuesto | Validation propuesta | Test propuesto |
|---|---:|---:|---:|
| Mendeley | 5.535 | 1.186 | 1.186 |
| Roboflow v26 | 281 | 85 | 204 |
| Total público | 5.816 | 1.271 | 1.390 |
| 25 frames adjudicados | Sin asignar, fuera del entrenamiento público | Sin asignar | Sin asignar |

La propuesta conserva 202 componentes, con cero cruces de grupo entre particiones. Es un punto de partida para benchmark, no test industrial aprobado. No deben sumarse fuentes relacionadas/versiones Roboflow en particiones distintas. Cuando llegue v4 se recalcularán coincidencias y grupos antes de asignarlo; distinto publicador no demuestra distinto origen.

Hay un bloqueo específico de balance en Roboflow que el porcentaje global oculta. Los nombres WIN sugieren cuatro días, proxies de captura y no identidades de botella verificadas:

| Fecha nominal | Imágenes | Composición fuente principal | Partición heredada de la propuesta |
|---|---:|---|---|
| 2022-07-04 | 281 | Good 106, Broken 29, Loose 55, No Cap 80, Ring 28 cajas | Train |
| 2022-07-05 | 82 | Solo No Cap | Validation |
| 2022-07-13 | 3 | Solo Loose Cap | Validation |
| 2022-07-01 | 204 | Good 112, Broken 25, Loose 66, Ring 20 cajas | Test |

Por eso validation tiene solo tres imágenes positivas Broken/Loose y ningún Good Cap. No permite seleccionar un clasificador binario Good-vs-defectuoso con especificidad representativa. Para TAPA física, las 272 Good/Broken están concentradas en dos fechas; el tercer conjunto requiere cajas compatibles/revisión adicional o una nueva fuente. No remediarlo mezclando frames del mismo día/objeto entre particiones.

Mendeley ofrece más grupos para benchmark de superficie, pero esos grupos siguen siendo proxies de archivo/similitud, no sesiones físicas certificadas. Conservar límites de generalización y una evaluación posterior del dominio real. Los grupos/ensayos previamente usados en TinyCapCNN deben declararse; no reutilizar sus resultados como prueba independiente del nuevo detector ni inicializar con pesos que hayan visto el test reservado.

## 8. Qué falta exactamente y siguiente paso mínimo

**No pedir nuevas capturas todavía.** Prioridad:

1. Recuperar la exportación real **Bottle Defect Detection v4, 262 imágenes**, preferentemente COCO JSON/YOLO con README/licencia. La publicación ya existe; no hace falta empezar otro dataset ni proporcionar API keys. Se verificará versión, archivos, cap/no-cap/crumbled y duplicados antes de importar.
2. Revisar una muestra dirigida de la geometría Good/Broken/Loose/Ring para fijar qué cuenta como TAPA física. Usar las cajas existentes y modificar únicamente las necesarias en una copia versionada con decisión humana. Revisar después las candidatas que se aprueben, sin repetir las 25 adjudicaciones.
3. Aprobar taxonomía: dent → abolladura/deformación acotada; scuff → rozadura o alcance explícito de rayadura; Ring separado; No Cap condicionado. Con esto puede prepararse el prototipo de superficie con las cajas actuales, sin fotografías nuevas.
4. Para tapa, resolver el desequilibrio por grupos usando primero v4 y sus posibles sesiones. Para clasificación/inspección mantener desconocidos; los negativos Good locales ya revisados pueden reutilizarse dentro de su alcance, sin extenderlos automáticamente a toda la fuente.
5. Solo si después de esos pasos faltan positivos independientes, tipos de tapa o evaluación representativa del dominio objetivo, solicitar **esa cobertura concreta**, preferentemente imágenes/videos autorizados del dominio plástico. Captura nueva sí será necesaria si se pretende demostrar seguimiento, asociación y defectos temporales de una línea sin una fuente autorizada equivalente, pero no es requisito para empezar a aprovechar las fuentes públicas.

No hace falta recapturar todo ni esperar a resolver los videos stock para investigar superficie con fuentes CC BY. Tampoco estas fuentes justifican decir que Calidad está terminado: no aportan aún seguimiento, enlaces tapa-envase por escena múltiple o validación industrial del piloto.

## 9. Verificación y entregables

- resumen_auditoria.json e inventario_canonico.jsonl: cantidades reales, hashes y clases; 8.477 públicos + 25 frames, sin sumar subconjuntos.
- archivos_comprimidos_localizados.json y licencias_y_procedencia.json: archivos, versiones, autores y evidencia.
- duplicados_y_grupos.json y propuesta_particiones_publicas.jsonl: coincidencias exactas y propuesta por componentes revalidada, no aprobada para entrenar.
- matriz_compatibilidad.csv y propuesta_combinacion.json: límites por objetivo y separación de tareas.
- roboflow_cajas_fuente.jpg y ejemplos_geometria.json: ejemplos auditables de regiones originales; no predicciones ni adjudicaciones automáticas.
- protegidos_antes.json y verificacion_integridad.json: conservación de entradas y evaluaciones anteriores.

Solo se añadieron artefactos en output/auditoria_datasets_calidad_v002_001. No se cambió código de módulos, EPP, producción, SQLite operativo, pesos, datasets públicos, las 244 cajas ni las siete decisiones humanas. No se repitieron entrenamientos, inferencias o pruebas de software antiguas; se verificó integridad y estructura para esta propuesta nueva.
