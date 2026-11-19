"""Ejecución opcional sobre videos existentes, solo en laboratorio.

Detecta botellas (COCO) y sigue IDs temporales. No localiza tapas ni clasifica
defectos. La falta de un detector de tapa se declara NO DISPONIBLE.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from .fuentes import FUENTES, ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", choices=[p.name for alias, p in FUENTES.items()
                                          if alias.startswith("fuentes/") and "epp_largo" not in alias], required=True)
    parser.add_argument("--salida", type=Path, required=True)
    args = parser.parse_args()
    video = FUENTES["fuentes/" + args.video]
    salida = args.salida.resolve()
    if not salida.is_relative_to(ROOT / "output/experimental_pilotos"):
        raise ValueError("La salida debe estar dentro de output/experimental_pilotos.")
    pesos = ROOT / "datasets/calidad_botellas/v002/experiments/individual_v001/weights/yolo11s.pt"
    if not pesos.is_file():
        raise FileNotFoundError("Pesos locales ausentes. No se descargan modelos.")
    import cv2
    import imageio_ffmpeg
    from ultralytics import YOLO
    fuente_hash = hashlib.sha256(video.read_bytes()).hexdigest()
    captura = cv2.VideoCapture(str(video))
    fps = captura.get(cv2.CAP_PROP_FPS)
    ancho, alto = int(captura.get(cv2.CAP_PROP_FRAME_WIDTH)), int(captura.get(cv2.CAP_PROP_FRAME_HEIGHT))
    captura.release()
    if not fps > 0 or not ancho > 0 or not alto > 0:
        raise ValueError("Metadatos de video inválidos.")
    salida.mkdir(parents=True, exist_ok=False)
    modelo = YOLO(str(pesos))
    resultados = modelo.track(source=str(video), classes=[39], conf=.30, imgsz=640,
        tracker="bytetrack.yaml", persist=True, stream=True, device="cpu", save=False, verbose=False)
    proceso = subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(), "-n", "-v", "error", "-f", "rawvideo",
        "-pix_fmt", "bgr24", "-s", f"{ancho}x{alto}", "-r", str(fps), "-i", "-", "-an",
        "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2", "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(salida / "detecciones.mp4")], stdin=subprocess.PIPE)
    fotogramas = 0
    estado = "ERROR"
    try:
        with (salida / "observaciones.jsonl").open("x", encoding="utf-8") as archivo:
            for resultado in resultados:
                observaciones = [{"class_name": "ENVASE", "bbox_xyxy": b.xyxy[0].tolist(),
                    "score": float(b.conf[0]), "track_id": int(b.id.item()) if b.id is not None else None}
                    for b in resultado.boxes]
                archivo.write(json.dumps({"frame_index": fotogramas, "tiempo_nominal": fotogramas / fps,
                    "detections": observaciones, "TAPA": "NO DISPONIBLE", "defectos": "NO EVALUABLE"}) + "\n")
                imagen = resultado.plot()
                cv2.putText(imagen, "EXPERIMENTAL: ENVASE / ID temporal; calidad NO EVALUABLE",
                    (10, 25), cv2.FONT_HERSHEY_SIMPLEX, .55, (0, 255, 255), 1)
                if fotogramas % max(1, round(fps)) == 0:
                    if not cv2.imwrite(str(salida / f"frame_{fotogramas:06d}.jpg"), imagen):
                        raise OSError("No se pudo guardar evidencia.")
                proceso.stdin.write(imagen.tobytes())
                fotogramas += 1
        proceso.stdin.close()
        if proceso.wait() != 0 or not fotogramas:
            raise RuntimeError("No se completó la codificación del video.")
        if hashlib.sha256(video.read_bytes()).hexdigest() != fuente_hash:
            raise RuntimeError("La fuente cambió durante la ejecución.")
        estado = "COMPLETADO"
    finally:
        resultados.close()
        if proceso.poll() is None:
            proceso.kill()
            proceso.wait()
        (salida / "reporte.json").write_text(json.dumps({"estado": estado,
            "video_origen": str(video.relative_to(ROOT)), "video_sha256": fuente_hash,
            "pesos_sha256": hashlib.sha256(pesos.read_bytes()).hexdigest(), "fotogramas": fotogramas,
            "deteccion": "COCO bottle -> ENVASE", "TAPA": "NO DISPONIBLE",
            "clasificacion_defectos": "NO EJECUTADA", "RAYADURA": "NO DISPONIBLE", "DEFORMACION": "NO DISPONIBLE",
            "tiempos": "frame/FPS nominal; no usar como PTS medidos",
            "seguimiento": "IDs temporales; no identidades físicas verificadas",
            "precision": None, "recall": None}, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
