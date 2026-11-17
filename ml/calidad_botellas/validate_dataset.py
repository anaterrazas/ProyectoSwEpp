"""Comprueba integridad, etiquetas y separación sin modificar el dataset."""
import argparse
from collections import Counter
import json
from pathlib import Path

import cv2

from .extract_crops import sha256


def validate(root, ready=False):
    root = Path(root).resolve()
    run = json.loads((root / "run.json").read_text(encoding="utf-8"))
    if run["status"] != "COMPLETED":
        raise ValueError("La ejecución no terminó correctamente.")
    rows = [json.loads(line) for line in (root / "samples.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    ids, hashes, groups, per_track = set(), set(), {}, Counter()
    for row in rows:
        path = (root / row["image"]).resolve()
        if not path.is_relative_to(root / "images") or not path.is_file():
            raise ValueError("Ruta de imagen inválida o ausente.")
        if row["sample_id"] in ids or row["image_sha256"] in hashes:
            raise ValueError("Recorte duplicado.")
        ids.add(row["sample_id"])
        hashes.add(row["image_sha256"])
        if sha256(path) != row["image_sha256"]:
            raise ValueError("Imagen modificada desde la extracción.")
        image = cv2.imread(str(path))
        if image is None or list(image.shape[:2]) != [row["quality"]["height"], row["quality"]["width"]]:
            raise ValueError("Imagen ilegible o dimensiones inconsistentes.")
        if (row["analysis_id"] != run["source"]["analysis_id"] or row["run_id"] != run["run_id"]
                or row["source_sha256"] != run["source_sha256"]
                or row["track_id"] not in run["counted_track_ids"] or not row["counted_in_this_run"]):
            raise ValueError("Procedencia inconsistente.")
        if not 0 <= row["frame_index"] < run["frames_processed"]:
            raise ValueError("Fotograma inválido.")
        left, top, right, bottom = row["crop_box_xyxy"]
        if not (0 <= left < right <= run["video"]["width"] and 0 <= top < bottom <= run["video"]["height"]
                and right - left == image.shape[1] and bottom - top == image.shape[0]):
            raise ValueError("Coordenadas inconsistentes.")
        if set(row["labels"]) != {"RAYADURA", "DEFORMACION", "TAPA_DEFECTUOSA"} or any(
            v is not None and (type(v) is not int or v not in (0, 1)) for v in row["labels"].values()
        ):
            raise ValueError("Etiquetas multietiqueta inválidas.")
        if set(row["evaluable"]) != {"body", "cap"} or any(
            v is not None and type(v) is not bool for v in row["evaluable"].values()
        ):
            raise ValueError("Evaluabilidad inválida.")
        if row["annotation_status"] not in ("PENDING", "ANNOTATED", "REVIEWED"):
            raise ValueError("Estado de anotación inválido.")
        if row["annotation_status"] == "PENDING" and any(v is not None for v in row["labels"].values()):
            raise ValueError("Una muestra pendiente no debe contener etiquetas de defectos.")
        if row["split"] not in ("UNASSIGNED", "train", "val", "test"):
            raise ValueError("Partición inválida.")
        if ready and (row["annotation_status"] != "REVIEWED" or not row["annotator"] or not row["reviewer"]
                      or row["split"] == "UNASSIGNED" or not row["capture_session_id"] or not row["physical_bottle_id"]
                      or any(v is None for v in row["evaluable"].values()) or type(row["other_defect"]) is not bool):
            raise ValueError("Faltan revisión humana, evaluabilidad, identidad física o partición.")
        if row["split"] != "UNASSIGNED":
            for group in [("video", row["source_sha256"]), ("session", row["capture_session_id"]),
                          ("bottle", row["physical_bottle_id"])]:
                if group[1] is None:
                    continue
                if group in groups and groups[group] != row["split"]:
                    raise ValueError("Fuga de datos entre particiones.")
                groups[group] = row["split"]
        per_track[row["track_id"]] += 1
    if len(rows) != run["saved_crops"] or any(n > run["selection"]["max_per_track"] for n in per_track.values()):
        raise ValueError("Cantidad de recortes inconsistente.")
    if run["audit_count"] != len(set(run["counted_track_ids"])):
        raise ValueError("Conteo de auditoría inconsistente.")
    return {"samples": len(rows), "tracks_with_crops": len(per_track), "counted_tracks": run["audit_count"],
            "quality": dict(Counter(row["quality"]["status"] for row in rows)),
            "annotations": dict(Counter(row["annotation_status"] for row in rows)),
            "ready_check": ready, "status": "OK"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, nargs="+")
    parser.add_argument("--ready", action="store_true", help="Exige anotaciones revisadas y particiones; no entrena.")
    args = parser.parse_args()
    print(json.dumps(validate_many(args.directory, args.ready), ensure_ascii=False, indent=2))


def validate_many(roots, ready=False):
    reports, hashes, groups = [], set(), {}
    for root in roots:
        reports.append(validate(root, ready))
        rows = [json.loads(line) for line in (Path(root) / "samples.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
        for row in rows:
            if row["image_sha256"] in hashes:
                raise ValueError("Imagen duplicada entre ejecuciones; no combinar sin depurar.")
            hashes.add(row["image_sha256"])
            if row["split"] == "UNASSIGNED":
                continue
            for group in [("video", row["source_sha256"]), ("session", row["capture_session_id"]),
                          ("bottle", row["physical_bottle_id"])]:
                if group[1] is not None:
                    if group in groups and groups[group] != row["split"]:
                        raise ValueError("Fuga de datos entre ejecuciones o sesiones.")
                    groups[group] = row["split"]
    return {"status": "OK", "runs": reports, "unique_images": len(hashes)}


if __name__ == "__main__":
    main()
