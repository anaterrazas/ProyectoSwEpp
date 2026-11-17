# Preparación offline del dataset de calidad

Esta fase solo extrae evidencia real y prepara etiquetas humanas. No existe un
clasificador, entrenamiento, migración ni escritura en la base real. Los archivos
de producción, YOLO11n, ByteTrack y el conteo CU-09 permanecen intactos.

Leer primero [el protocolo](PROTOCOLO_CAPTURA.md) y [la taxonomía](taxonomy.json).
Dependencias: el entorno existente (Python, OpenCV, NumPy, Ultralytics, PyTorch,
Django e imageio-ffmpeg). No instalar ni actualizar dependencias para esta fase.

## Extracción

Desde la raíz del proyecto, usar un directorio de salida NUEVO y el original
correspondiente al análisis. Para el ejemplo verificado del análisis 3:

```powershell
.\venv\Scripts\python.exe -B -m ml.calidad_botellas.extract_crops `
  --video media/produccion/videos/produccion_X98Znra.mp4 `
  --analysis-id 3 `
  --output datasets/calidad_botellas/v001/runs/nueva_captura_a3
```

No volver a ejecutar el comando sobre la misma salida: falla sin sobrescribirla.
Se rechazan salidas dentro de `media` o de la carpeta del video. El video pasa
por la validación ya existente. El UUID identifica esta nueva ejecución de
seguimiento, que NO es la ejecución histórica del análisis en Django.

El extractor usa los mismos parámetros actuales: yolo11n.pt, clase 39,
confianza 0,30, imgsz 640, bytetrack.yaml, persist/stream, CPU, save=False.
Guarda hash de pesos, configuración del tracker y versiones. No modifica pesos,
no descarga un modelo ausente ni llama a las vistas de producción. El conteo de
auditoría reproduce la regla de primer fotograma y cruce derecha-izquierda para
seleccionar los tracks pertinentes; no sustituye el conteo operativo ni sus datos.

Límites adicionales: hasta 200 tracks observados y 128 MiB de PNG seleccionados
en memoria. Un fallo conserva `run.json` con `FAILED`; no reutilizar esa ejecución.
La selección por pHash opera dentro de cada track; cambios de identidad y casi
duplicados entre tracks/ejecuciones requieren revisión humana. Duplicados PNG
exactos se omiten en una ejecución y se detectan al validar varias juntas.

## Estructura creada

```text
datasets/calidad_botellas/v001/runs/<captura>/
├── run.json                  # procedencia, opciones, versiones, cobertura y conteo
├── samples.jsonl             # una fila por imagen; etiquetas inicialmente null
└── images/
    ├── unlabeled/            # calidad técnica PASS, todavía SIN etiqueta
    └── review/               # avisos técnicos; nunca defecto simulado
```

No se asignan train/val/test automáticamente: todas las muestras empiezan como
`UNASSIGNED`, evitando dividir vistas de una misma botella por error.

## Etiquetado humano

Editar una copia versionada de `samples.jsonl` o importarla mediante un adaptador
a una herramienta de anotación multietiqueta. No cambiar hashes, coordenadas ni
campos de procedencia. Mantener las imágenes intactas. El JSONL es el formato de
intercambio propio del proyecto, no un export YOLO estándar.

1. Completar `capture_session_id` y `physical_bottle_id` desde el registro de
   captura. El ID de track por sí solo no prueba identidad física estable.
2. Revisar imagen y original; marcar `evaluable.body` y `evaluable.cap` como
   true/false. No asumir que PASS significa regiones completamente visibles.
3. Etiquetar cada defecto: 1 presente, 0 ausente tras inspección suficiente,
   null desconocido. Por ejemplo, una tapa oculta queda desconocida, no correcta.
4. Usar múltiples positivos cuando corresponda. Registrar `other_defect=true`
   si hay daño fuera de taxonomía y escalarlo a calidad. No marcar conforme.
5. RAYADURA: daño superficial; excluir reflejos, gotas, uniones y diseño.
   DEFORMACION: desviación de forma frente a referencia del mismo producto y
   perspectiva, no distorsión óptica. TAPA_DEFECTUOSA: daño, mala colocación o
   ausencia cuando la etapa requiere tapa. El código sin acento es estable.
6. CONFORME es una conclusión humana derivada: todas las regiones necesarias
   evaluables, defectos conocidos ausentes y ningún otro defecto. No significa
   conformidad dimensional, hermeticidad o calidad de superficies no visibles.
   NO_EVALUABLE expresa insuficiencia de evidencia y puede coexistir con un
   defecto conocido en otra región. No crear clases mutuamente excluyentes.
7. Completar `annotator`, pasar a `ANNOTATED`, registrar un segundo `reviewer`
   y pasar a `REVIEWED` tras resolver discrepancias. Crear una copia versionada
   para cada ronda; conservar la anterior como historial. No escribir estos datos
   en `InspeccionCalidad` todavía.
8. Asignar particiones por grupos. No duplicar una imagen en varias carpetas por
   tener múltiples defectos ni convertir null en 0.

## Validación sin cambios

```powershell
.\venv\Scripts\python.exe -B -m ml.calidad_botellas.validate_dataset `
  datasets/calidad_botellas/v001/runs/referencia_a3
```

Comprueba decodificación, dimensiones, hashes, asociación, cajas, conteos, límites,
etiquetas y fugas entre particiones. Acepta varias carpetas como argumentos para
detectar duplicados y fugas entre ejecuciones. Para un dataset anotado usar
`--ready`; el ejemplo sin etiquetar debe fallar esa comprobación. Esto no entrena
ni certifica la corrección semántica de las anotaciones. Ejecutar sobre TODAS las
carpetas seleccionadas antes de consolidar el dataset.

## Pruebas

```powershell
.\venv\Scripts\python.exe -B -m unittest ml.calidad_botellas.test_preparation -v
```

Prueba selección, deduplicación, calidad técnica, integridad, procedencia y video
real: ocho botellas, 434 fotogramas. Las matrices artificiales existen solo dentro
de pruebas unitarias y nunca se exportan como datos reales. La regresión CU-09
existente se ejecuta además con SQLite de prueba en memoria y multimedia temporal.
No ejecutar las pruebas contra SQLite real ni extraer desde el video con overlays.

El siguiente paso requiere autorización independiente. No entrenar ni integrar
clasificaciones automáticas a partir de esta demostración.
