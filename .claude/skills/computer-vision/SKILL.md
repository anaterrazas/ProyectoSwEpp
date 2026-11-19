---
name: computer-vision
description: Visión artificial en Sistema EPP (YOLO, OpenCV, ByteTrack, detección/seguimiento de personas y envases, asociación de objetos, video, evidencias). Usar al tocar pipelines de detección, tracking, asociación o evidencias visuales.
---

# Computer Vision – Sistema EPP

## Reglas
- Verificar existencia, ruta y versión/hash de cada modelo (`.pt`) antes de usarlo; leer su config en `config/` (p. ej. `config/pilotos.json`).
- Nunca sobrescribir pesos; guardar salidas nuevas con versión en `output/<nombre>_vNNN_NNN/`.
- Videos originales: solo lectura. Escribir derivados en `output/`.
- Separar experimentos (laboratorio) de producción; no promover un modelo sin autorización.
- Registrar parámetros de inferencia (modelo, conf, iou, imgsz, tracker, fuente, fecha) junto a cada resultado.
- Asociación persona–EPP / tapa–envase: usar criterios geométricos explícitos y documentados; si es ambigua, no asignar.
- Mantener estado `NO EVALUABLE` cuando la visibilidad o evidencia sea insuficiente; no forzar OK/NO OK.
- Convención TAPA: caja de toda la tapa visible + anillo de seguridad, sin brida, cuello, rosca ni cuerpo (`docs/PROTOCOLO_TAPA_GEOMETRIA_v1.md`).
- Resultados experimentales ≠ precisión industrial; indicarlo siempre.
- No ejecutar inferencia/entrenamiento masivo sin autorización; probar con 1-2 muestras.

## Estilo
- Reportar rutas exactas y métricas resumidas; sin volcar código ni logs largos.
