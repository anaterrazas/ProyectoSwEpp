# Control EPP y calidad industrial

Aplicación Django con análisis de video de seguridad EPP, conteo de botellas,
inspección manual por unidad y reportes de producción.

El alcance vigente y la preparación de los pilotos se describen en
[docs/PILOTOS.md](docs/PILOTOS.md). El piloto de calidad se centra en tapa ausente
o mal colocada después del tapado. La inspección automática industrial todavía
requiere captura, anotación y evaluación independiente.

## Mapa del proyecto

| Ubicación | Responsabilidad |
|---|---|
| `administracion/` | Áreas, cámaras, trabajadores y equipos |
| `seguridad/`, `monitoreo/` | Detecciones y piloto EPP con revisión humana |
| `produccion/`, `reportes/` | Conteo, inspección manual, lotes y consultas |
| `ml/calidad_botellas/` | Preparación, etiquetado y auditoría de datos |
| `datasets/` | Fuentes, etiquetas y experimentos locales; ver inventario |
| `pruebas_ia/` | Pruebas exploratorias y videos fuente de referencia |
| `media/` | Archivos operativos; conservar con la base de datos |
| `Modelos/`, `yolo11n.pt` | Pesos utilizados por el sistema |
| `output/` | Evidencias de verificación y manifiestos de limpieza |

## Desarrollo local

Desde el entorno existente:

```powershell
.\venv\Scripts\python.exe -B manage.py check
.\venv\Scripts\python.exe -B manage.py runserver
```

Entradas: `/admin/`, `/monitoreo/`, `/produccion/`, `/reportes/`.
La configuración actual corresponde a desarrollo local. `requirements.txt` fue
normalizado a UTF-8 conservando las versiones; esto no acredita por sí solo una
instalación nueva en otra máquina.

Consultar [la organización y depuración](docs/DEPURACION.md) antes de eliminar
datos, modelos o experimentos.
