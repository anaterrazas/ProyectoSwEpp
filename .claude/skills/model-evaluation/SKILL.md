---
name: model-evaluation
description: Datasets YOLO, entrenamiento y evaluación en Sistema EPP (splits, duplicados, licencias, precision/recall/F1, mAP, matrices de confusión, auditoría de anotaciones). Usar para preparar datasets o evaluar modelos.
---

# Model Evaluation – Sistema EPP

## Reglas
- Entrenar SOLO con autorización expresa del usuario en esa tarea.
- Comprobar licencia y procedencia de cada fuente; las referencias propias con procedencia/autorización pendiente se excluyen del entrenamiento.
- Mantener hashes (sha256) y manifiestos JSON; no sobrescribir datasets originales ni anotaciones humanas: crear versiones nuevas.
- No inventar anotaciones ni corregirlas en silencio; toda corrección con autor, fecha, hash y original conservado.
- Split por grupos/sesiones/fuentes; detectar duplicados y casi-duplicados antes de dividir; nunca mezclar imágenes relacionadas entre train/val/test.
- Test independiente: no usarlo para ajustar umbrales ni hiperparámetros (usar val).
- Documentar hiperparámetros, versiones (ultralytics/torch), semilla y dataset hash.
- Métricas: precision, recall, F1, mAP@50, mAP@50:95, matriz de confusión, por clase; indicar tamaño muestral e intervalos/limitaciones estadísticas.
- Conservar evaluaciones previas; escribir nuevas en carpeta versionada de `output/`.
- Distinguir métrica verificada (reproducida) de histórica (solo citada en informe).

## Estilo
- Resumen con rutas y cifras clave; sin tablas gigantes.
