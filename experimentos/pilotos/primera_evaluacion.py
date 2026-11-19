"""Auditoría y artefactos de la primera evaluación real, sin escribir en fuentes."""
import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import html
import json
import math
from pathlib import Path

import cv2

from .evaluacion import comparar, iou
from .fuentes import ROOT, REFERENCIAS


def sha(p):
    with Path(p).open("rb") as archivo:
        return hashlib.file_digest(archivo, "sha256").hexdigest()


def leer(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def guardar(p, dato):
    with Path(p).open("x", encoding="utf-8") as archivo:
        json.dump(dato, archivo, ensure_ascii=False, indent=2)


def conflictos_semanticos(records):
    """Alertas a adjudicar; nunca reclasifican ni corrigen las etiquetas humanas."""
    return [{"sample_id": ref["sample_id"], "box_id": b["box_id"],
             "clase_guardada": b["class_name"], "nota_humana": b.get("notes"),
             "motivo": "Clase ENVASE con nota que describe una tapa; requiere adjudicación humana"}
            for ref in records for b in ref["annotation"]["boxes"]
            if b["class_name"] == "ENVASE" and b.get("notes", "").strip().lower().startswith("tapa ")]


def auditar(salida):
    if not salida.resolve().is_relative_to(ROOT / "output/experimental_pilotos"):
        raise ValueError("Salida fuera del laboratorio.")
    manifiesto = leer(REFERENCIAS / "manifest.json")
    if len(manifiesto["frames"]) != 25:
        raise ValueError("Se esperaban los mismos 25 fotogramas humanos.")
    protegidos = {}
    for base in [ROOT / "produccion", ROOT / "config"]:
        for p in base.rglob("*"):
            if p.is_file() and "__pycache__" not in p.parts:
                protegidos[str(p.relative_to(ROOT))] = sha(p)
    for p in [ROOT / "db.sqlite3", REFERENCIAS / "manifest.json"]:
        protegidos[str(p.relative_to(ROOT))] = sha(p)
    for p in (REFERENCIAS / "revisions").rglob("*.json"):
        protegidos[str(p.relative_to(ROOT))] = sha(p)
    videos = {v["video_id"]: v for v in manifiesto["videos"]}
    for video in videos.values():
        p = Path(video["source_path"])
        if not p.resolve().is_relative_to(ROOT) or sha(p) != video["video_sha256"]:
            raise ValueError("Video fuente alterado o fuera del workspace.")
        protegidos[str(p.relative_to(ROOT))] = video["video_sha256"]
    historial = Counter()
    for p in (REFERENCIAS / "revisions").rglob("*.json"):
        historial[leer(p)["status"]] += 1
    records, muestras = [], []
    resumen = Counter()
    hashes_imagen = set()
    for frame in manifiesto["frames"]:
        sid = frame["sample_id"]
        p = (REFERENCIAS / frame["image"]).resolve()
        if not p.is_relative_to(REFERENCIAS) or sha(p) != frame["image_sha256"]:
            raise ValueError(f"Hash de imagen incorrecto: {sid}")
        if frame["image_sha256"] in hashes_imagen:
            raise ValueError("Imagen repetida entre referencias.")
        hashes_imagen.add(frame["image_sha256"])
        protegidos[str(p.relative_to(ROOT))] = sha(p)
        imagen = cv2.imread(str(p))
        h, w = imagen.shape[:2]
        if [w, h] != [frame["width"], frame["height"]]:
            raise ValueError("Dimensiones inconsistentes.")
        revision = sorted((REFERENCIAS / "revisions" / sid).glob("*.json"))[-1]
        anotacion = leer(revision)
        if anotacion["sample_id"] != sid or anotacion["source"]["image_sha256"] != frame["image_sha256"]:
            raise ValueError("Asociación de anotación e imagen inconsistente.")
        resumen["frames_" + anotacion["status"]] += 1
        cerrado = anotacion["status"] == "reviewed" and anotacion.get("exhaustive") is True
        cajas_frame = []
        ids = {b["box_id"]: b for b in anotacion["boxes"]}
        if len(ids) != len(anotacion["boxes"]):
            raise ValueError("ID de caja repetido.")
        for b in anotacion["boxes"]:
            clase = b["class_name"]
            x1, y1, x2, y2 = b["bbox_xyxy"]
            if clase not in ("ENVASE", "TAPA") or not all(math.isfinite(v) for v in [x1,y1,x2,y2]) or not (0 <= x1 < x2 <= w and 0 <= y1 < y2 <= h):
                raise ValueError(f"Caja inválida en {sid}")
            estado = "evaluable" if cerrado and b.get("not_evaluable") is False else "no_evaluable_o_desconocida" if cerrado else "borrador"
            resumen[f"{clase}_{estado}"] += 1
            for atributo in ("partial", "occluded"):
                if b.get(atributo) is True:
                    resumen[atributo] += 1
            pequena = min(x2 - x1, y2 - y1) < 16
            proyectada = min(x2 - x1, y2 - y1) * 640 / max(w, h) < 16
            resumen["cajas_pequenas_nativas"] += pequena
            resumen["cajas_pequenas_entrada_640"] += proyectada
            parent = b.get("parent_envase_box_id")
            if clase == "TAPA":
                resumen["tapas_con_asociacion" if parent else "tapas_sin_asociacion"] += 1
                if parent and (parent not in ids or ids[parent]["class_name"] != "ENVASE"):
                    raise ValueError("Asociación tapa-envase inválida.")
            cajas_frame.append({"box_id": b["box_id"], "clase": clase, "estado": estado,
                "pequena_nativa": pequena, "pequena_640": proyectada,
                "occluded": b.get("occluded"), "partial": b.get("partial"), "parent": parent})
        nitidez = float(cv2.Laplacian(cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var())
        resumen["frames_posible_desenfoque"] += nitidez < 50
        muestras.append({"sample_id": sid, "video_id": frame["video_id"], "frame_index": frame["frame_index"],
            "pts_seconds": frame["pts_seconds"], "estado": anotacion["status"], "exhaustive": anotacion.get("exhaustive"),
            "sha256": frame["image_sha256"], "revision_sha256": sha(revision), "nitidez_laplaciano": nitidez,
            "posible_desenfoque": nitidez < 50, "cajas": cajas_frame})
        records.append({"sample_id": sid, "source": frame, "annotation": anotacion,
            "revision_origen": str(revision.relative_to(ROOT)), "revision_sha256": sha(revision)})
    salida.mkdir(parents=True, exist_ok=False)
    guardar(salida / "referencias.json", {"records": records})
    guardar(salida / "auditoria.json", {"fecha_utc": datetime.now(timezone.utc).isoformat(),
        "resumen": dict(resumen), "historial_versiones_no_sumar_como_muestras": dict(historial),
        "muestras": muestras, "protegidos_antes": protegidos,
        "nota": "Reviewed es cierre del anotador, no segunda revisión independiente. Nitidez <50 es aviso técnico, no etiqueta humana."})
    guardar(salida / "conflictos_semanticos.json", conflictos_semanticos(records))
    print(json.dumps(dict(resumen)), flush=True)
    if resumen.get("frames_reviewed") != 25:
        raise ValueError("Hay borradores: auditoría conservada, inferencia y métricas bloqueadas.")


def dibujar(imagen, cajas, prediccion):
    colores = {"TP": (40, 180, 30), "FP": (20, 20, 230), "FN": (0, 130, 240),
        "IGNORADA": (150, 150, 150), "NO_EVALUABLE": (150, 150, 150), "CLASE_NO_EJECUTADA": (210, 80, 180)}
    escala = 1  # Derivado a resolución nativa para revisar objetos pequeños al ampliar.
    copia = cv2.resize(imagen, (round(imagen.shape[1]*escala), round(imagen.shape[0]*escala)))
    for b in cajas:
        x1,y1,x2,y2 = [round(v*escala) for v in b["bbox_xyxy"]]
        color = colores[b["estado"]]
        cv2.rectangle(copia, (x1,y1), (x2,y2), color, 2)
        indice = b["prediction_index"] if prediccion else b["reference_index"]
        texto = f"{'P' if prediccion else 'H'}{indice} {b['class_name']} {b['estado']}"
        if prediccion:
            texto += f" {b['score']:.2f}"
        cv2.putText(copia, texto, (max(0,x1), max(12,y1+12)), cv2.FONT_HERSHEY_SIMPLEX, .35, (0,0,0), 2)
        cv2.putText(copia, texto, (max(0,x1), max(12,y1+12)), cv2.FONT_HERSHEY_SIMPLEX, .35, color, 1)
    return copia


def finalizar(salida):
    auditoria = leer(salida / "auditoria.json")
    refs = leer(salida / "referencias.json")
    preds = leer(salida / "predicciones.json")
    resultado = comparar(refs, preds)
    guardar(salida / "comparacion.json", resultado)
    mapa = {r["sample_id"]: r for r in refs["records"]}
    conflictos = conflictos_semanticos(refs["records"])
    frames_conflicto = {c["sample_id"] for c in conflictos}
    if not (salida / "conflictos_semanticos.json").exists():
        guardar(salida / "conflictos_semanticos.json", conflictos)
    avisos = {r["sample_id"]: r for r in auditoria["muestras"]}
    por_video = {}
    for video_id in {r["source"]["video_id"] for r in refs["records"]}:
        registros = [r for r in refs["records"] if r["source"]["video_id"] == video_id]
        ids = {r["sample_id"] for r in registros}
        por_video[video_id] = comparar({"records": registros}, {**preds, "samples": [p for p in preds["samples"] if p["sample_id"] in ids]})
    guardar(salida / "por_video.json", por_video)
    (salida / "galeria").mkdir()
    cards, errores, analisis_cajas = [], [], []
    for detalle in resultado["detalle"]:
        sid = detalle["sample_id"]
        ref = mapa[sid]
        imagen = cv2.imread(str(REFERENCIAS / ref["source"]["image"]))
        for tipo, cajas in (("humano", detalle["referencias"]), ("prediccion", detalle["predicciones"])):
            if not cv2.imwrite(str(salida / "galeria" / f"{sid}_{tipo}.jpg"), dibujar(imagen, cajas, tipo == "prediccion")):
                raise OSError("No se pudo generar la galería.")
        for tipo, cajas in (("prediccion", detalle["predicciones"]), ("referencia", detalle["referencias"])):
            for b in cajas:
                fila = {"sample_id": sid, "video_id": ref["source"]["video_id"], "frame_index": ref["source"]["frame_index"],
                    "pts_seconds": ref["source"]["pts_seconds"], "tipo": tipo, "estado": b["estado"],
                    "clase": b["class_name"], "box_id": b.get("box_id"), "bbox_xyxy": b["bbox_xyxy"],
                    "score": b.get("score"), "occluded": b.get("occluded"), "partial": b.get("partial"),
                    "posible_desenfoque": avisos[sid]["posible_desenfoque"]}
                if tipo == "referencia":
                    fila["max_iou_con_prediccion_misma_clase"] = max((iou(b["bbox_xyxy"], p["bbox_xyxy"]) for p in detalle["predicciones"] if p["class_name"] == b["class_name"]), default=None)
                    a = next(a for a in avisos[sid]["cajas"] if a["box_id"] == b["box_id"])
                    fila.update(pequena_640=a["pequena_640"], asociacion_padre=a["parent"])
                    analisis_cajas.append(fila)
                if b["estado"] in ("FP", "FN", "IGNORADA", "NO_EVALUABLE", "CLASE_NO_EJECUTADA"):
                    errores.append(fila)
        datos = html.escape(json.dumps(detalle, ensure_ascii=False, indent=2))
        notas = html.escape(json.dumps(ref["annotation"]["boxes"], ensure_ascii=False, indent=2))
        alerta = '<p>ALERTA: contradicción entre clase ENVASE y nota humana; requiere adjudicación, sin modificar etiquetas.</p>' if sid in frames_conflicto else ''
        cards.append(f'<article><h2>{html.escape(sid)}</h2>{alerta}<p>Frame {ref["source"]["frame_index"]} · PTS {ref["source"]["pts_seconds"]} s · posible desenfoque: {avisos[sid]["posible_desenfoque"]}</p><div class="paneles"><figure><figcaption>Referencia humana: verde TP, naranja FN, gris no evaluable, violeta TAPA no ejecutada</figcaption><a href="galeria/{sid}_humano.jpg"><img loading="lazy" src="galeria/{sid}_humano.jpg" alt="Anotaciones humanas"></a></figure><figure><figcaption>Predicciones reales: verde TP, rojo FP, gris ignorada</figcaption><a href="galeria/{sid}_prediccion.jpg"><img loading="lazy" src="galeria/{sid}_prediccion.jpg" alt="Predicciones reales"></a></figure></div><details><summary>Cajas, coincidencias y errores</summary><pre>{datos}</pre></details><details><summary>Notas humanas originales</summary><pre>{notas}</pre></details></article>')
    guardar(salida / "errores.json", errores)
    guardar(salida / "analisis_objetos.json", analisis_cajas)
    with (salida / "errores.csv").open("x", encoding="utf-8-sig", newline="") as archivo:
        campos = sorted({k for fila in errores for k in fila})
        escritor = csv.DictWriter(archivo, fieldnames=campos)
        escritor.writeheader()
        escritor.writerows(errores)
    metricas = html.escape(json.dumps(resultado["por_clase"], ensure_ascii=False, indent=2))
    pagina = '<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Evaluación experimental ENVASE/TAPA</title><style>body{font:15px system-ui;margin:25px;color:#183047}article{padding:20px 0;border-top:1px solid #bbc}.paneles{display:flex;gap:15px}figure{margin:0;width:50%}img{width:100%}pre{white-space:pre-wrap}figcaption{min-height:45px}@media(max-width:800px){.paneles{display:block}figure{width:100%}}</style></head><body><h1>Primera evaluación experimental · 25 fotogramas</h1><p>YOLO11s COCO bottle → ENVASE. Confianza 0,30; imgsz 640; IoU ≥0,50. TAPA: detector no disponible. No se evaluaron defectos ni seguimiento.</p><p>Las imágenes mostradas son derivados de visualización: los originales y etiquetas humanas no se modificaron. Fotogramas correlacionados ya usados en desarrollo; no es validación industrial.</p><pre>' + metricas + '</pre><p>Clic en cada imagen para verla ampliada. H indica índice humano y P índice de predicción dentro del fotograma.</p>' + ''.join(cards) + '</body></html>'
    if conflictos:
        pagina = pagina.replace('<pre>', f'<aside style="background:#fff1cf;padding:16px">Referencia pendiente de adjudicación: {len(conflictos)} cajas ENVASE tienen notas que describen tapas. Cifras provisionales contra las etiquetas actuales; no acreditan rendimiento real final. Consulte conflictos_semanticos.json.</aside><pre>', 1)
    (salida / "index.html").write_text(pagina, encoding="utf-8")
    cambios = [p for p, digest in auditoria["protegidos_antes"].items() if sha(ROOT / p) != digest]
    if cambios:
        raise RuntimeError(f"Entradas protegidas modificadas: {cambios}")
    guardar(salida / "verificacion.json", {"entradas_protegidas_sin_cambios": len(auditoria["protegidos_antes"]),
        "cambios": cambios, "originales_modificados": False, "entrenamiento": False,
        "predicciones_usadas_como_referencia": False,
        "sha256_salidas": {str(p.relative_to(salida)): sha(p) for p in salida.rglob("*") if p.is_file()}})
    print(json.dumps(resultado["por_clase"], ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("accion", choices=["auditar", "finalizar"])
    parser.add_argument("--salida", required=True, type=Path)
    args = parser.parse_args()
    salida = args.salida.resolve()
    if not salida.is_relative_to(ROOT / "output/experimental_pilotos"):
        raise ValueError("Fuera del laboratorio.")
    (auditar if args.accion == "auditar" else finalizar)(salida)


if __name__ == "__main__":
    main()
