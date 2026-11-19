# Contexto maestro · Sistema EPP

Recuperación de contexto del trabajo previo (OpenAI Codex). Fecha: 18/11/2026. Solo lectura de código, docs y artefactos; sin entrenamiento, inferencia, migraciones ni cambios en datos. Las cifras se citan de los informes indicados; solo los hashes de pesos y la estructura se contrastaron directamente con los archivos (ver «Verificado»).

Convención: **VERIFICADO** = contrastado con archivo/config actual · **INFORMADO** = declarado en un informe, no recontrastado · **EXPERIMENTAL** · **PENDIENTE** · **NO IMPLEMENTADO**.

## 1. Descripción general

Plataforma Django para (a) **Seguridad EPP**: detectar personas, casco y chaleco en video, seguirlas, asociar el equipo a cada persona y proponer candidatos de incumplimiento sujetos a revisión humana; y (b) **Control de Calidad**: piloto de inspección de **tapa ausente o mal colocada después del tapado** en botellas. Ambos módulos están en fase experimental/laboratorio; no hay validación industrial ni en planta (`config/pilotos.json`: `validado_en_planta: false`, `rechazo_automatico: false`, `revision_humana_obligatoria: true`).

Respaldo: `README.md`, `docs/PILOTOS.md`, `config/pilotos.json`, `docs/CIERRE_EPP_V002_Y_PLAN_INTEGRACION.md`.

## 2. Arquitectura

Dos capas que conviene no mezclar:

| Capa | Ubicación | Rol |
|---|---|---|
| **Aplicación Django operativa** (`config/settings.py`, SQLite `db.sqlite3`) | `administracion/` (áreas, cámaras, trabajadores, equipos), `seguridad/` (modelo `DeteccionEPP`, `piloto.py` asociación/persistencia), `monitoreo/` (cámaras, análisis YOLO, reporte piloto), `produccion/` (productos, criterios, lotes, `AnalisisProduccion`, `InspeccionCalidad`), `reportes/` | Rutas: `/admin/`, `/monitoreo/`, `/reportes/`, `/produccion/` (`config/urls.py`). VERIFICADO. |
| **Laboratorio aislado** (`experimentos/pilotos/`, settings propios, SQLite `output/experimental_pilotos/laboratorio.sqlite3`, puerto 8010) | Portal `/`, `/demo/epp/`, `/demo/calidad/`, `/demo/historial/`, `/artefactos/...`, adjudicación y geometría de tapa, visores `/monitoreo/` y `/calidad/` heredados | Presenta resultados ya calculados con permisos separados EPP/Calidad, servicio de medios con Range y catálogo cerrado de artefactos. INFORMADO en `docs/INFORME_DEMO_INTEGRADA.md`; módulos existen (VERIFICADO: `catalogo.py`, `portal.py`, `artefactos.py`, `media.py`, `panel.py`). |
| **Datos/ML de Calidad** | `datasets/calidad_botellas/{v001,v002,v003}`, `datasets/publicos_calidad_botellas`, `ml/calidad_botellas/` (preparación, etiquetado, auditoría) | Datasets, referencias humanas, experimentos (`v002/experiments/{individual_v001,day1_v001,detection_manual_v001}`). |
| **Evidencias** | `output/` (≈25 carpetas por fase, cada una con `INFORME.md`, `manifest.json`, `verificacion_integridad.json`) | Informes y manifiestos con SHA-256; base de «archivos protegidos». |

El propio cierre indica que **no existe aún un contrato único de ejecución/resultados** entre EPP y Calidad (arquitectura de adaptadores descrita en `docs/CIERRE_EPP_V002_Y_PLAN_INTEGRACION.md` §3 es *propuesta, no implementada*).

## 3. Tecnologías

Django 5.2.19, SQLite, Bootstrap en plantillas; Ultralytics 8.4.212 (YOLO), Torch 2.15.0, OpenCV 5.0.0.93, NumPy 2.5.4, `lap` (ByteTrack), imageio-ffmpeg; CPU (`device="cpu"`). Python 3.13 (`ml/__pycache__/*.cpython-313`). Respaldo: `requirements.txt` (normalizado a UTF-8 según `README.md`; no probado en instalación nueva). Pruebas del laboratorio con Node/Chrome en `scripts/verificar_*.mjs`.

## 4. Módulo Seguridad EPP

**Flujo implementado (VERIFICADO en código):** `monitoreo/views.py::analizar_camara` carga `YOLO(ruta_modelo)` (EPP) y `YOLO(yolo11n.pt)`; las personas se siguen con `modelo_personas.track(classes=[0], conf=.30, tracker="bytetrack.yaml", persist=True, device="cpu")`; `seguridad/piloto.py` aporta `asociar` (centro de la caja del equipo en región anatómica, con abstención ante ambigüedad), `estados` y `Persistencia` (candidato si la señal persiste ≥2 s). `monitoreo/piloto.py::reporte_piloto` y `monitoreo/urls.py` exponen el reporte con decisiones humanas. Modelo de datos: `seguridad/models.py::DeteccionEPP` (tipos Person, Hardhat, NO-*, etc.).

**Pesos (VERIFICADO, SHA-256 iguales a los del informe):** `yolo11n.pt` (0ebbc80d…ee1), `Modelos/best.pt` (2b33d4d0…a4f61). Clases usadas de `best.pt`: Hardhat→CASCO, Safety Vest→CHALECO, NO-Hardhat y NO-Safety Vest como señales negativas.

**Resultados (INFORMADO, 33 fotogramas humanos / 203 cajas; sin test independiente):**

| Clase | P | R | F1 |
|---|---:|---:|---:|
| PERSONA (con tracking) | 81,5 % | 71,6 % | 76,3 % |
| CASCO | 83,3 % | 63,6 % | 72,2 % |
| CHALECO base (conf 0,30) | 96,8 % | 40,5 % | 57,1 % |
| CHALECO candidata (conf 0,15) | 97,7 % | 58,1 % | 72,9 % |

Asociación (CASCO 28/55; CHALECO 20/74 → 31/74), 4 y 10 IDs con 3 y 12 interrupciones (fragmentación), cero candidatos persistentes en los dos videos (`media/videos/trabajadores.mp4` 122 fotogramas; `pruebas_ia/trabajadores.mp4` 252). Cero candidatos **no** prueba ausencia de incumplimientos. La candidata (umbral 0,15) vive solo en el laboratorio; no está integrada al flujo Django.

Respaldo: `docs/CIERRE_EPP_V002_Y_PLAN_INTEGRACION.md`; `output/experimental_pilotos/{evaluacion_epp33,auditoria_errores_epp33,comparacion_videos_epp,seguridad_epp}_v002_001/INFORME*.md`; código `experimentos/pilotos/{seguridad_epp,evaluacion_epp33,referencia_epp}.py`.

## 5. Módulo Control de Calidad

**Aplicación operativa (VERIFICADO en modelos):** `produccion/models.py` — `Producto`, `CriterioCalidad`, `LoteProduccion`, `AnalisisProduccion`, `InspeccionCalidad`; catálogo BOTELLA/CAJA/BOLSA (estructura, no capacidad validada). `produccion/views.py` incluye seguimiento ByteTrack de conteo.

**Laboratorio Calidad (INFORMADO + código presente):**
- Localización ENVASE: `yolo11s.pt` COCO bottle→ENVASE (conf 0,30, 640, CPU) — SHA-256 85a76fe8… VERIFICADO. 25 fotogramas de referencia (15 `prueba2.mp4`, 10 `tapas.mp4`): 99 TP / 39 FP / 8 FN / 2 ignoradas (P 71,7 %, R 92,5 %), provisional: 7 de los 8 FN son cajas ENVASE cuya nota decía «tapa» (`docs/FASE2_CALIDAD_V002.md`).
- Clasificador `TinyCapCNN` (`day1_v001/artifacts/cap_model.pt`, 548886…c96b1 VERIFICADO): binario TAPA_DEFECTUOSA, sin cajas; test 17 imágenes F1 66,7 % = baseline mayoritario. No acredita nada.
- **No existe detector TAPA evaluado**, ni clasificación correcta/ausente/mal colocada, ni defectos (RAYADURA, DEFORMACION: NO DISPONIBLE).
- Simulación `botellasSinTapa.mp4`: 399 fotogramas, 1.087 observaciones, 39 IDs temporales, cero llamadas al clasificador → NO EVALUABLE por abstención (demuestra el veto, no rendimiento).
- Fase 2.2: 7 conflictos ENVASE→TAPA adjudicados por humano (Ana, 18/11) e integrados en copia `datasets/calidad_botellas/v002/experiments/detection_manual_v001/dataset_tapa_adjudicado_fase23_001` (ver `output/integracion_tapa_adjudicada_v002_001/INFORME.md`); sin segunda revisión independiente.
- Fases 2.8–2.10 (dataset TAPA): suficiencia **NO PREPARADA** para entrenar (`output/fase28_…`); índice candidato de 284 imágenes (272 v26 + 12 v4) (`output/fase29_…`); convención oficial confirmada por el usuario: *caja = toda la tapa visible + anillo unido, excluir cuello/rosca/cuerpo* (`docs/PROTOCOLO_TAPA_GEOMETRIA_v1.md`). Criba técnica de 272 ROI v26: 4 CONSERVAR, 268 REQUIEREN AJUSTE HUMANO, 0 NO EVALUABLE; herramienta `/demo/calidad/tapa-geometria/` lista para que una persona decida (`output/fase210_…/INFORME.md`). Decisiones humanas aún no registradas según ese informe.

## 6. Modelos y datasets

| Recurso | Ruta | Estado |
|---|---|---|
| Persona COCO | `yolo11n.pt` | Congelado, verificado |
| EPP 14 clases | `Modelos/best.pt` | Congelado, verificado |
| ENVASE baseline | `datasets/calidad_botellas/v002/experiments/individual_v001/weights/yolo11s.pt` | Congelado, verificado |
| Alternativa Faster R-CNN MobileNetV3 | `individual_v001/` | Solo comparación |
| TinyCapCNN | `day1_v001/artifacts/cap_model.pt` | Experimental débil |
| Referencia EPP humana | 33 fotogramas, 203 cajas (`experimentos/pilotos/referencia_epp.py`, JSON `pruebas_ia/referencia_epp_2026-11-18T01-19-39.310Z.json`) | Sin test independiente |
| Referencia Calidad | 25 imágenes, 244 cajas (108 ENVASE, 136 TAPA→ con 7 reclasificadas) | Sin 2.º revisor |
| Datasets públicos | `datasets/publicos_calidad_botellas`, Mendeley v1 (defectos de superficie, no TAPA), Roboflow v26/v4 (zip `pruebas_ia/Bottle Defect Detection.v4i.coco.zip`) | Licencia/procedencia heterogénea; auditorías en `output/auditoria_*` |

No se entrenó ningún modelo nuevo en las fases 2.x (INFORMADO). Cada carpeta de `output/` tiene manifiesto/hashes (p. ej. `output/fase29_…/manifest.json`).

## 7. Resultados experimentales

Ver tablas §4 y §5. Todas son **resultados de laboratorio sobre muestras pequeñas, correlacionadas y conocidas**; no son precisión industrial. No se agregan TP/FP/FN entre etapas (reutilizan referencias) ni se mezclan detección, asociación, tracking, evento y defecto en un único porcentaje.

## 8. Funcionalidades

| Funcionalidad | Estado |
|---|---|
| Django: `manage.py check` sin incidencias; 10 tests `monitoreo`+`seguridad` OK (ejecutado hoy, BD de prueba) | IMPLEMENTADA Y VERIFICADA |
| Análisis EPP YOLO+ByteTrack+asociación+persistencia 2 s en `monitoreo/views.py` | IMPLEMENTADA; precisión CON LIMITACIONES / EXPERIMENTAL |
| Reporte y decisiones humanas con observación, historial y versión | IMPLEMENTADA (INFORMADO, probada con fixtures; sin alertas reales) |
| Candidata chaleco 0,15 | EXPERIMENTAL, solo laboratorio |
| Portal de demostración `/`, `/demo/*`, galerías, medios con Range (38 tests, Chrome verificado según informe) | IMPLEMENTADA (INFORMADO; no reejecutado hoy) |
| Visor Calidad, ENVASE baseline, simulación con abstención | EXPERIMENTAL |
| Adjudicación de conflictos y herramienta de geometría TAPA | IMPLEMENTADA como herramienta; decisiones de geometría PENDIENTES |
| Detector TAPA; clasificación correcta/ausente/mal colocada; RAYADURA/DEFORMACION; cámaras en vivo; contrato de ejecución común | NO IMPLEMENTADO |
| Integración automática de resultados del laboratorio al reporte Django | NO IMPLEMENTADO |

## 9. Problemas y limitaciones

1. **Árbol git sin confirmar**: casi todo el trabajo de Codex y fases 2.x está sin versionar (solo 1 commit). `.gitignore` excluye `db.sqlite3`, `media/`, `venv/`.
2. `requirements.txt` cambió de codificación (1690→775 bytes); revisar equivalencia de paquetes.
3. **El test run ejecuta análisis YOLO real** (salida «Fotogramas procesados: 6») — alguna prueba de `monitoreo/tests.py` hace inferencia en vez de mock. No investigado; verificar antes de usar tests rutinariamente.
4. No se confirmó que `experimentos/pilotos/test_*.py` y `seguridad/test_piloto.py` se ejecuten con `manage.py test` de la app principal (corren con settings del laboratorio; el informe cita 38 pruebas).
5. EPP: omisiones de chaleco/persona, fragmentación de IDs, 19 casco NO_EVALUABLE, inconsistencia `epp_largo_000100/P2`, estado heredado `CUMPLE` ≠ conformidad global.
6. Calidad: sin detector TAPA, etapa/SKU/línea sin confirmar (`config/pilotos.json`: `linea`, `sku`, `camara_id` = null); dataset TAPA no apto para entrenar; 31 imágenes con omisiones en v4; sin segunda revisión independiente.
7. Evidencia muy limitada: dos clips EPP conocidos, 25 fotogramas Calidad.
8. Permiso: visor `/calidad/` heredado aún usa permiso EPP.
9. Contenido de repositorio muy pesado (`output/`, `datasets/`, `runs/`, backups `db_backup_*.sqlite3` y `media_backup/` en raíz).

## 10. Pendientes priorizados (según `docs/CIERRE_…` §4 y fases 2.x)

- **P0** Congelar cierre y confirmar alcance de demostración (EPP supervisado; Calidad = diagnóstico ENVASE + abstención).
- **P0** Registrar en git el estado actual (con autorización) y definir qué se ignora.
- **P1** Decisiones humanas sobre geometría TAPA (268 ROI v26 + reservas v4) con la herramienta existente; resolver caja mínima y confirmar línea/SKU/etapa.
- **P1** Decisión técnica sobre omisiones de chaleco/persona y continuidad de IDs en EPP.
- **P1** Contrato de ejecución y separación de permisos EPP/Calidad.
- **P2** Adaptadores comunes Django↔laboratorio; evaluación reservada con revisión independiente.
- **P3** Entrenamiento de detector TAPA solo tras suficiencia, test reservado y autorización explícita.

## 11. Próximos pasos recomendados

1. Elegir el frente: (a) estabilizar repo/tests (punto 9.1, 9.3, 9.4), (b) cerrar referencias TAPA, o (c) mejorar EPP.
2. Si (a): inspeccionar `monitoreo/tests.py` para aislar la inferencia, y decidir qué commitear.
3. Mantener la regla: nada de entrenamiento ni inferencia masiva sin autorización.

## Verificado en esta recuperación

- `manage.py check` sin incidencias; 10 tests `monitoreo seguridad` OK.
- SHA-256 de los cuatro pesos = informes.
- Flujo `analizar_camara` (YOLO + `track(... bytetrack.yaml ...)`), `seguridad/piloto.py`, modelos y `config/pilotos.json` leídos.
- Existen las carpetas `output/` y módulos de `experimentos/pilotos/` citados.

**No verificado:** métricas y conteos (33/25 referencias), 38 tests del laboratorio, verificación Chrome, integridad de los 817/534 archivos protegidos, contenido de datasets y licencias, estado actual de la SQLite del laboratorio y servidor 8010.
