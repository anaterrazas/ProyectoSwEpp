# Resultado de preparación del flujo de etiquetado

Se inspeccionaron visualmente los 19 recortes de ocho tracks y se generó una
vista conjunta en `output/calidad_etiquetado/inspection_overview.png`.
Se observaron reflejos, oclusiones y diferencias de nitidez. No se asignaron
etiquetas de defectos ni se declararon botellas conformes.

La herramienta local ofrece galería por botella/fotograma, ampliación, atributos
desconocidos, multietiqueta, borradores, segundo revisor, cierre y reapertura.
Guarda versiones JSONL nuevas con autor y fecha UTC. No modifica imágenes ni
`samples.jsonl`. La documentación de uso e incorporación está en `ETIQUETADO.md`.

## Validación

- Suite completa: 56/56 pruebas aprobadas, 82,530 segundos; 44 anteriores y 12
  nuevas. SQLite en memoria, multimedia temporal y migraciones deshabilitadas.
- Pruebas específicas de la versión final del servidor: 12/12, 1,219 segundos.
- `manage.py check`: sin problemas.
- Regresión del conteo: ocho botellas en 434 fotogramas, también al reprocesar.
- Guardados probados exclusivamente sobre copias temporales: múltiples defectos,
  desconocidos, contradicciones, revisión, reapertura, historial, conflictos,
  bloqueo concurrente, duplicados, integridad, exportación y controles HTTP locales.
- Playwright: galería real con 19 muestras, atributos inicialmente desconocidos,
  formulario y captura `output/playwright/etiquetado_galeria.png`.
- Espacio real inicializado sin etiquetas: revisión 0, 19 muestras pendientes.
- Hashes de producción, configuración, media, SQLite y extracción original
  idénticos antes y después. No se modificaron los archivos de la fase anterior.

El servidor solo se publica en 127.0.0.1; las identidades de anotador/revisor son
declaradas, no verificadas mediante Django. Respaldar la carpeta de revisiones.
No se entrenó ningún modelo, no hubo migraciones ni cambios a los registros reales.
