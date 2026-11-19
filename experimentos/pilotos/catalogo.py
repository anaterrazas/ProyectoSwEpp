"""Catálogo de presentación. No ejecuta modelos ni escribe en las evaluaciones."""
from .fuentes import ROOT

LAB = "output/experimental_pilotos/"
SIM = "datasets/calidad_botellas/v002/experiments/individual_v001/runs/piloto_tapa_20261117/"
PERMISOS = {"epp": "seguridad.view_deteccionepp", "calidad": "produccion.view_analisisproduccion"}
MODULOS = {
    "epp": {
        "nombre": "Seguridad EPP", "etiqueta": "Piloto supervisado", "color": "azul",
        "descripcion": "Personas, cascos y chalecos. Evidencia visible y revisión humana; sin confirmación automática de cumplimiento.",
        "capacidades": [("PERSONA · CASCO · CHALECO", "Detección experimental disponible"), ("CHALECO 0,15", "CANDIDATA EXPERIMENTAL · solo laboratorio"), ("Asociación y seguimiento", "Disponibles con omisiones y pérdidas de ID"), ("Alertas persistentes", "Sin validación suficiente; cero candidatos en estos clips")],
    },
    "calidad": {
        "nombre": "Control de Calidad", "etiqueta": "En desarrollo", "color": "verde",
        "descripcion": "Inspección experimental de envases plásticos. Las capacidades pendientes permanecen explícitas y separadas.",
        "capacidades": [("ENVASE", "Detección experimental disponible"), ("TAPA", "Sin detector evaluado"), ("Asociación tapa–envase", "PENDIENTE"), ("Clasificación de defectos", "NO EVALUABLE en la simulación existente"), ("RAYADURA", "NO DISPONIBLE"), ("DEFORMACION", "NO DISPONIBLE")],
    },
}
# Directorios específicos, nunca todo output, datasets o el workspace.
RAICES = {
    LAB + "seguridad_epp_v002_001": "epp",
    LAB + "evaluacion_epp33_v002_001": "epp",
    LAB + "auditoria_errores_epp33_v002_001": "epp",
    LAB + "comparacion_videos_epp_v002_001": "epp",
    LAB + "evaluacion_deteccion_v002_001": "calidad",
    SIM.rstrip("/"): "calidad",
}
DOCUMENTOS = ["GUION_DEMO_INTEGRADA.md", "INFORME_DEMO_INTEGRADA.md", "CIERRE_EPP_V002_Y_PLAN_INTEGRACION.md", "MONITOREO_LABORATORIO.md", "PILOTOS.md"]
EJECUCIONES = [
    ("epp", "Base temporal · dos videos", LAB+"seguridad_epp_v002_001/modelos_y_parametros.json", LAB+"seguridad_epp_v002_001/INFORME_EPP.md", "Inferencia completa base conservada"),
    ("epp", "Referencia humana · 33 imágenes", LAB+"evaluacion_epp33_v002_001/metricas.json", LAB+"evaluacion_epp33_v002_001/index.html", "Imágenes aisladas; no sumar a los resultados temporales"),
    ("epp", "Auditoría y configuraciones", LAB+"auditoria_errores_epp33_v002_001/plan_previo.json", LAB+"auditoria_errores_epp33_v002_001/index.html", "Barrido exploratorio y selección post hoc"),
    ("epp", "Base frente a candidata · videos completos", LAB+"comparacion_videos_epp_v002_001/plan.json", LAB+"comparacion_videos_epp_v002_001/index.html", "374 fotogramas; tracking compartido; no independiente"),
    ("calidad", "ENVASE · 25 referencias", LAB+"evaluacion_deteccion_v002_001/predicciones.json", LAB+"evaluacion_deteccion_v002_001/index.html", "Concordancia provisional; siete conflictos de clase"),
    ("calidad", "Simulación con abstención", SIM+"report.json", SIM+"processed.mp4", "399 fotogramas; cero llamadas al clasificador; NO EVALUABLE"),
]


def permite(user, modulo):
    return user.has_perm(PERMISOS[modulo])


def leer(relativo):
    import json
    try:
        return json.loads((ROOT / relativo).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
