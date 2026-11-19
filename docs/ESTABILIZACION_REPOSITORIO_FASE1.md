# Estabilización del repositorio – Fase 1 (auditoría y plan)

Fecha: 2026-11-18. Rama `inicio-epp`. Alcance: solo lectura. No se modificó código, datos, SQLite, pesos ni configuración; no se instaló nada; no se ejecutó ninguna suite de tests ni inferencia. Único comando de ejecución: `manage.py check` (sin incidencias). Contexto general: `docs/CONTEXTO_MAESTRO_PROYECTO.md`.

## 1. Hallazgos

### 1.1 Git
- Un único commit (`d019bb0c`). 6 archivos modificados y 36 rutas sin seguimiento. Rastreados: 142 archivos.
- Modificados: `.gitignore`, `monitoreo/{views.py,urls.py,tests.py}`, `monitoreo/templates/monitoreo/camaras.html`, `requirements.txt`.
- Sin seguimiento (código y documentación valiosos): `CLAUDE.md`, `README.md`, `config/pilotos.json`, `docs/`, `experimentos/`, `scripts/`, `static/`, `seguridad/{piloto.py,test_piloto.py}`, `monitoreo/piloto.py`, 2 plantillas nuevas de `monitoreo`, `.claude/`.
- Sin seguimiento (artefactos): ~17 carpetas `output/*` (informes de fases, auditorías), `pruebas_ia/referencia_epp_2026-11-18T01-19-39.310Z.json`, `pruebas_ia/Bottle Defect Detection.v4i.coco.zip`, `datasets/` (parcialmente).
- Pesos rastreados: `Modelos/best.pt` y `yolo11n.pt` están en el commit, aunque `Modelos/` figura en `.gitignore` (el ignore no afecta a archivos ya rastreados). Cualquier `git add -A`/`commit -a` seguiría rastreándolos; quedan versionados como binarios.
- `produccion/` está rastreado y sin cambios; `monitoreo/` es donde está el trabajo nuevo.
- Peso en disco: `datasets` 2249 MB, `output` 1076 MB, `pruebas_ia` 389 MB, `media` 360 MB, `media_backup` 326 MB, `venv` 1282 MB, `Modelos` 50 MB.

### 1.2 Archivos de alto valor que NO están en Git ni tienen copia
Ignorados por `.gitignore` o sin seguimiento; un `git clean` o un fallo de disco los perdería:
- `datasets/calidad_botellas/v002/experiments/detection_manual_v001/{dataset_tapa_adjudicado_fase23_001,revision_tapa_fase21_001}/` y `individual_v001/`, `day1_v001/` (anotaciones y adjudicaciones humanas, ~617 MB en `datasets/calidad_botellas`).
- `output/experimental_pilotos/` (439 MB: SQLite del laboratorio, `acceso_local.json`, revisiones). Ignorado por diseño; se pierde en un clon.
- Videos originales `pruebas_ia/*.mp4` (ignorados) y `media/`.
- `db.sqlite3` (operativa) y dos `db_backup_20261114_*.sqlite3`: ignorados, solo existen en esta carpeta.
- `pruebas_ia/referencia_epp_*.json` (referencia EPP de 33 fotogramas) está sin seguimiento ni ignorado.

### 1.3 Temporales y duplicados
- `media_backup/` (326 MB), `db_backup_*.sqlite3` x2, `bus.jpg` (imagen de ejemplo de Ultralytics), `runs/` (1 MB), `__pycache__`. Ignorados salvo `bus.jpg` (rastreado).
- `output/tests/` está vacío (los tests limpian sus temporales).
- `.claude/` sin seguimiento: contiene las skills del proyecto (conviene versionarla, excluyendo configuración local).

### 1.4 `requirements.txt` (corrige la hipótesis inicial)
- No se perdieron paquetes. El archivo en HEAD estaba **corrupto por codificación mixta**: UTF-16 con las 2 últimas líneas (`imageio-ffmpeg==0.8.1`, `lap==0.5.14`) añadidas en ASCII, de modo que no era legible por `pip`. La versión actual es ASCII/CRLF, 44 líneas, contiene los mismos paquetes (incluidas esas dos) y es válida.
- Instalado en `venv` (pip list) coincide con las versiones fijadas para Django 5.2.19, ultralytics 8.4.212, torch 2.15.0, torchvision 0.29.2, opencv-python 5.0.0.93, numpy 2.5.4, lap 0.5.14, imageio-ffmpeg 0.8.1, pillow 13.0.0, matplotlib 3.11.2. `pip check`: sin incompatibilidades.
- Imports de terceros usados en el código: `django`, `cv2`, `ultralytics`, `numpy`, `imageio_ffmpeg`, `PIL`. Todos cubiertos. `lap` lo exige ByteTrack (no se importa directamente).
- Observaciones (sin acción): `polars`, `matplotlib`, `psutil`, `nvidia-ml-py`, `ultralytics-platform` son dependencias transitivas/auxiliares de ultralytics; el proyecto corre solo en CPU. `ultralytics-platform` no es un import del proyecto (no verificado por qué está fijado). Se recomienda separar `requirements.txt` (runtime) de dependencias de laboratorio en una fase posterior, no ahora.
- Veredicto: **simplificado/corregido correctamente**. Confirmar el cambio con un commit propio.

## 2. Estado de pruebas

| Elemento | Estado | Evidencia |
|---|---|---|
| `manage.py check` | OK, 0 incidencias (ejecutado hoy) | salida de consola |
| `monitoreo/tests.py` (4 tests) | Ejecutado antes (10 tests de monitoreo+seguridad OK). Simula `YOLO` con `patch` en los tests de `analizar_camara`; escribe un video sintético con `cv2.VideoWriter` en carpeta temporal | `monitoreo/tests.py:67,73,88` |
| `seguridad/tests.py` | Archivo de 3 líneas (vacío en la práctica) | `seguridad/tests.py` |
| `seguridad/test_piloto.py` (52 líneas) | Ejecutado antes dentro de los 10. Sin YOLO ni cv2 | grep |
| `experimentos/pilotos/` (13 `test_*.py` + `tests.py`, ~38 tests) | **No ejecutados hoy.** Descubribles por patrón `test*.py` y `__init__.py` presentes (inferencia) | `experimentos/pilotos/` |
| `produccion/` (5 archivos de test, ~710 líneas) | **No ejecutados ni auditados antes.** Ver 3 | `produccion/test*.py` |

### Qué ejecuta inferencia, video o datos reales
1. **INFERENCIA REAL (confirmado por lectura):** `produccion/tests.py::FlujoProduccionTests.test_video_real_y_reprocesamiento` (línea 30 en adelante). Crea un análisis con `pruebas_ia/produccion.mp4` (2.9 MB, original no versionado) y llama a `procesar_analisis`, que en `produccion/views.py:133` carga `YOLO(yolo11n.pt)` y procesa 434 fotogramas en CPU (el test comprueba `cantidad_contada == 8`). No hay `patch` de YOLO en ese test (los otros del archivo sí lo parchean, p. ej. línea 86). Aísla `MEDIA_ROOT` con `TemporaryDirectory` y la BD de test de Django, de modo que no escribe en `db.sqlite3` ni `media/`; lee `yolo11n.pt` y el video (solo lectura). También ejecuta ffmpeg real vía `subprocess` sobre el video procesado.
2. Procesamiento de video real sin YOLO: `monitoreo/tests.py` (escribe y lee video sintético de 6 fotogramas en carpeta temporal). `produccion/test_seguridad.py` simula `subprocess`/ffmpeg con `patch` (líneas 145–161) y YOLO con `patch` (55, 92).
3. Lectura de datos reales del repo (solo lectura): `experimentos/pilotos/test_consolidacion_fuentes_tapa.py:8,34` lee `datasets/calidad_botellas/v003/...` y `datasets/publicos_calidad_botellas/imports/...` (falla si esos datasets no existen en un clon); `test_portal.py` solicita rutas reales a `/artefactos/` y comprueba 404 en `db.sqlite3`, `acceso_local.json`, `laboratorio.sqlite3` (verifica protección, sin escribirlos).
4. Escritura bajo el repositorio: varios tests de laboratorio crean carpetas `output/tests/<uuid>` y las borran con `addCleanup` (`test_adjudicacion_tapa.py:15`, `test_geometria_tapa.py:24`, `test_revision_tapa_v4.py:34`, `test_portal.py:98`, `tests.py:16`). Es ruta ignorada; riesgo bajo, pero un test interrumpido deja residuos allí. No se detectó escritura sobre rutas reales de adjudicaciones/revisiones (usan `override_settings` con raíz temporal).
5. Tests puros/mocks (sin I/O pesado): `test_evaluacion*.py`, `test_referencia_epp.py`, `test_calidad_individual.py` (arreglos numpy), `test_auditoria_tapa.py`, etc.

### Pendiente por verificar (requiere ejecutar)
- Que todos los tests pasen y cuánto tardan; que `manage.py test` descubra los de `experimentos/pilotos`.
- Qué `settings` usan los tests de laboratorio (hay `experimentos/pilotos/settings.py` propio, puerto 8010).
- Si `FlujoProduccionTests` tarda minutos en CPU.

## 3. Rutas reales
- **Producción:** `db.sqlite3` (`config/settings.py:86`), `media/` (`config/settings.py:133`, `MEDIA_ROOT`), `Modelos/best.pt` y `yolo11n.pt` (raíz y `Modelos/`), `media_backup/`, `db_backup_*.sqlite3`.
- **Laboratorio:** `experimentos/pilotos/` (settings propio), `output/experimental_pilotos/laboratorio.sqlite3`, `output/experimental_pilotos/acceso_local.json`, `output/pilotos_*/`, `config/pilotos.json`.
- **Datos protegidos:** `datasets/**`, `pruebas_ia/*.mp4`, `pruebas_ia/referencia_epp_*.json`, `output/<fase>/` (evidencias/informes históricos).
- Django aísla la BD en tests (BD de prueba en memoria) y los tests revisados sobreescriben `MEDIA_ROOT`. Riesgo residual: cualquier test que use `ROOT/...` sin `override_settings` escribe en el repo real (solo `output/tests` observado).

## 4. Riesgos (priorizados)
| # | Riesgo | Impacto |
|---|---|---|
| R1 | Todo el trabajo de las fases (código, docs, informes) sin commit; un único commit | Pérdida total ante `reset`/`clean`/fallo de disco |
| R2 | Anotaciones y adjudicaciones humanas de TAPA/EPP, `laboratorio.sqlite3`, `db.sqlite3` y videos originales solo existen localmente, sin copia versionada | Pérdida irrecuperable de trabajo humano |
| R3 | `FlujoProduccionTests` ejecuta YOLO real; correr `manage.py test` completo lo dispara sin aviso | Lentitud y consumo de CPU; viola la regla "no inferencias sin autorización" |
| R4 | Pesos (`best.pt`, `yolo11n.pt`) rastreados en Git pese a `.gitignore` | Repo pesado; futuros cambios de pesos inflan el historial |
| R5 | `requirements.txt` en HEAD ilegible para pip | Entorno no reproducible desde el commit actual (se corrige con el archivo actual) |
| R6 | Tests de laboratorio dependen de datasets locales no versionados | Fallos en otro equipo/clon |
| R7 | `output/tests` como destino de temporales dentro del repo | Residuos si un test se interrumpe |
| R8 | `seguridad/tests.py` vacío: cobertura EPP solo en `test_piloto.py` | Lógica operativa EPP poco cubierta |

## 5. Propuesta de separación de pruebas
1. **Unitarias con mocks** (rápidas, default): `monitoreo/tests.py`, `produccion/test_seguridad.py`, `test_consultas.py`, `test_registro_manual.py`, `seguridad/test_piloto.py`, y los `test_*` puros del laboratorio.
2. **Integración Django** (BD de prueba + `MEDIA_ROOT` temporal): vistas, permisos, portal (`test_portal.py`, `experimentos/pilotos/tests.py`).
3. **Visión artificial (inferencia real, opt-in):** `produccion/tests.py::FlujoProduccionTests`. Marcar con etiqueta (`@tag("vision")`) y excluir por defecto con `--exclude-tag=vision`; ejecutarlo solo con autorización.
4. **Laboratorio con datos reales (opt-in):** `test_consolidacion_fuentes_tapa.py` y otros que lean `datasets/`; `@tag("laboratorio")` + `skipUnless` si faltan los datasets.
5. Comando seguro por defecto propuesto: `manage.py test --exclude-tag=vision --exclude-tag=laboratorio`. Requiere editar tests (añadir tags): se hará solo con autorización.

## 6. Estrategia de recuperación (propuesta; nada aplicado)
1. **Respaldo previo a cualquier commit** (fuera del repo, p. ej. `D:\respaldo_epp_AAAAMMDD\`; copia, no mover): `db.sqlite3` y los dos backups, `output/experimental_pilotos/`, `datasets/calidad_botellas/v002/experiments/` (anotaciones), `pruebas_ia/*.mp4` y `referencia_epp_*.json`, `Modelos/`, `yolo11n.pt`. Verificar con SHA-256 (los hashes de los 4 pesos ya constan en el documento maestro). Opcional: `git bundle` y `git stash`-like copia del árbol de trabajo (`git status` + zip de código).
2. **Etiqueta de seguridad:** tras el primer commit, `git tag base-estable-AAAAMMDD`.
3. **Commits por módulo, en este orden** (sin `git add -A`; `git add` por rutas; revisar `git diff --cached --stat` antes de cada uno):
   1. `requirements.txt` (corrección de codificación).
   2. `.gitignore`.
   3. Documentación y proyecto: `CLAUDE.md`, `README.md`, `docs/`, `.claude/skills/` (sin configuración local).
   4. Núcleo EPP: `seguridad/piloto.py`, `seguridad/test_piloto.py`, `config/pilotos.json`.
   5. Monitoreo: `monitoreo/{piloto.py,views.py,urls.py,tests.py}` y plantillas.
   6. Laboratorio: `experimentos/`, `scripts/`, `static/`.
   7. Informes ligeros de `output/*` (solo `INFORME*.md`, `*.json` de métricas pequeñas; sin imágenes/videos/SQLite).
4. **Excluir de Git:** `datasets/**` (ya ignorado), videos, SQLite, `media*`, `venv`, `output/experimental_pilotos/`, `pruebas_ia/*.mp4`, `Modelos/*.pt`. Para pesos y datasets usar almacenamiento externo o Git LFS (decisión pendiente); documentar hashes en un manifiesto versionado.
5. **Sacar pesos del índice sin borrarlos:** `git rm --cached Modelos/best.pt yolo11n.pt` (conserva los archivos en disco) solo tras respaldar y con autorización; el historial seguirá conteniéndolos.
6. **Recuperación ante fallo:** trabajar en ramas por tarea (`git switch -c fase1-...`); revertir con `git revert`/`git restore` solo sobre archivos propios; restaurar datos desde el respaldo verificado por SHA-256. Ejecutar `manage.py check` tras cada commit.

## 7. Dependencias verificadas
Django 5.2.19, ultralytics 8.4.212, torch 2.15.0, torchvision 0.29.2, opencv-python 5.0.0.93, numpy 2.5.4, lap 0.5.14, imageio-ffmpeg 0.8.1, pillow 13.0.0: instalado = fijado; `pip check` OK. Python 3.13, CPU.

## 8. No verificado
- Resultado de cualquier suite de tests hoy (solo `manage.py check`).
- Duración y comportamiento real de `FlujoProduccionTests`.
- Motivo de `ultralytics-platform` en `requirements.txt`.
- Contenido de los respaldos existentes (`media_backup`, `db_backup_*`): solo se listaron.
- Licencias de datasets; integridad de archivos protegidos.

## 9. Próximos pasos (esperan autorización)
1. Crear el respaldo externo verificado por SHA-256 (§6.1).
2. Añadir tags a los tests y definir el comando seguro por defecto (§5).
3. Ejecutar la suite segura (`--exclude-tag=vision`) en una BD de prueba y registrar resultados.
4. Commits por módulo (§6.3) con revisión de `git diff --cached` en cada uno.
5. Decidir pesos y datasets: LFS, almacenamiento externo o manifiesto de hashes.
6. Actualizar `docs/CONTEXTO_MAESTRO_PROYECTO.md` con las correcciones de esta fase (riesgo 3 y `requirements.txt`).
