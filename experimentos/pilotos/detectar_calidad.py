"""Inferencia opcional sobre los 25 frames congelados; no entrena ni modifica fuentes."""
import argparse
import hashlib
import json
import time
from importlib.metadata import version
from pathlib import Path
from .fuentes import ROOT, REFERENCIAS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--referencias", type=Path, required=True)
    parser.add_argument("--salida", type=Path, required=True)
    args = parser.parse_args()
    salida = args.salida.resolve()
    if not salida.is_relative_to(ROOT / "output"):
        raise ValueError("Use una salida experimental dentro de output.")
    if salida.exists():
        raise FileExistsError("No se sobrescriben predicciones.")
    pesos = ROOT / "datasets/calidad_botellas/v002/experiments/individual_v001/weights/yolo11s.pt"
    if not pesos.is_file():
        raise FileNotFoundError("Pesos locales ausentes; no se descargan automáticamente.")
    from ultralytics import YOLO
    modelo = YOLO(str(pesos))
    if modelo.names[39] != "bottle":
        raise ValueError("El catálogo de clases de los pesos no coincide con COCO bottle.")
    datos = json.loads(args.referencias.read_text(encoding="utf-8"))
    muestras = []
    inicio = time.perf_counter()
    for ref in datos["records"]:
        imagen = (REFERENCIAS / ref["source"]["image"]).resolve()
        if not imagen.is_relative_to(REFERENCIAS) or hashlib.sha256(imagen.read_bytes()).hexdigest() != ref["source"]["image_sha256"]:
            raise ValueError("Imagen de referencia alterada o fuera del dataset.")
        resultado = modelo.predict(str(imagen), classes=[39], conf=.30, imgsz=640, device="cpu", save=False, verbose=False)[0]
        muestras.append({"sample_id": ref["sample_id"], "image_sha256": ref["source"]["image_sha256"],
            "detections": [{"class_name": "ENVASE", "bbox_xyxy": b.xyxy[0].tolist(), "score": float(b.conf[0])}
                           for b in resultado.boxes]})
    reporte = {"samples": muestras, "clases_ejecutadas": ["ENVASE"], "modelo": "YOLO11s COCO bottle -> ENVASE",
               "pesos_sha256": hashlib.sha256(pesos.read_bytes()).hexdigest(),
               "referencias_sha256": hashlib.sha256(args.referencias.read_bytes()).hexdigest(),
               "parametros": {"classes": [39], "conf": .30, "imgsz": 640, "device": "cpu", "save": False},
               "catalogo_modelo": modelo.names,
               "versiones": {p: version(p) for p in ["ultralytics", "torch", "numpy", "opencv-python"]},
               "segundos_inferencia_25": time.perf_counter() - inicio,
               "TAPA": "DETECTOR_NO_DISPONIBLE_EN_ESTE_BASELINE", "defectos": "NO EJECUTADOS",
               "seguimiento": "NO EJECUTADO", "RAYADURA": "NO DISPONIBLE", "DEFORMACION": "NO DISPONIBLE"}
    with salida.open("x", encoding="utf-8") as archivo:
        json.dump(reporte, archivo, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
