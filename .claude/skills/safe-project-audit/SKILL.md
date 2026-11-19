---
name: safe-project-audit
description: Auditoría de solo lectura de Sistema EPP (arquitectura, código, dependencias, modelos, datasets, pruebas, funcionalidades incompletas). Usar cuando se pida auditar, diagnosticar o documentar el estado real sin modificar nada.
---

# Safe Project Audit – Sistema EPP

## Reglas
- Solo lectura primero: Glob/Grep/Read; leer parcialmente archivos grandes.
- Alcance mínimo: auditar solo el componente pedido, no el repositorio entero.
- No modificar código, configuración, BD, modelos, datasets ni videos; no borrar ni sobrescribir informes (nuevos documentos con nombre nuevo/versionado).
- No entrenar ni inferir sin autorización. Pruebas: solo comprobaciones seguras (p. ej. `manage.py check`, tests acotados con BD de prueba).
- Cada afirmación con respaldo: ruta de archivo/artefacto. Separar HECHO verificado / INFERENCIA / HISTÓRICO (citado en docs).
- Clasificar funcionalidades: IMPLEMENTADA Y VERIFICADA · CON LIMITACIONES · EXPERIMENTAL · EN DESARROLLO · NO IMPLEMENTADA · PENDIENTE DE VALIDACIÓN.
- Errores hallados: documentar impacto; no corregir sin autorización.
- No declarar terminado sin verificar; indicar qué no se verificó.
- Subagentes solo si el barrido es amplio y aporta valor real.

## Salida
- Resumen ejecutivo corto + hallazgos priorizados con rutas.
