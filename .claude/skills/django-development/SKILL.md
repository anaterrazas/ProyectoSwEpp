---
name: django-development
description: Desarrollo Django en Sistema EPP (urls, views, models, templates Bootstrap, formularios, permisos, SQLite, servicios). Usar al modificar backend/frontend de las apps seguridad (EPP) o monitoreo/calidad.
---

# Django – Sistema EPP

## Antes de editar
- Leer solo los archivos del componente afectado (`urls.py`, `views.py`, template, servicio relacionado). Buscar con Grep antes de crear algo nuevo.
- Consultar el doc pertinente en `docs/` (p. ej. `MONITOREO_LABORATORIO.md`, `PILOTOS.md`).

## Reglas
- Respetar la arquitectura existente; reutilizar servicios/helpers; no duplicar funcionalidad.
- Mantener separadas las apps EPP (`seguridad/`) y Calidad/laboratorio (`monitoreo/`); no importar lógica de una en otra sin justificarlo.
- Laboratorio experimental ≠ producción. No tocar la SQLite operativa (`db.sqlite3`): sin migraciones aplicadas, sin escrituras ni borrados; tests solo con BD de prueba de Django.
- Si hace falta una migración, crearla pero NO aplicarla sin autorización.
- Templates: extender los base existentes, usar Bootstrap ya presente; sin cambios cosméticos no pedidos.
- Vistas delgadas; lógica en módulos/servicios (p. ej. `monitoreo/piloto.py`, `seguridad/piloto.py`). Validar entradas, CSRF y permisos en cada endpoint.
- Código modular, pequeño y mantenible; sin dependencias nuevas sin permiso.

## Después de editar
- Ejecutar solo pruebas específicas: `python manage.py test <app>.tests.<Clase>` (no la suite completa salvo petición).
- Reportar con rutas exactas y resumen breve; no pegar código extenso.
