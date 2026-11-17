"""Extractor offline de recortes originales. Nunca escribe en SQLite ni media.

Ejecutar desde la raíz: python -m ml.calidad_botellas.extract_crops --help
"""
import argparse
from collections import Counter
from contextlib import closing
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import sqlite3
from uuid import uuid4

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[2]


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as archivo:
        while bloque := archivo.read(1024 * 1024):
            digest.update(bloque)
    return digest.hexdigest()


@dataclass(frozen=True)
class Options:
    margin: float = 0.05
    max_per_track: int = 5
    min_interval_seconds: float = 0.4
    min_width: int = 64
    min_height: int = 128
    min_laplacian: float = 40.0
    max_dark_fraction: float = 0.40
    max_bright_fraction: float = 0.40
    hash_distance: int = 6
    max_gray_difference: float = 0.06
    max_tracks: int = 200
    max_memory_bytes: int = 128 * 1024 * 1024

    def validate(self):
        if not (0 <= self.margin <= 0.25 and 1 <= self.max_per_track <= 10
                and 0 <= self.min_interval_seconds <= 120
                and self.min_width > 0 and self.min_height > 0
                and self.min_laplacian >= 0 and 0 <= self.hash_distance <= 63
                and 0 <= self.max_gray_difference <= 1
                and 0 <= self.max_dark_fraction <= 1 and 0 <= self.max_bright_fraction <= 1
                and self.max_tracks > 0 and self.max_memory_bytes > 0):
            raise ValueError("Opciones de extracción fuera de rango.")


def read_analysis(database, analysis_id, video, media_root):
    """Verifica procedencia con conexión SQLite exclusivamente de lectura."""
    if analysis_id <= 0:
        raise ValueError("El ID del análisis debe ser positivo.")
    with closing(sqlite3.connect(Path(database).resolve().as_uri() + "?mode=ro", uri=True)) as connection:
        row = connection.execute(
            "SELECT a.id,a.video_original,l.id,p.tipo FROM produccion_analisisproduccion a "
            "JOIN produccion_loteproduccion l ON l.id=a.lote_id "
            "JOIN produccion_producto p ON p.id=l.producto_id WHERE a.id=?", (analysis_id,),
        ).fetchone()
    if row is None or row[3] != "BOTELLA":
        raise ValueError("Se requiere un análisis existente de botellas.")
    original = (Path(media_root).resolve() / row[1]).resolve()
    if not row[1] or not original.is_relative_to(Path(media_root).resolve()):
        raise ValueError("Ruta de video original inválida.")
    if sha256(original) != sha256(video):
        raise ValueError("El video no corresponde al original del análisis indicado.")
    return {"analysis_id": row[0], "lot_id": row[2], "product_type": row[3],
            "database_verified": True, "stored_original": row[1]}


def crop_and_quality(image, box, options):
    """No redimensiona el recorte. Los indicadores no son diagnósticos de defectos."""
    height, width = image.shape[:2]
    coords = np.asarray(box, dtype=float)
    if coords.shape != (4,) or not np.isfinite(coords).all():
        return None
    x1, y1, x2, y2 = coords
    if x2 <= x1 or y2 <= y1:
        return None
    dx, dy = (x2 - x1) * options.margin, (y2 - y1) * options.margin
    bounds = [max(0, math.floor(x1 - dx)), max(0, math.floor(y1 - dy)),
              min(width, math.ceil(x2 + dx)), min(height, math.ceil(y2 + dy))]
    left, top, right, bottom = bounds
    if right <= left or bottom <= top:
        return None
    crop = image[top:bottom, left:right].copy()
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    laplacian = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    dark = float(np.mean(gray <= 10))
    bright = float(np.mean(gray >= 245))
    flags = []
    if crop.shape[1] < options.min_width or crop.shape[0] < options.min_height:
        flags.append("small_crop")
    if laplacian < options.min_laplacian:
        flags.append("possible_blur")
    if dark > options.max_dark_fraction:
        flags.append("underexposure")
    if bright > options.max_bright_fraction:
        flags.append("overexposure_or_reflection")
    if x1 <= 1 or y1 <= 1 or x2 >= width - 1 or y2 >= height - 1:
        flags.append("touches_frame_border")
    metrics = {"width": crop.shape[1], "height": crop.shape[0], "laplacian_variance": laplacian,
               "dark_fraction": dark, "bright_fraction": bright, "flags": flags,
               "status": "REVIEW" if flags else "PASS"}
    thumb = cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA)
    dct = cv2.dct(thumb.astype(np.float32))[:8, :8].flatten()[1:]
    fingerprint = sum(int(bit) << i for i, bit in enumerate(dct > np.median(dct)))
    return crop, bounds, metrics, thumb, fingerprint


class Selector:
    def __init__(self, options):
        self.options = options
        self.samples = {}
        self.stats = Counter()

    def consider(self, track_id, image, box, frame, fps, confidence):
        result = crop_and_quality(image, box, self.options)
        if result is None:
            self.stats["invalid_box"] += 1
            return
        crop, bounds, quality, thumb, fingerprint = result
        if track_id not in self.samples and len(self.samples) >= self.options.max_tracks:
            raise ValueError("Límite de tracks alcanzado; dividir la captura en videos más cortos.")
        selected = self.samples.setdefault(track_id, [])
        rank = (not quality["flags"], -len(quality["flags"]), quality["laplacian_variance"])
        near = [s for s in selected if (
            (s["fingerprint"] ^ fingerprint).bit_count() <= self.options.hash_distance
            and float(np.mean(np.abs(s["thumb"].astype(float) - thumb.astype(float)))) / 255
            <= self.options.max_gray_difference
        ) or abs(s["frame_index"] - frame) / fps < self.options.min_interval_seconds]
        if near and (len(near) > 1 or rank <= near[0]["rank"]):
            self.stats["similar_or_temporally_close"] += 1
            return
        if not near and len(selected) >= self.options.max_per_track and rank <= min(s["rank"] for s in selected):
            self.stats["per_track_limit"] += 1
            return
        ok, encoded = cv2.imencode(".png", crop)
        if not ok:
            raise ValueError("No se pudo codificar el recorte.")
        sample = {"frame_index": frame, "timestamp_seconds_nominal": frame / fps,
                  "detector_box_xyxy": [float(n) for n in box], "crop_box_xyxy": bounds,
                  "detector_confidence": float(confidence), "quality": quality,
                  "png": encoded.tobytes(), "thumb": thumb, "fingerprint": fingerprint, "rank": rank}
        if near:
            selected.remove(near[0])
            self.stats["replaced_by_better_view"] += 1
        elif len(selected) >= self.options.max_per_track:
            selected.remove(min(selected, key=lambda s: s["rank"]))
            self.stats["replaced_by_better_view"] += 1
        selected.append(sample)
        if sum(len(s["png"]) for samples in self.samples.values() for s in samples) > self.options.max_memory_bytes:
            raise ValueError("Límite de memoria de recortes alcanzado.")


def extract(video, weights, output, provenance, options=None, model_factory=None):
    options = options or Options()
    options.validate()
    video, weights, output = Path(video).resolve(), Path(weights).resolve(), Path(output).resolve()
    if not provenance.get("database_verified") or provenance.get("product_type") != "BOTELLA":
        raise ValueError("Primero verificar el análisis y video con read_analysis().")
    # Nunca escribir debajo de media ni junto al video de entrada.
    if output.is_relative_to(ROOT / "media") or output.is_relative_to(video.parent):
        raise ValueError("La salida debe estar separada del video original y de media.")
    if not weights.is_file():
        raise FileNotFoundError(weights)  # No descargar pesos implícitamente.
    from django.core.files import File
    from produccion.videos import validar_video
    with video.open("rb") as source:
        validar_video(File(source))
    capture = cv2.VideoCapture(str(video))
    try:
        fps = capture.get(cv2.CAP_PROP_FPS)
        width, height = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)), int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if not capture.isOpened() or not math.isfinite(fps) or fps <= 0 or width <= 0 or height <= 0:
            raise ValueError("Video sin metadatos válidos.")
    finally:
        capture.release()
    source_hash, weights_hash = sha256(video), sha256(weights)
    # mkdir exclusivo: jamás sobrescribir una ejecución previa.
    output.mkdir(parents=True, exist_ok=False)
    if model_factory is None:
        from ultralytics import YOLO
        model_factory = YOLO
    from ultralytics.utils import YAML
    from ultralytics.utils.checks import check_yaml
    tracker_path = Path(check_yaml("bytetrack.yaml"))
    run_id = str(uuid4())
    config = {"weights_sha256": weights_hash, "classes": [39], "conf": 0.30, "imgsz": 640,
              "tracker": "bytetrack.yaml", "tracker_sha256": sha256(tracker_path),
              "tracker_config": YAML.load(tracker_path), "persist": True, "stream": True,
              "save": False, "device": "cpu", "verbose": False}
    manifest = {"schema_version": "1.0.0", "run_id": run_id,
                "created_at": datetime.now(timezone.utc).isoformat(), "source": provenance,
                "source_video": str(video), "source_sha256": source_hash,
                "taxonomy_sha256": sha256(Path(__file__).with_name("taxonomy.json")),
                "video": {"width": width, "height": height, "fps": fps,
                          "timestamp_basis": "frame_index / nominal_fps; not exact VFR PTS"},
                "detector": config, "selection": asdict(options),
                "versions": {p: importlib.metadata.version(p) for p in ["ultralytics", "torch", "opencv-python"]},
                "status": "RUNNING"}
    def save_json(name, data):
        # Solo se reemplaza nuestro metadato de progreso dentro de la ejecución nueva.
        (output / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    save_json("run.json", manifest)
    selector, previous, counted = Selector(options), {}, set()
    frames, results = 0, None
    try:
        model = model_factory(str(weights))
        results = model.track(source=str(video), classes=[39], conf=0.30, imgsz=640,
                              tracker="bytetrack.yaml", persist=True, stream=True,
                              save=False, device="cpu", verbose=False)
        for result in results:
            if frames >= 7200:
                raise ValueError("Video fuera del límite de fotogramas.")
            boxes = result.boxes
            if boxes is not None and boxes.id is not None:
                for box, identity, confidence in zip(boxes.xyxy.cpu().numpy(), boxes.id.cpu().numpy(), boxes.conf.cpu().numpy()):
                    track_id = int(identity)
                    x1, _, x2, _ = map(int, box)
                    center = (x1 + x2) // 2
                    old = previous.get(track_id)
                    # Auditoría independiente de la regla existente; no escribe el conteo CU-09.
                    if frames == 0 or (old is not None and old > width // 2 and center <= width // 2):
                        counted.add(track_id)
                    previous[track_id] = center
                    selector.consider(track_id, result.orig_img, box, frames, fps, confidence)
            frames += 1
        if not frames:
            raise ValueError("No se leyeron fotogramas.")
        records, exact_hashes, coverage = [], set(), []
        for track_id in sorted(counted):
            saved = 0
            for sample in sorted(selector.samples.get(track_id, []), key=lambda s: s["frame_index"]):
                digest = hashlib.sha256(sample["png"]).hexdigest()
                if digest in exact_hashes:
                    selector.stats["exact_duplicate"] += 1
                    continue
                exact_hashes.add(digest)
                bucket = "review" if sample["quality"]["flags"] else "unlabeled"
                relative = Path("images") / bucket / f"a{provenance['analysis_id']}_{run_id}_t{track_id}_f{sample['frame_index']:06d}.png"
                (output / relative).parent.mkdir(parents=True, exist_ok=True)
                with (output / relative).open("xb") as destination:
                    destination.write(sample["png"])
                record = {k: v for k, v in sample.items() if k not in ["png", "thumb", "fingerprint", "rank"]}
                record.update({"sample_id": str(uuid4()), "image": relative.as_posix(), "image_sha256": digest,
                               "analysis_id": provenance["analysis_id"], "run_id": run_id, "track_id": track_id,
                               "source_sha256": source_hash, "counted_in_this_run": True,
                               "split": "UNASSIGNED", "physical_bottle_id": None, "capture_session_id": None,
                               "annotation_status": "PENDING", "annotator": None, "reviewer": None,
                               "labels": {"RAYADURA": None, "DEFORMACION": None, "TAPA_DEFECTUOSA": None},
                               "evaluable": {"body": None, "cap": None}, "other_defect": None})
                records.append(record)
                saved += 1
            coverage.append({"track_id": track_id, "saved_crops": saved,
                             "quality_pass": sum(r["track_id"] == track_id and r["quality"]["status"] == "PASS" for r in records)})
        (output / "samples.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")
        if sha256(video) != source_hash or sha256(weights) != weights_hash:
            raise ValueError("El video o los pesos cambiaron durante la extracción.")
        manifest.update({"status": "COMPLETED", "frames_processed": frames,
                         "audit_count": len(counted), "counted_track_ids": sorted(counted),
                         "saved_crops": len(records), "coverage": coverage, "selection_stats": dict(selector.stats),
                         "warning": "IDs locales a esta ejecución; no reasignar inspecciones históricas automáticamente."})
        save_json("run.json", manifest)
        return manifest
    except Exception as error:
        manifest.update({"status": "FAILED", "error_type": type(error).__name__, "error": str(error)})
        save_json("run.json", manifest)
        raise
    finally:
        if results is not None and hasattr(results, "close"):
            results.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--analysis-id", type=int, required=True)
    parser.add_argument("--database", type=Path, default=ROOT / "db.sqlite3")
    parser.add_argument("--media-root", type=Path, default=ROOT / "media")
    parser.add_argument("--weights", type=Path, default=ROOT / "yolo11n.pt")
    parser.add_argument("--output", type=Path, required=True, help="Carpeta nueva, fuera de media y de la carpeta del video.")
    parser.add_argument("--max-per-track", type=int, default=5)
    parser.add_argument("--min-interval", type=float, default=0.4)
    args = parser.parse_args()
    options = Options(max_per_track=args.max_per_track, min_interval_seconds=args.min_interval)
    provenance = read_analysis(args.database, args.analysis_id, args.video, args.media_root)
    result = extract(args.video, args.weights, args.output, provenance, options)
    print(json.dumps({k: result[k] for k in ["run_id", "status", "frames_processed", "audit_count", "saved_crops"]}, indent=2))


if __name__ == "__main__":
    main()
