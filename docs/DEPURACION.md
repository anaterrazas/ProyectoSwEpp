# Organización y depuración — 17/11/2026

## Depuración ejecutada

Se eliminaron 22 archivos de `media_backup_20261114_140925`, idénticos por ruta y
SHA-256 a los conservados en `media_backup`: **341.357.548 bytes** (325,54 MiB).
El manifiesto con hashes está en
`output/limpieza/piloto_respaldo_20261117.json`. No se borraron videos fuente,
datasets, etiquetas, pesos ni registros operativos. El respaldo conservado es
histórico; no debe confundirse con una copia actualizada de la base y sus medios.

Se normalizó `requirements.txt`, que combinaba UTF-16 mal formado y líneas ASCII.
Se conservaron las 44 dependencias y sus versiones. Se corrigió la ruta de pesos
del flujo web EPP a `Modelos/best.pt`, respetando el nombre real del directorio.

## Inventario de conservación

| Material | Estado de producto | Tratamiento |
|---|---|---|
| `ml/calidad_botellas/` | Herramientas reutilizables | Conservar |
| `datasets/calidad_botellas/v001/` | Referencia histórica y revisión de 19 recortes | Archivo de referencia; conservar etiquetas e imágenes vinculadas |
| `v002/tools/` | Captura y validación reutilizables | Conservar; código visible para Git |
| `v002/experiments/day1_v001/` | Clasificador de escena experimental; no supera baseline | Congelado como referencia, sin uso operativo |
| `v002/experiments/individual_v001/` | Detección/seguimiento experimental; calidad global no evaluable | Referencia para futura localización por unidad |
| `v002/experiments/detection_manual_v001/` | Anotador de ENVASE/TAPA | Herramienta activa del piloto de calidad |
| `datasets/publicos_calidad_botellas/raw/` | Fuentes y archivos de adquisición | Conservar hasta consolidar originales/importaciones |
| `datasets/publicos_calidad_botellas/imports/` | Datos y procedencia utilizados por experimentos | Conservar; no tratar etiquetas desconocidas como negativas |
| `datasets/publicos_calidad_botellas/audits/` | Auditorías históricas con referencias cruzadas | Archivo de evidencia; no borrar por antigüedad |
| `pruebas_ia/` | Mezcla de originales y salidas | Conservar fuentes; revisar salidas individualmente |
| `media/`, `db.sqlite3` | Estado operativo | Conservar y respaldar conjuntamente |
| `Modelos/best.pt`, `yolo11n.pt` | Dependencias activas | Conservar |

El archivo de experimentos es lógico: se conserva su ubicación para no romper
rutas relativas, manifiestos, hashes ni pruebas que dependen de ella. No se crearon
copias adicionales. `.gitignore` ahora permite versionar Python y documentos de
los experimentos y herramientas; los datos, pesos y resultados continúan ignorados.
Esto los hace visibles para Git, pero no crea un commit ni un respaldo remoto.

La siguiente reorganización física debe separar código y datos mediante rutas
configurables y probar cada consumidor antes de mover originales. Hoy no hay un
experimento que se pueda borrar entero solo porque no esté integrado en Django.

## Próximas reducciones condicionadas

1. Comparar contenido y dependencias de `raw/` e `imports/`; una coincidencia de
   imagen no permite borrar sus anotaciones, licencia ni archivo de procedencia.
2. Regenerar una auditoría a partir de sus entradas antes de descartar miniaturas
   o videos intermedios. Conservar su informe y receta de reproducción.
3. Retirar salidas exploratorias solo cuando ninguna prueba o informe las use.
4. Reconstruir el entorno en otra carpeta antes de considerar regenerable `venv/`.

No se hizo una eliminación masiva por extensión ni se sustituyeron archivos por
enlaces. Cada eliminación adicional necesita evidencia concreta de redundancia.
