# Geometría oficial TAPA v1 · auditoría y edición humana

## Resultado

El criterio confirmado queda documentado en `docs/PROTOCOLO_TAPA_GEOMETRIA_v1.md`: **toda la tapa visible y su anillo de seguridad unido; excluir cuello, rosca y cuerpo**. No se adoptó la convención amplia de ROI de v26 como si ya cumpliera ese criterio.

| Criba técnica de las 272 ROI v26 | Cajas |
|---|---:|
| CONSERVAR | **4** |
| REQUIERE AJUSTE HUMANO | **268** |
| NO EVALUABLE por visibilidad del objeto | **0** |

Las cuatro conservables son los **índices de inspección v26 054, 147, 224 y 238**, no identificadores COCO ni imágenes v4. Sus regiones cubren la tapa y banda unida y no se prolongan hasta la brida/cuello como las ROI amplias. Los límites se contrastaron ampliados; sus detalles están en `detalle/` y sus identificadores fuente completos en `catalogo.json`.

Las demás regiones localizan una tapa visible, pero incluyen cuello/brida/contexto innecesario o requieren confirmar un borde conforme al protocolo. Se envían a intervención humana; **no se exige modificar una caja que la persona pueda justificar como CONSERVAR**. La clasificación es una criba técnica provisional del asistente, no una adjudicación humana nueva ni una segunda revisión independiente.

NO EVALUABLE=0 no significa dataset validado: en estas fotos grandes se puede localizar el objeto y preparar un ajuste; no se descartaron tapas rotas por estar rotas. La persona puede registrar NO EVALUABLE si su revisión encuentra evidencia insuficiente. No se generaron coordenadas corregidas ni se propagó un ajuste entre fotos parecidas.

## Método y alcance

Se reutilizaron las 14 hojas de las 272 regiones y las seis hojas de escenas completas verificadas en Fase 2.9, junto con sus hashes. La revisión se centró ahora en el borde tapa/anillo frente a cuello/brida, y se ampliaron doce casos próximos al límite. Los recortes son vistas derivadas para inspección, no cambios de imagen ni cajas propuestas por un detector. La decisión conserva el origen de cada caja.

En una vista inclinada, un rectángulo alineado con la imagen contendrá inevitablemente espacios de fondo o porciones proyectadas de otras superficies. El criterio operativo es no ampliar sus extremos para abarcar el cuello, no prometer una segmentación de píxeles. Si no se distingue la unión del anillo, no se inventa: la persona debe conservar la duda o NO EVALUABLE.

## Herramienta funcional

URL: **http://127.0.0.1:8010/demo/calidad/tapa-geometria/**

Se enlaza desde Calidad, reutilizando autenticación, permisos, navegación, servicio de imágenes y el patrón de historial del laboratorio. La página anterior de adjudicación v4 y sus decisiones permanecen intactas.

Incluye las 272 ROI v26 y las doce reservas v4. Permite filtrar por la criba técnica o por ausencia de decisión humana; abrir original, ver el contexto de la ROI, ampliar, dibujar manualmente un rectángulo o introducir cuatro coordenadas. Cambiar vista/zoom no cambia coordenadas de anotación. La caja verde inicial es una copia de trabajo del original, no una corrección del sistema.

Decisiones explícitas:

- **CONSERVAR:** solo acepta las coordenadas originales.
- **AJUSTADA:** requiere coordenadas distintas e indicación de edición humana explícita; no calcula ni sugiere nuevos límites.
- **NO EVALUABLE / PENDIENTE:** no llevan caja adjudicada ni se convierten en negativos.

Cada guardado añade un JSON nuevo en `decisiones/` con autor real declarado, cuenta autenticada, fecha UTC, justificación, visibilidad, caja fuente, caja humana, hash de imagen, hash del protocolo, revisión, hash del registro anterior y sello del contenido. Se rechazan revisiones obsoletas y guardados concurrentes. Se valida que la caja tenga área, coordenadas finitas y límites de imagen; no se hace clipping ni ajuste automático.

La descarga **«copia experimental con decisiones persistidas»** deriva la versión de trabajo desde las últimas decisiones sin cambiar el RAW, el catálogo técnico o las versiones anteriores. La copia mantiene entrenamiento deshabilitado. El estado del informe y `dataset_revision_inicial.json` reflejan el momento de entrega; las decisiones humanas posteriores se consultan en la herramienta.

## Reserva v4: geometría, procedencia e independencia

Se revisaron las doce imágenes (11,40,65,75,88,102,126,142,171,204,231,259) en seis pares. La tapa es visible, pero el criterio nuevo obliga a confirmar sus límites y la unión del anillo; algunos bordes fuente dejan fuera parte de la base o abarcan una zona que podría ser cuello. Se incluyen en la misma herramienta como casos 272–283, pendientes de confirmación/ajuste humano. No se declaran doce errores nuevos ni se inventan sus coordenadas correctas.

La evidencia disponible acredita la exportación **Bottle Defect Detection v4**, publicación Spark Intelligence y licencia registrada CC BY 4.0. Se mantienen sus hashes, README, COCO y adquisición. No acredita una URL original ni una sesión de captura por fotografía.

Comprobación adicional de metadatos de las doce:

- No hay campos EXIF de origen en ninguna.
- El COCO asigna `license: 1`, correspondiente a CC BY 4.0.
- Todas tienen `date_captured = 2023-12-06T20:02:35+00:00`, idéntico a `info.date_created` del export. No se usa ese valor como evidencia de doce capturas o fechas de sesión.
- `info.url` apunta a una ruta genérica `object-detection/undefined`, que no recupera las fuentes originales. Se conserva la URL de la publicación verificada; no se inventan enlaces individuales.
- Se mantienen seis grupos de dos variantes; las doce imágenes no son doce orígenes independientes.
- La auditoría previa de la combinación no encontró coincidencias estrictas entre fuentes/grupos. Eso no prueba independencia de adquisición o identidad física.

**Test independiente aprobado: 0 imágenes.** No se resuelve esta carencia con el cambio de geometría. No se infieren derechos adicionales por ausencia de marcas de agua. Las 25 referencias propias siguen fuera por autorización pendiente.

## Pruebas e integridad

Nueve pruebas automatizadas verifican originales, copia derivada, guardado de coordenadas humanas sin transformación, rechazo de ajuste implícito, protocolo, validación, estados no evaluables, historial/versiones, detección de alteraciones, fallo de publicación, permisos, CSRF y catálogo cerrado de imágenes. Todos los guardados de prueba se realizaron en fixtures aislados, eliminados al terminar; no son adjudicaciones reales.

Chrome/CDP verificó ocho casos de ambas fuentes, imagen original, JavaScript, dibujo manual, rechazo de acceso a casos inexistentes, CSRF y geometría fuera de imagen. La prueba de dibujo se descartó localmente; la petición inválida recibió 400. Ninguna adjudicación ficticia se envió con éxito. La vista móvil se comprobó a 390 píxeles sin desbordamiento horizontal. Playwright CLI no estaba disponible en caché; se reutilizó Chrome/CDP del proyecto.

Se recargó únicamente el servidor de laboratorio con `experimentos.pilotos.settings`. No se cambió ninguna cuenta ni permiso. No se modificaron EPP, producción, SQLite operativo, pesos, datasets previos ni evaluaciones. El resultado de hashes y manifiestos se detalla en `verificacion_integridad.json`.

## Archivos de implementación

- Nuevo protocolo: `docs/PROTOCOLO_TAPA_GEOMETRIA_v1.md`.
- Nuevos: `experimentos/pilotos/geometria_tapa.py`, `experimentos/pilotos/test_geometria_tapa.py`, `experimentos/pilotos/templates/demo/geometria_tapa.html`, `static/laboratorio/geometria_tapa.js`, `scripts/verificar_geometria_tapa.mjs`.
- Modificados solo en laboratorio: `experimentos/pilotos/urls.py` y el enlace de la rama Calidad en `experimentos/pilotos/portal.py`.
- Artefactos nuevos únicamente en esta carpeta experimental. Las versiones humanas futuras se añadirán por separado.

## Preparación final del dataset

**NO PREPARADO PARA ENTRENAMIENTO.** Quedan 268 intervenciones geométricas v26, confirmación de los límites de las doce reservas y un test con procedencia/independencia justificadas. Las cuatro conservables no bastan por sí solas para construir una evaluación defendible. Se mantiene la propuesta por grupos y las particiones anteriores, sin partir secuencias para completar artificialmente un test.

El siguiente paso es usar la cola de ajuste humano y guardar las decisiones reales. No hace falta repetir las adjudicaciones de clase ya guardadas ni alterar RAW. No se entrenó ni se ejecutaron inferencias. El protocolo elimina el bloqueo de definición geométrica; los ajustes y la referencia de prueba siguen abiertos.
