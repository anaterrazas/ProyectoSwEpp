# Sistema EPP

Proyecto Django (SQLite, Bootstrap) con YOLO/OpenCV/ByteTrack. Dos módulos: **Seguridad EPP** (`seguridad/`) y **Control de Calidad / laboratorio** (`monitoreo/`). Desarrollo previo hecho con OpenAI Codex; no hay historial de esas conversaciones: el código y los artefactos son la evidencia.

## Contexto
Estado real, arquitectura, modelos, resultados y pendientes: `docs/CONTEXTO_MAESTRO_PROYECTO.md` (leer primero). Resumen: Django operativo (`seguridad/`, `monitoreo/`, `produccion/`) + laboratorio aislado (`experimentos/pilotos/`, puerto 8010, SQLite propia). EPP es el módulo más avanzado (YOLO+ByteTrack, revisión humana); Calidad solo tiene baseline ENVASE y dataset TAPA en preparación. Todo es experimental, sin validación industrial.

## Reglas generales
- No modificar la SQLite operativa, datos de producción, videos originales, datasets originales, pesos existentes, anotaciones humanas ni informes/evidencias.
- Mantener separados laboratorio experimental y producción, y EPP y Calidad.
- No entrenar ni ejecutar inferencias masivas sin autorización expresa.
- No cambiar la arquitectura ni declarar algo terminado sin verificarlo.
- Antes de modificar un componente, consultar la documentación pertinente en `docs/` y leer solo los archivos necesarios.
- Resultados experimentales no son precisión industrial.
- Respuestas breves, con rutas exactas; sin volcar código ni auditorías completas si basta un componente.

## Skills (`.claude/skills/`)
- `/django-development` – backend/frontend Django.
- `/computer-vision` – detección, tracking, asociación, evidencias.
- `/model-evaluation` – datasets, entrenamiento, métricas.
- `/safe-project-audit` – auditorías de solo lectura.

## Documentación
`docs/` (p. ej. `MONITOREO_LABORATORIO.md`, `CIERRE_EPP_V002_Y_PLAN_INTEGRACION.md`, `FASE2_CALIDAD_V002.md`, `PROTOCOLO_TAPA_GEOMETRIA_v1.md`), `README.md`.
