# Importación pública sin alterar EPP

Los datos importados están en `datasets/publicos_calidad_botellas/`.
Consultar `INFORME_COMPATIBILIDAD.md` y `statistics.total.json` en esa carpeta.
No instalar Roboflow SDK ni proporcionar API keys para estos archivos locales.

```text
datasets/publicos_calidad_botellas/
├── raw/                       # archivos originales, README, licencia y metadatos
├── inspection/                # vista por clases de la inspección de Mendeley
├── imports/
│   ├── mendeley_kthmmbsh8t_v1_001/
│   └── roboflow_caps_v26_001/
│       ├── STATUS.json
│       ├── PROVENANCE_LICENSE.json
│       ├── statistics.json
│       ├── samples.public.jsonl
│       └── images/
│           ├── candidate_presence/
│           └── unmapped_review_only/
├── statistics.total.json
└── INFORME_COMPATIBILIDAD.md
```

Los candidatos llevan positivos parciales y desconocidos. No son decisiones
revisadas ni ejemplos aprobados para entrenar. No se añaden a la galería EPP ni
se representan como si pertenecieran a uno de sus análisis/tracks.

`public_sources.json` registra las fuentes verificadas y los mapeos explícitos.
El importador verifica proyecto, versión y licencia, valida imágenes y cajas,
rechaza rutas externas y compara SHA-256 contra la referencia EPP y las anteriores
importaciones completas. Los duplicados conservan su evidencia y una referencia
a la imagen anterior; no se copia otra imagen ni se sobrescriben manifiestos.
No convertir Good Cap ni la ausencia de anotaciones en un negativo o CONFORME.

Ejemplo para una NUEVA exportación verificada (usar siempre salida nueva):

```powershell
.\venv\Scripts\python.exe -B -m ml.calidad_botellas.import_public `
  --dataset-id roboflow_bottle_v4 `
  --input datasets/publicos_calidad_botellas/raw/roboflow_bottle_v4/extracted `
  --format coco `
  --output datasets/publicos_calidad_botellas/imports/roboflow_bottle_v4_001
```

No hace falta ejecutar ese ejemplo ahora: falta la exportación de esa fuente.
Descargar desde Roboflow Universe en formato COCO JSON y dejar el ZIP en Descargas.
Antes de extraer, verificar README, licencia y versión, rechazar miembros con
traversal/enlaces y limitar tamaño. No extraer archivos públicos en `media`, en
el código de producción ni sobre las 19 imágenes originales.

El importador acepta YOLO de detección (cinco columnas) o COCO de Roboflow con
`_annotations.coco.json`. No admite implícitamente segmentación, inferencias
generadas ni clases no documentadas como si fueran equivalentes.

Pruebas del importador:

```powershell
.\venv\Scripts\python.exe -B -m unittest ml.calidad_botellas.test_import_public -v
```

Las imágenes y etiquetas artificiales de esas pruebas existen solo en carpetas
temporales. No entran en la importación ni se usan como datos reales.
