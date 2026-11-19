# Roboflow v4 · adquisición y preparación de auditoría

18/11/2026 · America/La_Paz. Estado: pendiente de exportación autenticada oficial. No se presenta esta preparación como auditoría de archivos que aún no se han recibido.

## Resultado real de adquisición

Se buscó una exportación v4 en el proyecto y en Downloads, Desktop y Documents, incluyendo nombres Bottle/Defect/Roboflow/v4. Solo apareció el ZIP Bottle Defects v26 ya conocido; no se encontró exportación v4.

La [publicación oficial](https://universe.roboflow.com/spark-intelligence-scqhh/bottle-defect-detection/dataset/4) confirma Spark Intelligence, versión 4, 262 imágenes y licencia publicada CC BY 4.0. Declara 262 imágenes en train, cero en validation y test, sin aumentos. Estas son cifras publicadas, no verificaciones de una descarga local.

Se abrió la descarga oficial en Chrome. El sitio mostró verificación de seguridad Cloudflare. La consulta del endpoint oficial de exportación COCO respondió HTTP 401, indicando que requiere autenticación. No se intentó eludir controles ni se pidió publicar una API key. Los intentos están en pagina_descarga.json/png e intento_api_oficial.json.

Se solicitó abrir la página oficial desde el navegador del usuario, completar verificación/inicio de sesión y descargar COCO JSON como ZIP en Descargas, o indicar otra ruta local. Esta intervención es necesaria por el control de acceso del proveedor, no por una nueva aprobación del trabajo ya autorizado.

Mientras no llegue ese archivo, no se pueden verificar hashes, clases, coordenadas, duplicados ni geometría de v4. No se crean carpetas vacías que simulen una importación ni se añaden 262 imágenes al total canónico de 8.502. Los nombres cap/no-cap/crumbled del registro histórico son referencias pendientes de comprobar contra la exportación real.

## Restricción de separación conservada

Se revalidó la propuesta existente: 8.477 imágenes públicas en 202 grupos, sin grupos divididos entre particiones. Se guardó su ruta/hash y reglas de incorporación en restricciones_202_grupos.json. No se modificó ningún grupo ni split.

La llegada de v4 puede unir componentes si contiene duplicados o procedencia relacionada. Se mantendrá cada uno de los 202 grupos indivisible; si aparece una unión entre splits anteriores, se reasignará el componente completo antes de aprobar la combinación. No añadir v4 a test automáticamente por tener otro publicador. Su split original 100 % train tampoco define el reparto final del proyecto.

## Auditoría a ejecutar al recibir el ZIP

1. Verificar README/dataset: proyecto spark-intelligence-scqhh/bottle-defect-detection, v4, licencia, autor y fecha de exportación. Congelar SHA-256 del ZIP, procedencia y evidencia de publicación; conservar el archivo original.
2. Extraer en un directorio RAW nuevo del espacio público experimental, rechazando traversal, enlaces, tamaños anómalos y sobrescrituras. No ejecutar contenido del archivo.
3. Reutilizar ml.calidad_botellas.import_public en formato COCO/YOLO real. El importador ya valida identidad de exportación, imágenes, coordenadas y anotaciones y conserva clases originales. No instalar SDK ni reconstruir cajas desde previews.
4. Contar archivos, imágenes únicas, cajas por clase, dimensiones, imágenes sin anotaciones y flags. Contrastar la publicación de 262; documentar cualquier diferencia en vez de ajustar números para coincidir.
5. Comparar SHA-256 contra los 8.477 públicos y 25 frames adjudicados; después revisar similitud/procedencia entre fuentes y familias .rf. El hash distinto no acredita captura independiente.
6. Inspeccionar cajas por clase: distinguir tapa física, cuello, hueco, anillo, botella completa y región de deformación. Los ejemplos no sustituyen revisión de los casos dudosos. No Cap no es una tapa ni prueba un defecto sin contexto.
7. Registrar candidatos, pendientes y exclusiones por tarea; conservar anotaciones RAW y decisiones versionadas. Solo después actualizar cantidades de la matriz y proponer particiones finales por componentes.

No se ejecutó este pipeline sobre una exportación inexistente. El comando de importación ya está documentado en ml/calidad_botellas/DATASETS_PUBLICOS.md y se reutilizará con salida nueva.

## Recomendación de modelos, con los datos hoy verificados

| Prioridad | Modelo/tarea | Soporte existente | Limitación pendiente |
|---|---|---|---|
| 1 | Benchmark de defectos superficiales con taxonomía nativa Mendeley | 7.907 imágenes y 28.413 cajas; dent 8.029 cajas y scuff 10.893 | Limitar dominio y aprobar correspondencia dent/deformación y scuff/rozadura; no declarar toda RAYADURA/DEFORMACION industrial |
| 2 | Estado/ROI de tapa en taxonomía Roboflow | 570 imágenes y 606 cajas; Good/Broken/Loose/Ring/No Cap | Validación por grupos desequilibrada; no repetir un clasificador binario débil sin resolver el reparto y alcance |
| 3 | TAPA física | 272 cajas Good/Broken candidatas más lo que realmente aporte v4 | Revisar tapa frente a cuello/hueco; no mapear Loose/Ring/No Cap automáticamente; falta export v4 |
| No nuevo entrenamiento aún | ENVASE | Baseline COCO ya existente | Las cajas de defectos no son cajas de envase; las 101 humanas siguen conservadas y con derechos de video pendientes |

El material Mendeley puede sustentar preparación de un prototipo fuente sin nuevas capturas, manteniendo sus clases y cajas originales. Eso no autoriza entrenar ahora ni resuelve el detector TAPA. En particular, negativos confirmados por proyecto, conformidad global, transferencia de dominio y generalización no se deducen del tamaño de un dataset.

La propuesta previa de Mendeley conserva 5.535/1.186/1.186 imágenes para train/validation/test por grupos. La de Roboflow v26 conserva 281/85/204: validation contiene 82 No Cap y tres Loose, sin Good. No se aprueba como selección fiable de un modelo Good-vs-defectuoso. Ese bloqueo debe revisarse con el contenido real de v4 o con cambios justificados por grupos, nunca repartiendo frames relacionados.

## Exclusiones y pendientes actuales por tarea

- No Cap: no convertir su caja en TAPA física ni su etiqueta en incumplimiento de proceso automáticamente.
- Broken Ring: mantener anillo como subtipo separado; no convertirlo en tapa completa.
- Loose Cap: revisar geometría; ejemplos previos delimitan el hueco bajo la tapa.
- Defectos de superficie Mendeley: no convertir cajas de defecto en ENVASE; adhesión/rotura de etiqueta y producto sobre botella permanecen fuera de rayadura/deformación salvo protocolo explícito.
- Las 25 referencias/244 cajas: intactas y sin mezclar con públicos hasta resolver derechos del video fuente.
- v4: PENDIENTE_DE_ARCHIVOS, no excluido por calidad ni declarado compatible sin revisión.

## Estado de entregables

- Exportación v4 verificada: pendiente de descarga autenticada.
- Licencia/versión/publicación: confirmadas en fuente oficial; falta confirmar identidad del ZIP concreto.
- Conteos, duplicados y geometría v4: no calculables todavía.
- Matriz y combinación definitivas: no aprobadas hasta recibir y auditar el archivo. Se conservan las propuestas anteriores y las restricciones de los 202 grupos.
- Entrenamiento, inferencia, modificación de originales: ninguno.

No se solicitaron nuevas capturas. El siguiente paso mínimo es conseguir la exportación oficial, no repetir anotaciones ni abandonar las fuentes existentes.
