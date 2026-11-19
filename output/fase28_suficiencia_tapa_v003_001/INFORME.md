# Fase 2.8 · Auditoría de suficiencia TAPA v003

**Estado: NO PREPARADO para entrenamiento con una evaluación independiente defendible.** Se encontró un núcleo visual de bajo costo de revisión, pero no evidencia suficiente para afirmar que permita evaluar detección en video. No se entrenó ni se ejecutaron inferencias.

## Qué cambió desde Fase 2.7

- Hay 11 versiones reales. La nueva versión 11 cambia imagen **9 a COMPLETA**; ese bloqueo está resuelto. El v003 anterior permanece congelado en versión 10, sin sobrescribirlo.
- **24:** no existe decisión guardada entre los registros encontrados. Se revisaron los registros locales `decision.json` y el mecanismo de guardado; el cliente no conserva borradores en almacenamiento persistente. No se recuperó una decisión ni se inventó una. Los archivos derivados que contienen la imagen no son adjudicaciones.
- **38 y 165:** siguen COMPLETA con notas que afirman tapas visibles, cero cajas nuevas y sin caja TAPA después de reclasificar sus únicas cajas como ENVASE. Son omisiones pendientes, no decisiones que pueda completar el sistema.
- **60:** 203 confirma una tapa y 204 excluye una etiqueta; el estado global NO EVALUABLE no aclara si afecta solo a la etiqueta o toda la imagen. Se conserva el positivo local y el estado global, sin decidir por la revisora.

Estas últimas imágenes pueden quedar fuera de una primera selección: corregir todo el dataset no es una condición para estudiar un subconjunto distinto. No hace falta repetir los siete cambios de clase.

## Auditoría de las 262 imágenes

Se reutilizaron `inspect_image` y las huellas del auditor existente, y se comprobaron las 262 imágenes contra SHA-256, dimensiones y decodificación. Todas coinciden. Hay 262 hashes únicos y 180 cajas fuente geométricamente válidas. La geometría no valida semántica.

Se compararon 34.191 pares de imágenes. Se reprodujeron los 60 pares de similitud estricta, sin cruces entre los 14 grupos. Hay dos discrepancias de cajas TAPA: **24/38** y **160/184**. Son alertas verificables, no predicciones ni propuestas de coordenadas. El segundo caso muestra una tapa verde anotada en 160 y sin caja en la vista muy similar 184.

Una búsqueda más amplia produjo la alerta entre 248 y 259. Su inspección muestra fotos de botellas/productos distintos; la semejanza de silueta no justifica unir sus grupos. Tampoco se interpretan dos marcas iguales como una misma sesión. Se mantienen los grupos previos.

Se inspeccionaron 22 hojas que incluyen las 262 imágenes y se ampliaron casos dirigidos. Se encontraron **31 imágenes con omisiones visuales**, registradas individualmente en `observaciones_visuales.json`, con galería para comprobarlas. Ejemplos: 63 tiene una tapa verde central sin caja; 131 tiene tapa y ninguna caja cap; 123 tiene dos botellas y una sola tapa anotada; 245 muestra seis botellas con tapas y una sola caja; 163 deja tapas laterales sin cajas. Este número es un mínimo de incidencias de la criba, no una certificación de exhaustividad del resto ni un recuento de tapas faltantes.

La secuencia de la cinta pequeña contiene tapas sueltas/piezas verdes y objetos parcialmente visibles; su alcance requiere protocolo. No se convierten bocas, anillos o piezas ambiguas en tapas. Imágenes recortadas al cuerpo como 62 y 202 no son negativos confirmados. Las 114 imágenes de v4g02 conservan cero TAPA positivas tras adjudicación; no interesa revisar manualmente esas 114 antes de aprovechar positivos de otros grupos y no se incorporan automáticamente como negativos.

El detector técnico marcó nueve posibles desenfoques, nueve fondos muy claros y un fondo muy oscuro. Son señales para priorizar. En fotos de producto, un fondo blanco y un Laplaciano global bajo no prueban que la tapa esté desenfocada o mal expuesta; no se rechazaron automáticamente esas imágenes.

## Cajas y clases

- **173 TAPA candidatas**, una con nueva adjudicación humana (203) y 172 conservadas de fuente. No se presentan como 173 cajas humanas nuevamente validadas.
- **3 ENVASE**: 31, 123 y 567; sirven como correcciones de trazabilidad, no como dataset exhaustivo de envases.
- **4 NO EVALUABLE**: 134, 204, 324 y 773, conservadas fuera de positivos. TOTAL de visibilidad no cambia la clase excluida: en 204 y 773 la nota describe etiqueta/boca, no una tapa oculta.
- Cero cajas nuevas humanas y ninguna corrección automática de coordenadas.
- Las decisiones humanas identifican **cinco regiones fuente incompatibles con TAPA**: 31, 123 y 567 son envases; 204 es una etiqueta; 773 es boca/cuello. En 134 y 324 persiste duda visual. Se distinguen esos cinco errores de clase de los dos casos ambiguos; los siete dejan de ser positivos TAPA.
- El núcleo técnico descrito abajo tiene **12 cajas TAPA visualmente compatibles** y geométricamente válidas, sin anotaciones nuevas; eso no acredita una adjudicación humana ni prueba la exhaustividad de objetos pequeños fuera del alcance observado.
- TAPA_DEFECTUOSA, TAPA_AUSENTE como defecto, RAYADURA y DEFORMACION no se habilitan. `no-cap` no prueba defecto posterior al tapado.

## Particiones vigentes: conservadas, no aprobadas

| Partición actual | Imágenes | TAPA | ENVASE | NO EVALUABLE |
|---|---:|---:|---:|---:|
| train | 173 | 76 | 1 | 1 |
| validation | 25 | 36 | 0 | 1 |
| test | 41 | 41 | 0 | 2 |
| PENDIENTE | 23 | 20 | 2 | 0 |

Se verificó por hash la restricción de los 202 grupos anteriores. La auditoría no añade imágenes ni desplaza ninguna entre particiones históricas. Los 14 componentes son grupos conservadores de archivo/similitud, no 14 sesiones certificadas. v4g01 y v4g04 mezclan imágenes de web/producto; v4g03 mezcla al menos dos entornos de línea visibles. Ausencia de duplicados exactos no prueba independencia de fuente.

## Núcleo mínimo de bajo costo encontrado

**12 imágenes, 12 cajas, 6 grupos completos:** v4g05 (11,75), v4g07 (40,259), v4g09 (65,88), v4g12 (102,204), v4g13 (126,231), v4g14 (142,171). Cada par muestra una variante de un motivo visual, una tapa anotada y ninguna omisión evidente en esta inspección. Las cajas tienen lado menor de aproximadamente 31 a 89 píxeles a resolución 640. No hay ejemplos de tapas pequeñas de línea ni multienvase en este núcleo.

La propuesta nueva, separada de las particiones históricas, asigna cuatro grupos completos a entrenamiento (**8 imágenes / 8 tapas**), uno a validación (**2 / 2**) y uno a prueba (**2 / 2**). Se entrega en `subconjunto_minimo_candidato.jsonl` y `plan_minimo_por_grupos.json`, con aprobación deshabilitada. No incluye las referencias propias con derechos pendientes, ni los grupos de imágenes conflictivas.

Esto **no es un mínimo estadístico universal ni un conjunto suficiente para evaluar un detector de video**. Solo hay seis motivos visuales, y validación/prueba tendrían un motivo cada una con dos variantes correlacionadas. Puede reducir a seis pares la verificación inicial del recorrido de datos, pero una ejecución sobre ese núcleo mediría principalmente memorización y transferencia entre fotos de producto, no generalización a una línea. Ninguna imagen queda aprobada para entrenar en este informe.

## Procedencia y bloqueos

La exportación v4 tiene licencia CC BY 4.0 registrada y verificada en la auditoría previa; se conserva esa evidencia. La criba encontró marcas de terceros, incluidas Picxy, Adobe Stock, Dreamstime, Alamy, Shutterstock, Getty Images y COLOURBOX. Son alertas concretas de procedencia individual, no una conclusión legal ni prueba de que todo el dataset carezca de derechos. No se inventan enlaces o autorizaciones.

El núcleo evita las imágenes con esas marcas observadas, pero **no ver una marca no acredita derechos ni independencia**. Falta documentar el origen de los seis motivos para certificar separación independiente. Además, un test de un solo motivo es estadísticamente insuficiente para sostener precisión/recall generalizables. La cobertura no puede inferirse de hashes, clases o semejanza.

## Camino más corto recomendado

1. Mantener en cuarentena los grupos conflictivos y el grupo de 114 imágenes sin TAPA positiva, sin borrarlos ni dedicarles una nueva anotación masiva.
2. Utilizar la galería de los **seis pares** para confirmar conjuntamente cajas existentes, alcance de TAPA y procedencia. No hace falta dibujar de nuevo cajas que ya sean correctas ni revisar manualmente las 262 imágenes.
3. Si solo se desea verificar la canalización, acordar explícitamente ese alcance restringido del núcleo; no llamarlo evaluación independiente del detector de video. Este informe no ejecuta ni autoriza entrenamiento.
4. Para un entrenamiento respaldado por evaluación del objetivo real, cerrar exhaustividad y procedencia de grupos de escenas relevantes adicionales antes de reservar validación/prueba. No se fija un número mágico de imágenes: deben existir suficientes escenas realmente distintas y cobertura de tamaños/contextos. Los datos actuales ofrecen escenas potenciales, pero no están aún certificadas. Priorizar los grupos existentes antes de solicitar nuevas capturas.

La imagen 9 está resuelta. 24,38,165 y60 siguen pendientes para el cierre global, pero no bloquean por sí mismas estudiar el núcleo que las excluye. El bloqueo restante de ese núcleo es su alcance estadístico/de dominio y la independencia/procedencia, no aquellas cuatro imágenes. Se mantienen NO EVALUABLE y desconocidos; no se inventan negativos ni métricas.
