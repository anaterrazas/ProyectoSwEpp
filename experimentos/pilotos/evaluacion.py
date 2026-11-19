"""Congela referencia existente y compara solo localización ENVASE/TAPA.

No clasifica defectos ni calcula métricas temporales a partir de cajas aisladas.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
from .fuentes import REFERENCIAS, ROOT


def leer(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def iou(a, b):
    inter = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
    union = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - inter
    return inter / union if union else 0


def comparar(referencia, predicciones, umbral=.5):
    if not 0 < umbral <= 1:
        raise ValueError("IoU debe estar entre 0 y 1.")
    registros = {r["sample_id"]: r for r in referencia["records"]}
    if len(registros) != len(referencia["records"]):
        raise ValueError("Referencias duplicadas.")
    muestras = predicciones["samples"]
    clases_activas = set(predicciones.get("clases_ejecutadas", ["ENVASE", "TAPA"]))
    if not clases_activas or not clases_activas <= {"ENVASE", "TAPA"}:
        raise ValueError("Declare las clases realmente ejecutadas.")
    ids = [s["sample_id"] for s in muestras]
    if len(ids) != len(set(ids)) or set(ids) - registros.keys():
        raise ValueError("Predicciones duplicadas o sin referencia.")
    totales = {c: {"tp": 0, "fp": 0, "fn": 0, "ignoradas": 0} for c in ("ENVASE", "TAPA")}
    detalle = []
    for muestra in muestras:
        ref = registros[muestra["sample_id"]]
        anotacion = ref["annotation"]
        if anotacion["status"] != "reviewed" or not anotacion["exhaustive"]:
            raise ValueError("Se requiere referencia exhaustiva revisada.")
        if muestra.get("image_sha256") != ref["source"]["image_sha256"]:
            raise ValueError("La predicción no corresponde a la imagen de referencia.")
        cajas = anotacion["boxes"]
        usados = set()
        resultados_predicciones = []
        cuentas = {c: {"tp": 0, "fp": 0, "fn": 0, "ignoradas": 0} for c in totales}
        for numero, deteccion in sorted(enumerate(muestra["detections"]), key=lambda par: par[1]["score"], reverse=True):
            clase = deteccion["class_name"]
            caja = deteccion["bbox_xyxy"]
            score = deteccion["score"]
            if (clase not in clases_activas or len(caja) != 4 or not all(math.isfinite(v) for v in caja)
                    or caja[2] <= caja[0] or caja[3] <= caja[1] or not math.isfinite(score) or not 0 <= score <= 1):
                raise ValueError("Predicción inválida.")
            candidatos = [(iou(caja, b["bbox_xyxy"]), i) for i, b in enumerate(cajas)
                          if b["class_name"] == clase and b.get("not_evaluable") is False and i not in usados]
            mejor = max(candidatos, default=(0, None))
            if mejor[0] >= umbral:
                usados.add(mejor[1])
                cuentas[clase]["tp"] += 1
                estado = "TP"
            elif any(iou(caja, b["bbox_xyxy"]) > 0 for b in cajas
                     if b["class_name"] == clase and b.get("not_evaluable") is not False):
                cuentas[clase]["ignoradas"] += 1
                estado = "IGNORADA"
            else:
                cuentas[clase]["fp"] += 1
                estado = "FP"
            resultados_predicciones.append({"prediction_index": numero, "estado": estado,
                "reference_index": mejor[1] if estado == "TP" else None,
                "iou_match": mejor[0] if estado == "TP" else None, **deteccion})
        resultados_referencias = []
        for i, caja in enumerate(cajas):
            if caja["class_name"] in clases_activas and caja.get("not_evaluable") is False and i not in usados:
                cuentas[caja["class_name"]]["fn"] += 1
            estado = ("NO_EVALUABLE" if caja.get("not_evaluable") is not False else
                      "CLASE_NO_EJECUTADA" if caja["class_name"] not in clases_activas else
                      "TP" if i in usados else "FN")
            resultados_referencias.append({"reference_index": i, "estado": estado, **caja})
        for clase in totales:
            for campo, valor in cuentas[clase].items():
                totales[clase][campo] += valor
        detalle.append({"sample_id": muestra["sample_id"], "conteos": cuentas,
                        "predicciones": resultados_predicciones, "referencias": resultados_referencias})
    for clase, cuenta in totales.items():
        if clase not in clases_activas:
            cuenta.update(tp=None, fp=None, fn=None, ignoradas=None, precision=None, recall=None, estado="NO_EJECUTADA")
            continue
        tp, fp, fn = cuenta["tp"], cuenta["fp"], cuenta["fn"]
        cuenta["precision"] = tp / (tp + fp) if tp + fp else None
        cuenta["recall"] = tp / (tp + fn) if tp + fn else None
    return {"alcance": "LOCALIZACION_EN_FOTOGRAMAS_REVISADOS", "iou": umbral,
            "regla": "orden por score descendente; coincidencia única, misma clase, IoU mínimo",
            "regla_ignoradas": "Sin match evaluable, cualquier intersección positiva con una región no evaluable de la misma clase excluye la predicción de FP; política conservadora",
            "muestras_comparadas": len(muestras), "referencias_disponibles": len(registros),
            "no_ejecutadas": sorted(registros.keys() - set(ids)), "por_clase": totales, "detalle": detalle,
            "defectos": {"metricas": None, "motivo": "Sin referencia estructurada de defecto por unidad/etapa"},
            "seguimiento": {"metricas": None, "motivo": "Sin trayectorias humanas continuas"},
            "RAYADURA": "NO DISPONIBLE", "DEFORMACION": "NO DISPONIBLE",
            "advertencia": "Prueba de desarrollo; no es precisión industrial ni mAP."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="accion", required=True)
    preparar = sub.add_parser("preparar")
    preparar.add_argument("--salida", type=Path, required=True)
    comparar_cli = sub.add_parser("comparar")
    comparar_cli.add_argument("--referencias", type=Path, required=True)
    comparar_cli.add_argument("--predicciones", type=Path, required=True)
    comparar_cli.add_argument("--salida", type=Path, required=True)
    args = parser.parse_args()
    if args.accion == "preparar":
        fuente = REFERENCIAS / "manifest.json"
        manifiesto = leer(fuente)
        registros = []
        for frame in manifiesto["frames"]:
            revision = sorted((REFERENCIAS / "revisions" / frame["sample_id"]).glob("*.json"))[-1]
            anotacion = leer(revision)
            if anotacion["status"] != "reviewed" or not anotacion["exhaustive"]:
                raise ValueError("Hay referencias pendientes de revisión exhaustiva.")
            registros.append({"sample_id": frame["sample_id"], "source": frame,
                "annotation": anotacion, "revision_origen": str(revision.relative_to(ROOT)),
                "revision_sha256": hashlib.sha256(revision.read_bytes()).hexdigest()})
        if len(registros) != 25:
            raise ValueError("La referencia cambió; revisar antes de congelar.")
        salida = args.salida.resolve()
        if not salida.is_relative_to(ROOT / "output"):
            raise ValueError("La preparación debe estar dentro de output.")
        salida.mkdir(parents=True, exist_ok=False)
        (salida / "referencias.json").write_text(json.dumps({"records": registros}, ensure_ascii=False, indent=2), encoding="utf-8")
        plan = {"referencia_origen": str(fuente.relative_to(ROOT)),
                "referencia_sha256": hashlib.sha256(fuente.read_bytes()).hexdigest(),
                "fotogramas": 25, "anotaciones_fuente": "SOLO_LECTURA",
                "regiones_no_evaluables": "Conservadas en JSON; no eliminadas por el filtro de exportación YOLO",
                "alcance_revision": "Anotación humana; no equivale a revisión independiente de calidad",
                "separacion": ["personas_epp", "envase_tapa", "defectos", "seguimiento"],
                "predicciones": "PENDIENTES_NO_EJECUTADAS", "RAYADURA": "NO DISPONIBLE", "DEFORMACION": "NO DISPONIBLE"}
        (salida / "plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
    else:
        resultado = comparar(leer(args.referencias), leer(args.predicciones))
        resultado["referencias_sha256"] = hashlib.sha256(args.referencias.read_bytes()).hexdigest()
        resultado["predicciones_sha256"] = hashlib.sha256(args.predicciones.read_bytes()).hexdigest()
        with args.salida.open("x", encoding="utf-8") as archivo:
            json.dump(resultado, archivo, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
