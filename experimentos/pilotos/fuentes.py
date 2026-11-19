"""Referencias al inventario ya verificado; no realiza otra auditoría."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FUENTES = {
    "videos/trabajadores.mp4": ROOT / "media/videos/trabajadores.mp4",
    "fuentes/epp_largo.mp4": ROOT / "pruebas_ia/trabajadores.mp4",
    **{f"fuentes/{nombre}.mp4": ROOT / f"pruebas_ia/{nombre}.mp4"
       for nombre in ("produccion", "prueba2", "tapas", "botellasSinTapa", "produccion_prueba_02")},
}
REFERENCIAS = ROOT / "datasets/calidad_botellas/v002/experiments/detection_manual_v001/dataset"
