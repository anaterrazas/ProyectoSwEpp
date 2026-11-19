# Fase 2.6 · Adjudicación humana TAPA v4

## Estado

La revisión está disponible en `http://127.0.0.1:8010/demo/calidad/tapa-v4/`, enlazada desde Calidad. Requiere autenticación del laboratorio y permiso de consulta de Calidad; guardar exige además permiso para modificar inspecciones. **La preparación de la pantalla no equivale a adjudicación humana.** El estado real se obtiene de las versiones persistidas; no se rellenan decisiones automáticamente.

## Reutilización y alcance

Se reutilizan autenticación, permisos, CSRF, navegación y el servicio de archivos del laboratorio, la referencia con hashes de Fase 2.5 y las imágenes de contexto de la auditoría anterior. El lienzo conserva el patrón de coordenadas, ampliación y dibujo explícito del anotador manual existente. La revisión anterior de las 25 imágenes propias permanece independiente e intacta.

La nueva pantalla incluye siete accesos individuales (anotaciones 31, 123, 134, 204, 324, 567, 773), original sin alterar, cajas fuente, contexto con las anotaciones originales y recorte ampliado. Cada caja admite ENVASE, TAPA, NO EVALUABLE o PENDIENTE y una observación de visibilidad. No se desplazan ni redimensionan cajas originales. Las nuevas cajas deben dibujarse o introducirse con coordenadas por una persona, con clase y justificación explícitas; no se proponen cajas por IA.

## Exhaustividad

Se hizo una comprobación dirigida de escenas relacionadas, sin repetir la auditoría completa:

| Imagen | Referencia cap fuente | Observación técnica / pendiente humano |
|---|---:|---|
| 24 | 1 caja (76) | Tapas verdes visibles al fondo sin cajas específicas. |
| 38 | 1 caja (123) | Escena relacionada con 24; la caja abarca una botella y hay tapas de fondo sin cajas específicas. Corregir la clase de la botella no anota su tapa. |
| 42 | 1 caja (134) | Tapa verde visible en botella del lado izquierdo; la caja fuente está en otra región. |
| 95 | 1 caja (324) | Tapa verde visible en botella del lado izquierdo; la caja fuente está en otra región. |

Estas observaciones no son nuevas etiquetas ni coordenadas humanas. La cobertura del resto de imágenes no se declara completa: el selector permite revisar cualquiera de las 262. No se convierten las imágenes sin cajas cap en negativos. La exhaustividad es explícita por imagen: PENDIENTE, INCOMPLETA, NO EVALUABLE o COMPLETA. Declarar COMPLETA exige decidir todas sus cajas fuente, pero no acredita una segunda revisión ni elimina otras incertidumbres.

## Historial y nueva copia experimental

- `inicial/`: nueva representación candidata, basada en las 262 imágenes y 180 cajas fuente de Fase 2.5; las siete cajas señaladas aparecen pendientes en la representación de trabajo. Sus anotaciones originales permanecen completas en `source_annotations_cap`.
- `versiones/000001/`, etc.: cada guardado humano publica una generación completa con `decision.json`, `dataset.jsonl`, `estado.json` y `manifest.json`.
- Cada registro conserva identificador, clase y coordenadas fuente, clase adjudicada, justificación, autor declarado, cuenta autenticada, fecha UTC, SHA-256 de imagen y COCO, versión y hash de la decisión anterior.
- Las versiones contienen comprobaciones SHA-256 de archivos; no se sobrescriben. Se rechazan versiones obsoletas y guardados concurrentes. La publicación se hace mediante renombrado de carpeta completa; un fallo no deja una adjudicación parcialmente publicada.
- Las cajas retiradas de una revisión nueva siguen visibles en versiones anteriores. La justificación general debe explicar su retirada.
- Los enlaces de descarga usan un catálogo cerrado de cuatro nombres por versión. Las imágenes se resuelven por identificador contra el manifiesto y su hash; el cliente no proporciona rutas locales.

Las decisiones se integran en la **nueva copia experimental al guardar**, sin una segunda operación que pudiera sobrescribir las fuentes. El usuario puede descargar la última copia desde la pantalla. El JSON original de Roboflow y la Fase 2.5 no se modifican.

## Particiones e independencia

Se verificaron los hashes de las 262 imágenes y la geometría original se conserva. No hay duplicados exactos internos. Se mantienen 14 grupos completos: propuesta de entrenamiento 173 imágenes, validación 25, prueba 41 y pendientes 23. Se verificó por hash la restricción de los 202 grupos públicos anteriores.

Estas propuestas siguen **sin aprobar**: grupos de nombres/similitud no acreditan sesiones independientes. No hay evidencia nueva que resuelva la procedencia individual o independencia del material web/stock. Las 25 referencias propias no se usan para entrenamiento. No se alteran las particiones anteriores; las decisiones humanas nuevas se representan en generaciones experimentales nuevas.

## Verificación

Se ejecutaron 19 pruebas automatizadas: diez del flujo v4 y nueve de regresión de la adjudicación anterior. Pasaron sin errores; las pruebas de usuarios de regresión usaron una SQLite temporal en memoria, no la base operativa.

Chrome/CDP verificó las ocho imágenes de los siete conflictos más la imagen 24, sus recursos, contexto, selector de 262 imágenes, siete accesos, ausencia de expresiones de plantilla sin renderizar, acceso cerrado a archivos, rechazo CSRF y dibujo real en un borrador local. **No se envió ninguna decisión ni caja ficticia al registro humano.** Playwright CLI no estaba disponible en caché, por lo que se reutilizó el mecanismo Chrome/CDP del proyecto. Véase `verificacion_chrome.json`.

Al arrancar la actualización coexistieron el proceso de laboratorio anterior y el nuevo en el puerto 8010. Se verificaron sus comandos y se dejó un único servidor actualizado con `experimentos.pilotos.settings`, sin tocar procesos de producción. También se habilitó la ubicación del JavaScript exclusivamente en settings del laboratorio. No se cambiaron cuentas ni permisos.

La comparación con la línea base anterior verificó **26.361 archivos protegidos sin cambios**, incluido el material y resultados anteriores cubiertos por esa línea base. Resultado en `verificacion_integridad.json`.

## Archivos de implementación de esta fase

- Nuevos: `experimentos/pilotos/revision_tapa_v4.py`, `experimentos/pilotos/test_revision_tapa_v4.py`, `experimentos/pilotos/templates/demo/revision_tapa_v4.html`, `static/laboratorio/revision_tapa_v4.js`, `scripts/verificar_revision_tapa_v4.mjs`.
- Modificados: `experimentos/pilotos/urls.py` (rutas cerradas), `experimentos/pilotos/portal.py` (enlace solo en Calidad), `experimentos/pilotos/settings.py` (estáticos del laboratorio).
- Artefactos nuevos: únicamente esta carpeta experimental y sus versiones. No se modificó el módulo EPP, RAW, producción, SQLite operativo, pesos ni evaluaciones anteriores.

## Autorización de entrenamiento

**NO AUTORIZADO.** Primero debe verificarse la persistencia de las decisiones reales, el estado de exhaustividad de las imágenes revisadas y las referencias del conjunto reservado; además, sigue pendiente acreditar independencia y procedencia de los grupos de evaluación. Resolver siete clases no demuestra por sí mismo cobertura completa ni independencia. No se entrenó, no se ejecutó inferencia y no hay métricas nuevas de detección.
