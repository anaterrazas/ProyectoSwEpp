"""Contrato experimental Calidad v002. Consume observaciones; no ejecuta modelos.

No convierte ROI en tapas ni el clasificador binario heredado en cinco clases.
La asociación queda pendiente hasta disponer de detector y perfil evaluados.
"""
from copy import deepcopy
import math
import re

CLASES_INSPECCION = ("TAPA_AUSENTE", "TAPA_MAL_COLOCADA", "TAPA_CORRECTA", "RAYADURA", "DEFORMACION")


def validar_caja(caja):
    if not isinstance(caja, (list, tuple)) or len(caja) != 4:
        raise ValueError("Caja XYXY inválida")
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in caja):
        raise ValueError("Coordenadas no finitas")
    if not (0 <= caja[0] < caja[2] and 0 <= caja[1] < caja[3]):
        raise ValueError("Caja vacía o negativa")
    return list(caja)


def clases_pendientes():
    return {clase: {"estado": "NO DISPONIBLE", "prediccion": None, "score": None,
                    "motivo": "Sin modelo evaluado para esta clase y dominio"}
            for clase in CLASES_INSPECCION}


def preparar_fotograma(registro, *, fuente_sha256, ejecucion_id):
    """Representación derivada de frames.jsonl de individual_v001, sin reetiquetar.

    Todos los datos de detección salen del registro original. Los estados nuevos
    expresan indisponibilidad de capacidades, nunca verdad humana o conformidad.
    """
    if not re.fullmatch(r"[0-9a-f]{64}", fuente_sha256):
        raise ValueError("Falta hash de fuente válido")
    if not isinstance(ejecucion_id, str) or not ejecucion_id.strip():
        raise ValueError("Falta ejecución de origen")
    indice = registro.get("frame_index")
    if type(indice) is not int or indice < 0:
        raise ValueError("Índice de fotograma inválido")
    objetos = []
    ids = set()
    for numero, dato in enumerate(registro.get("objects", [])):
        if dato.get("label") != "bottle" or dato.get("class_id") != 39:
            raise ValueError("Este adaptador solo admite el baseline bottle → ENVASE")
        if dato.get("observed_this_frame") is not True:
            raise ValueError("No se aceptan posiciones sin observación actual")
        if dato.get("frame_index") != indice or dato.get("video_sha256") != fuente_sha256 or dato.get("run_id") != ejecucion_id:
            raise ValueError("Procedencia de objeto incompatible con fotograma")
        caja = validar_caja(dato.get("bbox_xyxy"))
        score = dato.get("score")
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score) or not 0 <= score <= 1:
            raise ValueError("Score inválido")
        track = dato.get("track_id")
        if track is not None:
            if type(track) is not int or track <= 0 or track in ids:
                raise ValueError("ID temporal inválido o repetido en el fotograma")
            ids.add(track)
        roi = deepcopy(dato.get("cap_neck_region"))
        if roi:
            validar_caja(roi.get("bbox_xyxy"))
        objetos.append({
            "observacion_id": f"{ejecucion_id}:{indice}:{numero}",
            "clase": "ENVASE", "bbox_xyxy": caja, "score": score,
            "track_id": track, "track_namespace": ejecucion_id, "identidad_fisica": None,
            "visibilidad": {"estado": "NO EVALUABLE", "origen": "SIN_REFERENCIA_HUMANA_EN_ESTA_OBSERVACION",
                            "control_tecnico_original": deepcopy(dato.get("cap_neck_region", {}).get("quality"))},
            "roi_cuello_candidata": roi, "roi_es_tapa_detectada": False,
            "tapa_asociada": None, "asociacion": {"estado": "NO EVALUABLE", "motivo": "Sin detector TAPA evaluado"},
            "inspeccion": {"estado": "NO EVALUABLE", "conformidad_global": None, "clases": clases_pendientes()},
            "resultado_heredado": deepcopy(dato.get("classes", {})),
        })
    return {"schema": "calidad_individual_v002.preparacion.1", "frame_index": indice,
            "pts_seconds": registro.get("pts_seconds"), "timestamp_seconds": registro.get("timestamp_seconds"),
            "fuente_sha256": fuente_sha256, "ejecucion_origen": ejecucion_id,
            "envases_observados": objetos, "tapas_observadas": None,
            "detector_tapa": "NO DISPONIBLE", "inferencia_nueva": False,
            "asociacion_habilitada": False, "referencia_humana": False}


def recortar_region(imagen, caja):
    """Copia una caja existente, sin detectar, inferir visibilidad ni alterar imagen.

    El llamador debe indicar si se trata de ROI geométrica o caja observada.
    No se recortan cajas fuera de imagen silenciosamente.
    """
    x1, y1, x2, y2 = validar_caja(caja)
    alto, ancho = imagen.shape[:2]
    if x2 > ancho or y2 > alto:
        raise ValueError("Región fuera de la imagen")
    return imagen[math.floor(y1):math.ceil(y2), math.floor(x1):math.ceil(x2)].copy()
