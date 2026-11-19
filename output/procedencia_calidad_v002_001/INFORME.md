# Procedencia y separación de videos · Calidad v002

18/11/2026 · America/La_Paz. Auditoría de archivos y registros existentes, sin entrenamiento, inferencia, modificación de referencias ni extracción para anotación. No se repitió la evaluación de modelos ni la anotación de los 25 frames.

## Diagnóstico concreto

**No se puede aprobar todavía una separación de entrenamiento/validación/prueba con independencia y derechos acreditados usando únicamente lo registrado.** Se localizaron cinco contenidos originales candidatos de Calidad en 26 archivos físicos. Las copias de uploads y backup no aportan muestras. Hay pistas nuevas de origen comercial/publicación externa, pero faltan URL exacta, autor, licencia aplicable y sesiones verificables.

No se demuestra que prueba2 y tapas sean de la misma sesión; tampoco se acredita formalmente que sean independientes. Sus contextos y fechas internas difieren y son indicios de capturas diferentes. La relación que merece especial precaución es **produccion y tapas**, no prueba2 y tapas: sus fechas internas se separan por 42 segundos y muestran escenas compatibles de embotellado con tapas amarillas. No separarlos entre particiones sin aclarar su origen.

## Alcance, reutilización y exclusiones

Se revisaron los videos candidatos en pruebas_ia, cargas de media/produccion/videos y copias de media_backup/produccion/videos. La búsqueda también comprobó las ubicaciones de videos/datos v002; no aparecieron otras fuentes originales de Calidad distintas de estas cinco. Los videos EPP no se cuentan como Calidad.

Se reutilizaron hashes/metadatos del manifiesto de las 25 imágenes, reportes históricos de referencia/simulación y registros de agrupación. Solo se leyeron cabeceras del contenedor, atributos del archivo y Zone.Identifier que no estaban documentados; no se repitió una decodificación completa de integridad. Para revisión visual se usaron imágenes existentes de prueba2/tapas y tres puntos de los otros videos. No se guardaron nuevas referencias de anotación ni se afirmó una búsqueda exhaustiva de objetos por todo el video.

Se excluyen como originales: deteccion_produccion.avi, resultados_preformas/deteccion_preformas.mp4, seguimiento/botellas/produccion.avi, seguimiento/conteo/conteo_botellas.mp4 y salidas IA. Los scripts existentes documentan que son derivados de produccion o produccion_prueba_02. No deben convertirse en nuevos grupos de captura ni verdad humana.

## Fuentes únicas comprobadas

| Archivo canónico en pruebas_ia | Resolución / FPS nominal | Frames / duración nominal | Copias idénticas | creation_time interno UTC | HostUrl en Zone.Identifier |
|---|---|---|---:|---|---|
| produccion.mp4 | 1280×720 / 50 | 434 / 8,68 s | 20 | 2021-12-02 01:00:58 | pexels.com |
| prueba2.mp4 | 1920×1080 / 29,970 | 406 / 13,55 s | 1 | 2020-10-02 18:51:58 | pexels.com |
| tapas.mp4 | 1280×720 / 50 | 450 / 9,00 s | 1 | 2021-12-02 01:01:40 | pexels.com |
| botellasSinTapa.mp4 | 768×432 / 25 | 399 / 15,96 s | 1 | No encontrado | istockphoto.com |
| produccion_prueba_02.mp4 | 3840×2160 / 29,970 | 1017 / 33,93 s | 3 | 2020-04-17 13:45:30 | pexels.com |

Las cinco fuentes son H.264 según sus cabeceras. Duración de tabla = número declarado de frames / FPS nominal; los PTS y duración del contenedor pueden diferir ligeramente. No sustituye los timestamps ya medidos en registros anteriores.

**Importante:** produccion_prueba_02 es 4K. El ejecutor genérico admite como máximo Full HD; reutilizarlo requiere una derivación controlada con transformación de coordenadas documentada, preservando el 4K original. No se realizó esa conversión y no se considera un impedimento técnico irreversible.

Los SHA-256 completos y las 26 rutas están en auditoria_procedencia.json. Cuatro hashes coinciden con referencias históricas: produccion, prueba2, tapas y botellasSinTapa. Para produccion_prueba_02 se calculó/verificó identidad entre sus tres copias; no se localizó un hash histórico independiente en los registros reutilizados, por lo que no se afirma comparación contra un inventario anterior para esa fuente.

## Qué prueban las fechas y metadatos

- Las fechas de creación/modificación del sistema de archivos corresponden principalmente a incorporaciones de noviembre de 2026, no necesariamente a grabación. La auditoría conserva ambas en UTC por cada copia.
- creation_time del contenedor es un indicio de creación/codificación, editable y no firmado. No certifica sesión, cámara, titular ni captura física.
- Los cinco Zone.Identifier tienen ZoneId=3 y HostUrl genérico. Son evidencia local de una procedencia web probable; no autentican el recurso específico ni los derechos del usuario.
- Los manifiestos originales siguen con session_id, capture_date, license y rights_holder desconocidos para prueba2/tapas. La configuración de pilotos declara etapa POST_TAPADO como objetivo, pero etapa_confirmada_en_videos=false: no usarla como prueba de captura posterior al tapado.
- Los metadatos emitidos en el stdout del comando ffmetadata incluyen encoder de la herramienta de exportación. Para identificar el archivo de entrada se usó exclusivamente la sección Input de stderr, no ese encoder generado. Los logs completos conservan la distinción.

No se rellenó ningún session_id, licencia o fecha de captura original a partir de esas pistas.

## Revisión visual y utilidad real

| Fuente | Evidencia visual / registrada | Uso candidato y limitación |
|---|---|---|
| prueba2 | Garrafas plásticas, tapas rojas/amarillas/blancas colocadas y sueltas | Desarrollo TAPA actual; ya tiene 125 cajas TAPA adjudicadas, no es test nuevo |
| tapas | Primer plano de tapas amarillas en máquina, con cuellos/envases oscuros | Desarrollo actual con 18 cajas TAPA; no demuestra por sí solo el dominio de envase plástico |
| produccion | Línea de botellas oscuras aparentemente de vidrio y tapas amarillas | Posible material auxiliar de detección si se acreditan derechos; posible misma sesión/familia de origen que tapas; sin cajas TAPA humanas |
| botellasSinTapa | Envases transparentes en transporte, marca visible iStock/Getty | No hay positivos TAPA acreditados ni etapa post-tapado confirmada; no es referencia de ausencia. Sin permiso ML acreditado |
| produccion_prueba_02 | Fabricación/soplado, preformas y máquina | No hay positivos TAPA acreditados en los puntos revisados. Puede aportar confusores/negativos solo tras revisión y derechos; no sustituye un test con tapas positivas |

La ausencia de positivos acreditados en los dos últimos no declara que todos sus frames carezcan de tapas. No se generaron negativos. Para detector TAPA pueden ser útiles tapas colocadas o sueltas de otros materiales, pero una evaluación en vidrio no acredita rendimiento en plástico. Tampoco una escena de fabricación confirma inspección posterior al tapado.

## Independencia y particiones

**prueba2 frente a tapas:** hashes distintos, fechas internas 2020/2021, resoluciones/FPS y contextos diferentes. Hay evidencia compatible con capturas diferentes, pero faltan páginas originales, autores, sesiones y relación entre contenidos. No está acreditada independencia del origen; no se modifica la unión conservadora del dataset por sesiones desconocidas.

**produccion frente a tapas:** mismo día interno, 42 s de diferencia, 720p/50 FPS y similitud de escena/capsulado. Es una hipótesis de relación que debe agruparlos provisionalmente para evitar fuga. No se afirma que sean duplicados byte a byte ni que se haya demostrado una misma sesión física.

**botellasSinTapa y produccion_prueba_02:** archivos y contextos distintos, pero sin sesión autenticada, licencia específica y referencia TAPA positiva. No pueden usarse automáticamente como validation/test útiles por tener un nombre distinto.

No se creó train/validation/test. El dataset adjudicado continúa con 25 frames, 101 ENVASE y 143 TAPA, un componente UNASSIGNED y ninguna partición asignada. Separar un video por tramos temporales o repartir sus frames no resolvería independencia. Todas las copias del mismo SHA deben quedar siempre juntas.

Incluso si se confirmara independencia de prueba2 y tapas, son material conocido de desarrollo y solo ofrecen dos fuentes positivas anotadas. No basta añadir un video sin positivos TAPA para obtener un test que mida recall. Se necesitan grupos independientes adecuados al alcance, no solo tres nombres de archivo.

## Derechos: qué se verificó y qué falta

Se examinaron registros locales y las condiciones oficiales actuales, consultadas el 18/11/2026. No se encontró comprobante, identificación exacta de clip o autorización ML asociada a estos archivos.

**Pexels:** el HostUrl solo apunta al dominio. Falta página/ID de cada clip, autor, procedencia del descargable, condiciones aplicables y soporte para el uso previsto. Sus términos restringen extracción automatizada no autorizada, incluidos fines ML; la guía de API exige permiso explícito para recopilar contenido a escala con esos fines. Esto no permite afirmar que todo uso manual esté prohibido, ni aprobar este uso concreto. [Términos oficiales, sección 8](https://www.pexels.com/terms-of-service/) y [guía oficial de API](https://help.pexels.com/hc/en-us/articles/900005880463-What-are-the-Terms-and-Conditions).

**iStock:** además del HostUrl, hay aviso de copyright y marca visible. La licencia oficial restringe el uso ML/AI, incluida evaluación, salvo autorización expresa. No hay evidencia de esa autorización en el proyecto; no incorporarlo a nuevos entrenamientos/evaluaciones ML hasta resolverla. Una licencia comercial ordinaria no demuestra permiso ML. [Licencia oficial, apartado 3.15](https://www.istockphoto.com/legal/license-agreement).

No se borraron ni modificaron evaluaciones anteriores ni se concluye retrospectivamente qué acuerdo tenía quien descargó. Se registra falta de acreditación para futuras decisiones. La existencia local o gratuidad de una descarga no acredita todos los usos.

## Búsqueda adicional tras la confirmación del usuario

El usuario confirmó que no conserva enlaces exactos ni documentación de licencia/autorización ML. Solo recuerda produccion_prueba_02 como el primer video recomendado de Pexels; ese recuerdo se registra como declaración, no como identificación de un recurso ni permiso.

Se amplió la búsqueda local, sin modificar videos/datasets:

- Historiales de descargas y URLs de los perfiles Default existentes de Chrome y Edge, filtrados por Pexels/iStock y nombres de estos videos. No se exportó navegación general ni credenciales.
- Chrome permitió lectura normal. Edge devolvió database is locked; se usó un snapshot SQLite immutable de solo lectura, sin cerrar el navegador ni cambiar su base. No había WAL visible. Esta lectura no garantiza recuperar actividad todavía en memoria o no persistida.
- No aparecieron descargas ni URLs de proveedor coincidentes en esos historiales consultados. Otros equipos, perfiles eliminados, navegación privada o historiales borrados no son recuperables por esta comprobación.
- Búsqueda de referencias a clips Pexels/iStock en registros locales del proyecto y conversaciones locales relacionadas: no se recuperó URL de clip ni CDN. Las URLs generales/de condiciones encontradas no identifican los videos. No se reconstruyeron enlaces por conjetura.
- Historiales de comandos PowerShell disponibles: sin referencias de descarga Pexels/iStock recuperadas. No se imprimieron comandos generales.
- Downloads, Desktop, Videos y Documents: se buscaron archivos de video con los tamaños de las cinco fuentes para recuperar un posible nombre original; no hubo candidatos por tamaño. No se inspeccionaron contenidos de documentos personales.

Registros: historial_fuentes_local.json, busqueda_referencias_adicional.json y busqueda_archivos_descargados.json. El dominio de Zone.Identifier es la única referencia local de origen recuperada, insuficiente para identificar el clip o acreditar licencia. No se modificaron historiales de navegador ni se eliminaron sesiones.

**Resultado actualizado:** no se ha podido acreditar ninguna fuente exacta o autorización adicional. Los cinco archivos siguen pendientes de procedencia/autorización y sin sesiones confirmadas. No se proponen nuevas búsquedas masivas ni se repiten anotaciones para solventar un problema de derechos y agrupación.

## Camino más corto recomendado

1. **Sin nuevas anotaciones:** la búsqueda local ya realizada no recuperó enlaces/IDs. Conservar los cuatro clips Pexels pendientes; reabrir su uso solo si aparece la referencia exacta y el permiso aplicable. Para iStock, solo avanzar si hay autorización expresa ML; no invertir en etiquetarlo mientras falte.
2. **Si se acreditan:** mantener las 25 imágenes corregidas como desarrollo, agrupar produccion/tapas salvo evidencia contraria y comprobar si existen contenidos adicionales realmente independientes con tapas del dominio. Los otros archivos actuales no aportan hoy esos dos grupos de evaluación confirmados. Acreditar una licencia no crea datos positivos ni independencia.
3. **Si no se recupera rápidamente la procedencia o no hay grupos adecuados:** la vía controlable es obtener material propio/autorizado. No hace falta una cámara industrial para un piloto de localización: un celular y envases/tapas reales permiten una captura acotada, declarando que será laboratorio. Reservar sesiones/grupos completos y distintos para desarrollo, validación y prueba; no tres recortes de la misma toma.
4. **Cantidad mínima condicionada:** si los actuales quedan autorizados y su dominio sirve como desarrollo, obtener al menos dos grupos nuevos independientes con positivos TAPA para validation/test. Si no se autorizan, no contar sus imágenes para entrenar: preparar también un grupo propio de desarrollo, es decir, al menos tres grupos en total como separación experimental mínima. Esto no acredita suficiencia estadística; ampliar según cobertura/curvas de rendimiento.
5. Registrar cámara/fecha/sesión/derechos, cajas de tapas visibles colocadas y sueltas, confusores y regiones ignoradas. Anotar únicamente esos datos nuevos cuando proceda; no repetir los 25. La estación post-tapado se confirma solo si se va a evaluar ausencia como defecto. Para localizar TAPA visible no es obligatorio resolver todavía rayaduras, deformaciones o las tres clases de colocación.

**Recomendación final:** conservar el trabajo actual; no entrenar ni forzar un split ahora. Dado que no se recuperaron fuentes exactas y el usuario no dispone de documentos, obtener material propio o expresamente autorizado es el camino mínimo controlable. Para la separación experimental inicial se requieren al menos tres grupos propios independientes con procedencia documentada, uno por desarrollo/validación/prueba; no tres recortes ni los mismos objetos conocidos repartidos entre conjuntos. No es necesario repetir los 25 frames: sus 244 cajas siguen intactas y podrán reutilizarse si después se acreditan derechos. No existe obligación técnica de volver a grabar si se consiguen otras fuentes válidas, pero no hay hoy esas fuentes acreditadas en el proyecto.

## Trazabilidad y conservación

- auditoria_procedencia.json: cinco contenidos, 26 copias, hashes, atributos UTC, tags de entrada, ADS y campos no confirmados.
- Logs *_contenedor.txt: cabeceras y metadatos, sin decodificación integral repetida.
- comparacion_fuentes.jpg: comparación visual de puntos de referencia, sin anotaciones ni predicciones nuevas.
- verificacion_integridad.json: conservación de fuentes y manifiesto previo.

Solo se añadieron artefactos de auditoría en esta carpeta. No se cambió código, anotaciones, adjudicaciones, dataset, sesión asignada, EPP, producción, SQLite operativo, modelos o pesos. No se ejecutaron entrenamientos, inferencias o pruebas de software ya aprobadas.
