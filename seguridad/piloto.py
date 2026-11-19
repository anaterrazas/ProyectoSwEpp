"""Reglas del piloto: asociación conservadora y persistencia por track temporal."""
from dataclasses import dataclass
import math
import unicodedata


CLASES = {"CASCO": ("Hardhat", "NO-Hardhat"),
          "CHALECO": ("Safety Vest", "NO-Safety Vest")}
ALIAS = {"casco": "CASCO", "hardhat": "CASCO", "chaleco": "CHALECO",
         "chaleco reflectivo": "CHALECO", "safety vest": "CHALECO"}


def equipos_piloto(nombres):
    equipos = set()
    for nombre in nombres:
        normal = unicodedata.normalize("NFKD", nombre.strip().lower())
        normal = " ".join("".join(c for c in normal if not unicodedata.combining(c)).split())
        if normal not in ALIAS:
            raise ValueError(f"EPP fuera del alcance del piloto: {nombre}")
        equipos.add(ALIAS[normal])
    if not equipos:
        raise ValueError("Configure el EPP obligatorio del área antes de analizar cumplimiento.")
    return sorted(equipos)


def asociar(caja, personas, equipo):
    """Centro en región anatómica; empate entre personas se abstiene."""
    x1, y1, x2, y2 = caja
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    candidatos = []
    for track, (px1, py1, px2, py2) in personas.items():
        w, h = px2 - px1, py2 - py1
        if w <= 0 or h <= 0:
            continue
        inferior, superior = (0, .35) if equipo == "CASCO" else (.20, .75)
        if px1 <= cx <= px2 and py1 + h * inferior <= cy <= py1 + h * superior:
            candidatos.append((abs(cx - (px1 + px2) / 2) / w, track))
    candidatos.sort()
    if not candidatos or (len(candidatos) > 1 and candidatos[1][0] - candidatos[0][0] <= .15):
        return None
    return candidatos[0][1]


def estados(personas, detecciones, obligatorios):
    """Sin evidencia explícita, o con evidencia contradictoria: NO_EVALUABLE."""
    evidencia = {(track, equipo): set() for track in personas for equipo in obligatorios}
    for tipo, confianza, caja in detecciones:
        if not math.isfinite(confianza) or confianza < .30:
            continue
        for equipo in obligatorios:
            positivo, negativo = CLASES[equipo]
            if tipo not in (positivo, negativo):
                continue
            track = asociar(caja, personas, equipo)
            if track is not None:
                evidencia[track, equipo].add("CUMPLE" if tipo == positivo else "INCUMPLIMIENTO")
    return {clave: next(iter(valor)) if len(valor) == 1 else "NO_EVALUABLE"
            for clave, valor in evidencia.items()}


@dataclass
class Persistencia:
    segundos: float = 2.0
    max_intervalo: float = .5

    def __post_init__(self):
        if (not math.isfinite(self.segundos) or self.segundos <= 0 or
                not math.isfinite(self.max_intervalo) or self.max_intervalo <= 0):
            raise ValueError("Los umbrales de persistencia deben ser positivos y finitos.")
        self.activos = {}
        self.eventos = []
        self.ultimo_tiempo = None

    def observar(self, tiempo, observaciones):
        if not math.isfinite(tiempo) or tiempo < 0 or (self.ultimo_tiempo is not None and tiempo <= self.ultimo_tiempo):
            raise ValueError("Los tiempos deben ser finitos, positivos y crecientes.")
        self.ultimo_tiempo = tiempo
        for clave in list(self.activos):
            if observaciones.get(clave) != "INCUMPLIMIENTO" or tiempo - self.activos[clave]["ultimo"] > self.max_intervalo:
                del self.activos[clave]
        nuevos = []
        for clave, estado in observaciones.items():
            if estado != "INCUMPLIMIENTO":
                continue
            episodio = self.activos.setdefault(clave, {"inicio": tiempo, "ultimo": tiempo, "evento": None})
            episodio["ultimo"] = tiempo
            if episodio["evento"] is not None:
                episodio["evento"]["fin"] = tiempo
            elif tiempo - episodio["inicio"] >= self.segundos:
                evento = {"track_id": clave[0], "equipo": clave[1], "inicio": episodio["inicio"],
                          "fin": tiempo, "detectado_en": tiempo, "revision": "PENDIENTE"}
                episodio["evento"] = evento
                self.eventos.append(evento)
                nuevos.append(evento)
        return nuevos
