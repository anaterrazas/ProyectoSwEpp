# Preparación de la demo – Laboratorio EPP / Calidad

Fecha de verificación: 2026-11-18. Alcance: solo lectura y solicitudes HTTP GET (más el POST de inicio de sesión). No se entrenó, no se ejecutó inferencia, no se modificó código, datasets, anotaciones, pesos ni SQLite operativa. **No se corrigió nada: no hay errores críticos.**

## 1. Estado del laboratorio
- **Funciona.** Arrancó correctamente en el puerto 8010 con `venv\Scripts\python.exe -B scripts\laboratorio_pilotos.py --serve` (sin `--init`; no se tocó la BD del laboratorio salvo la sesión de login).
- Usa su propia BD (`output/experimental_pilotos/laboratorio.sqlite3`) y `MEDIA_ROOT` propio (`experimentos/pilotos/settings.py`). Verificado: `db.sqlite3` operativa sin cambios (última modificación 2026-11-18 09:39, anterior a la verificación); `git status` sin archivos modificados nuevos.
- El servidor quedó **encendido en segundo plano** desde esta verificación; si hay que reiniciarlo, ver §3.

## 2. Acceso
- URL: **http://127.0.0.1:8010/** (también http://127.0.0.1:8010/monitoreo/).
- Usuario local: `piloto`. La clave está en `output/experimental_pilotos/acceso_local.json` (campo `clave`); no se reproduce aquí. Login verificado: 200 y acceso a todas las secciones.
- **Advertencia (error menor, no corregido):** si se abre directamente `/admin/login/` e inicia sesión sin pasar por otra página, Django redirige a `/accounts/profile/` y se ve un **404**. Evitarlo: abrir `http://127.0.0.1:8010/` (redirige al login con `next=/` y, tras entrar, muestra el portal), o tras ver el 404 escribir `127.0.0.1:8010/` en la barra de direcciones (la sesión ya está iniciada). Corrección mínima propuesta, solo si se autoriza: añadir `LOGIN_REDIRECT_URL = "/"` en `experimentos/pilotos/settings.py` (no afecta producción).
- `/artefactos/` sin ruta completa devuelve 404: es el comportamiento esperado (no hay índice); no usar esa URL como enlace.

## 3. Cómo encender / reiniciar (PowerShell, en la carpeta del proyecto)
```
.\venv\Scripts\python.exe -B scripts\laboratorio_pilotos.py --serve
```
No usar `--init` (migra y reescribe permisos del usuario; innecesario). Dejar la ventana abierta. Abrir `http://127.0.0.1:8010/` en Chrome.

## 4. Comprobaciones realizadas
- Rastreo automático con sesión iniciada: ~60 URLs alcanzadas siguiendo enlaces desde el portal; **todas 200, salvo `/artefactos/` (404 esperado)**. Incluye `/`, `/demo/epp/`, `/demo/calidad/`, `/demo/historial/`, `/monitoreo/`, `/monitoreo/piloto/1/<id>/`, `/demo/calidad/tapa-geometria/`, `/demo/calidad/tapa-v4/`, `/demo/calidad/adjudicacion/` y sus imágenes, y la documentación en `/artefactos/docs/*`.
- Navegación entre EPP y Calidad: enlaces del menú lateral presentes y con respuesta 200 (verificado por contenido HTML y estado; **no se probó visualmente en el navegador**).
- Videos: 10 URLs `.mp4` con respuesta 200 y solicitud `Range` → **206** (se pueden reproducir/avanzar). Códec h264 en los 6 comprobados con ffmpeg (compatible con Chrome).
- Texto de las páginas `/demo/epp/`, `/demo/calidad/`, `/demo/historial/` revisado: ya declara los límites correctamente (ver §7).
- `manage.py check` (verificación anterior): sin incidencias.

## 5. Videos que funcionan
| Video | Ruta servida | Duración |
|---|---|---|
| EPP corto base vs candidata (inferencia existente) | `/artefactos/output/experimental_pilotos/comparacion_videos_epp_v002_001/epp_corto_base_vs_candidata.mp4` | 4,88 s |
| EPP largo base vs candidata | `.../epp_largo_base_vs_candidata.mp4` | 10,08 s |
| Calidad: simulación ENVASE/seguimiento | `/artefactos/datasets/calidad_botellas/v002/experiments/individual_v001/runs/piloto_tapa_20261117/processed.mp4` | 15,96 s |
| Originales (solo lectura) | `/media/fuentes/epp_largo.mp4`, `prueba2.mp4`, `produccion.mp4`, `produccion_prueba_02.mp4`, `tapas.mp4`, `botellasSinTapa.mp4`; `/media/videos/trabajadores.mp4` | 9–16 s |

La reproducción dentro del navegador (controles, audio, pantalla completa) no se probó; solo carga y rangos HTTP.

## 6. Guion de demostración (≈10 min)
1. **Preparar (antes):** iniciar el servidor (§3), abrir `http://127.0.0.1:8010/`, iniciar sesión, comprobar que carga el portal. Dejar pestañas abiertas: Seguridad EPP, Calidad, Historial.
2. **Vista general:** explicar que es una plataforma **experimental de laboratorio**, sin operación industrial; hay dos módulos separados (EPP y Calidad).
3. **Seguridad EPP** (`/demo/epp/`): mostrar los dos videos base vs candidata (4,88 s y 10,08 s); explicar detección de PERSONA/CASCO/CHALECO, seguimiento compartido (ByteTrack) y revisión humana obligatoria. Mostrar tarjetas de métricas y la nota "33 referencias, no es validación independiente".
4. **Monitoreo existente** (`/monitoreo/`): abrir el reporte piloto (`/monitoreo/piloto/1/...`) para evidencias y decisiones humanas.
5. **Evidencias y métricas:** abrir `evaluacion_epp33_v002_001/index.html` y `auditoria_errores_epp33_v002_001/index.html` desde la sección de resultados (enlaces del portal).
6. **Control de Calidad** (`/demo/calidad/`): mostrar el video de simulación ENVASE/seguimiento (399 fotogramas); mostrar la tabla de capacidades: ENVASE disponible, TAPA sin detector, asociación pendiente, defectos no evaluables.
7. **Datasets y preparación de TAPA:** mostrar `/demo/calidad/tapa-geometria/`, `/demo/calidad/tapa-v4/` y `/demo/calidad/adjudicacion/` como **herramientas de preparación y revisión humana** del dataset (no resultados de un detector).
8. **Historial** (`/demo/historial/`): mostrar trazabilidad de manifiestos y la separación entre ejecuciones de IA y revisiones humanas.
9. **Cierre:** limitaciones (§7) y próximos pasos (§8).

## 7. Qué se puede afirmar y qué no
**Demostrable:** portal con acceso; pipeline EPP (personas, cascos, chalecos, seguimiento, revisión humana) sobre videos conocidos; métricas experimentales por alcance; localización experimental de ENVASE; herramientas de adjudicación y geometría de TAPA; historial trazable.

**Limitaciones que hay que decir en voz alta:**
- Todo es experimental, sin validación industrial ni en planta; "resultados experimentales no son precisión industrial".
- Métricas EPP sobre **33 imágenes de referencia**, con videos conocidos y selección de umbral post hoc (CHALECO 0,15 como candidata experimental); no hay conjunto independiente.
- No hay medición de falsas alarmas por minuto ("NO DISPONIBLE").
- Calidad: solo ENVASE (baseline COCO, concordancia provisional con 7 conflictos de clase). **No hay detector de TAPA, ni clasificación tapa correcta/ausente/mal colocada, ni rechazo automático. TAPA no está entrenado.** Rayadura y deformación: no disponibles. Los 39 IDs de la simulación son IDs temporales de seguimiento, no 39 envases únicos.
- Las "regiones geométricas" de TAPA son candidatas para anotación humana, no detecciones.
- Los videos y resultados son existentes (precomputados); **no se ejecuta inferencia en vivo**.

## 8. Errores corregidos
Ninguno (no se modificó ningún archivo salvo este documento). Un solo hallazgo menor: redirección a `/accounts/profile/` (404) al iniciar sesión sin `next` (§2).

## 9. No verificado
- Reproducción efectiva en navegador y aspecto visual (no se abrió Chrome).
- Funcionamiento de los formularios de adjudicación/anotación (se hicieron solo GET; no se enviaron POST para no alterar datos).
- Tiempo de carga de los videos en el equipo de la presentación; que el puerto 8010 esté libre allí.
- Suites de pruebas (no ejecutadas por restricción).
