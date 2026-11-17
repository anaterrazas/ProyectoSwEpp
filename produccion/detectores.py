"""Catálogo cerrado de detectores para los tres tipos del sistema EPP."""
from dataclasses import dataclass

from .models import Producto


@dataclass(frozen=True)
class Detector:
    pesos: str
    clases: tuple[int, ...]
    confianza: float
    tamano: int


# Incorporar aquí los pesos y clases de cajas/bolsas cuando hayan sido validados.
# None significa no disponible; nunca se sustituye por el detector de botellas.
DETECTORES = {
    Producto.Tipo.BOTELLA: Detector("yolo11n.pt", (39,), 0.30, 640),
    Producto.Tipo.CAJA: None,
    Producto.Tipo.BOLSA: None,
}


def detector_para_producto(producto):
    detector = DETECTORES.get(producto.tipo)
    if detector is None:
        raise ValueError(f"El conteo IA para {producto.get_tipo_display()} todavía no está habilitado.")
    return detector
