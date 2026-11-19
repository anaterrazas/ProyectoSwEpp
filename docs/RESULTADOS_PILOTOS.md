# Resultados de simulación con videos — 17/11/2026

## EPP: casco y chaleco

- Cámara y área existentes: ID 1. Reglas añadidas: casco y chaleco.
- Fuente: `media/videos/trabajadores.mp4`, sin modificación de sus bytes.
- Inferencia real con YOLO EPP y YOLO11n/ByteTrack: 122 fotogramas completos.
- 191 observaciones equipo/persona de cumplimiento y 333 no evaluables.
- Cero candidatos persistentes de incumplimiento. No acredita ausencia de
  incumplimientos: no hay anotación independiente ni un caso negativo confirmado.
- Las cantidades son observaciones repetidas, no personas únicas. La proporción
  no evaluable es alta; la cobertura debe mejorar antes de aceptar el piloto.
- El usuario y las detecciones de simulación se crearon en SQLite en memoria.
  La base operativa conserva sus 16 detecciones históricas. Solo se añadieron
  las dos relaciones de EPP obligatorio del área, con respaldo previo.

En la aplicación, abrir
`/monitoreo/piloto/1/89dea6db-38f9-40e5-a538-f9e3f7e4c471/` con permiso de consulta.
También aparece en la lista de cámaras.

[Video EPP procesado](../media/resultados_ia/camara_1/89dea6db38f940e5a538f9e3f7e4c471/resultado_epp.mp4)
· [Reporte JSON](../media/resultados_ia/camara_1/89dea6db38f940e5a538f9e3f7e4c471/reporte.json).

## Calidad: tapa después del tapado

- Fuente: `pruebas_ia/botellasSinTapa.mp4`, bytes originales conservados.
- Pipeline experimental individual, detector preentrenado: 399 fotogramas,
  1.087 observaciones y 39 IDs temporales. No equivalen a 39 envases físicos.
- 15 fotogramas sin detección de envase. Cero llamadas al clasificador de tapa.
- Las 1.087 observaciones fueron bloqueadas por incompatibilidad visual y falta
  de confirmación de dominio/etapa. También hubo regiones pequeñas, oclusión,
  desenfoque y regiones en borde.
- Resultado: NO EVALUABLE. El nombre del archivo no demuestra que falte una tapa
  obligatoria después del tapado. No se generaron etiquetas ni conformidades.

[Video de calidad procesado](../datasets/calidad_botellas/v002/experiments/individual_v001/runs/piloto_tapa_20261117/processed.mp4)
· [Reporte detallado](../datasets/calidad_botellas/v002/experiments/individual_v001/runs/piloto_tapa_20261117/report.json).

Reproducción en una salida nueva:

```powershell
.\venv\Scripts\python.exe -B datasets/calidad_botellas/v002/experiments/individual_v001/pipeline.py --input pruebas_ia/botellasSinTapa.mp4 --output datasets/calidad_botellas/v002/experiments/individual_v001/runs/otra_simulacion
```

## Verificación de software

50 pruebas de producción, monitoreo y seguridad aprobadas con SQLite en memoria y
medios temporales. Incluyen 10 pruebas nuevas del piloto. Después de los últimos
ajustes se repitieron esas 10, todas aprobadas. Django no detectó incidencias.
La regresión con video real conserva ocho botellas al procesar y reprocesar.
En el sandbox Windows se usaron carpetas temporales con permisos heredados del
workspace para evitar el fallo de ACL de `TemporaryDirectory`.

Las pruebas nuevas cubren incertidumbre, asociación ambigua, persistencia,
interrupciones, deduplicación, reglas ausentes, permisos, revisión e historial,
conflictos de revisión y generación/lectura real de video H.264. La prueba web
unitaria simula las detecciones; las dos ejecuciones de video descritas arriba
usan inferencia real. No se midió precisión o recall de los pilotos.

## Próxima evidencia necesaria

Continuar usando videos: anotar exhaustivamente ejemplos de casco/chaleco
presente, ausente y ocluido, y envases/tapas con etapa de proceso conocida.
El anotador manual existente permite preparar ENVASE/TAPA. Se necesitan ejemplos
de tapa ausente, mal colocada y correcta con revisión humana, antes de ajustar
modelos o activar clasificación automática. No es necesario disponer de cámaras
en vivo para realizar esa preparación.
