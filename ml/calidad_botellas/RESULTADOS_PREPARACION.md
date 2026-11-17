# Resultado de la primera fase

Extracción real independiente del análisis 3, lote 1. Fuente: video original,
SHA-256 `93b17306b5e2dcd9467c1dc1d507dc85431021cbfe1bc808efea0badac338e08`.
Ejecución `502b6eb7-cf3b-429f-b1c3-a4f7bbeeb8ec`.

| Verificación | Resultado |
| --- | --- |
| Fotogramas | 434 |
| Conteo de auditoría | 8 |
| IDs contabilizados | 1, 2, 3, 4, 15, 23, 32, 35 |
| Recortes PNG | 19, con cobertura de los 8 IDs |
| Candidatos omitidos por similitud/proximidad temporal | 1160 |
| Vistas reemplazadas por otra de mejor calidad técnica | 366 |
| Avisos técnicos | 19 PASS con los umbrales iniciales; no equivale a conformidad |
| Etiquetado | 19 PENDING, defectos y evaluabilidad en null |
| Partición | UNASSIGNED en todas las muestras |
| Validación de integridad del dataset | OK |
| Validación --ready | Rechazo esperado: falta anotación humana |
| Suite completa | 44/44, 72,790 segundos |
| manage.py check | Sin problemas |

Las 40 pruebas existentes y las cuatro nuevas se ejecutaron con SQLite en memoria,
migraciones deshabilitadas y multimedia temporal. La regresión del flujo Django
real obtuvo ocho botellas en 434 fotogramas y conservó el resultado al reprocesar.
La nueva prueba verificó además los IDs, los píxeles originales del recorte,
deduplicación, límites, rechazo de sobrescritura, asociaciones inválidas,
integridad, etiquetas pendientes y fugas de datos.

Los hashes del código de produccion/config, SQLite y los 28 archivos de media
coinciden antes y después. No se cambió el conteo ni el algoritmo, pesos o
configuración de YOLO11n/ByteTrack. No hubo migraciones ni escritura de registros.

## Evidencia y limitaciones

El dataset está en `datasets/calidad_botellas/v001/runs/referencia_a3`.
Contiene `run.json`, `samples.jsonl` e `images/unlabeled/*.png`.
Los recortes no incluyen las anotaciones dibujadas por YOLO.

La inspección visual de ejemplos de los IDs 1, 15 y 35 muestra reflejos,
oclusiones, diferencias de nitidez y visibilidad parcial de algunas regiones.
El filtro técnico no evalúa la visibilidad semántica de la tapa ni garantiza
resolución suficiente para rayaduras. Es obligatorio revisar esas condiciones
antes de etiquetar. No asignar CONFORME porque una imagen tenga estado PASS.

Esta muestra valida la herramienta y su compatibilidad con CU-09; no valida un
modelo de calidad ni constituye un conjunto suficiente para entrenar. No se
realizó clasificación automática ni entrenamiento. Se requiere autorización
independiente antes de continuar con esa fase.
