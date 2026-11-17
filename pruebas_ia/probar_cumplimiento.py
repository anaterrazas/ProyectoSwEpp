
from pathlib import Path

import cv2
from ultralytics import YOLO


BASE_DIR = Path(__file__).resolve().parent.parent

ruta_video = BASE_DIR / "pruebas_ia" / "trabajadores.mp4"
ruta_epp = BASE_DIR / "modelos" / "best.pt"
ruta_personas = BASE_DIR / "yolo11n.pt"

if not ruta_video.exists():
    raise FileNotFoundError("No se encontró trabajadores.mp4")

if not ruta_epp.exists():
    raise FileNotFoundError("No se encontró modelos/best.pt")

modelo_personas = YOLO(str(ruta_personas))
modelo_epp = YOLO(str(ruta_epp))

captura = cv2.VideoCapture(str(ruta_video))

if not captura.isOpened():
    raise ValueError("No se pudo abrir el video")

# Analizar el fotograma 50
captura.set(cv2.CAP_PROP_POS_FRAMES, 50)

correcto, imagen = captura.read()
captura.release()

if not correcto:
    raise ValueError("No se pudo leer el fotograma")

# Detectar personas
resultado_personas = modelo_personas.predict(
    imagen,
    classes=[0],
    conf=0.25,
    verbose=False
)[0]

# Detectar equipos de protección
resultado_epp = modelo_epp.predict(
    imagen,
    conf=0.30,
    verbose=False
)[0]


def calcular_asociacion(caja_epp, caja_persona, tipo):
    x1, y1, x2, y2 = caja_epp
    px1, py1, px2, py2 = caja_persona

    ancho = px2 - px1
    alto = py2 - py1

    if ancho <= 0 or alto <= 0:
        return None

    centro_x = (x1 + x2) / 2
    centro_y = (y1 + y2) / 2

    if tipo == "Hardhat":
        limite_y = py1 + alto * 0.35

    elif tipo == "Safety Vest":
        limite_y = py1 + alto * 0.70

    else:
        return None

    # Verificar que el EPP se encuentre en la
    # región aproximada del cuerpo
    if not (
        px1 <= centro_x <= px2
        and py1 <= centro_y <= limite_y
    ):
        return None

    # Calcular distancia horizontal normalizada
    centro_persona = (px1 + px2) / 2

    distancia = abs(
        centro_x - centro_persona
    ) / ancho

    return distancia


# Almacenar personas detectadas
personas = []

for caja in resultado_personas.boxes:
    coordenadas = caja.xyxy[0].tolist()

    personas.append({
        "caja": coordenadas,
        "casco": False,
        "chaleco": False,
    })


# Asociar EPP con personas
for caja in resultado_epp.boxes:

    clase = int(caja.cls[0])
    nombre = modelo_epp.names[clase]
    coordenadas = caja.xyxy[0].tolist()

    if nombre not in ["Hardhat", "Safety Vest"]:
        continue

    candidatos = []

    for indice, persona in enumerate(personas):

        distancia = calcular_asociacion(
            coordenadas,
            persona["caja"],
            nombre
        )

        if distancia is not None:
            candidatos.append(
                (distancia, indice)
            )

    candidatos.sort()

    if candidatos:

        mejor_distancia, mejor_indice = candidatos[0]

        asignacion_valida = (
            len(candidatos) == 1
            or candidatos[1][0] - mejor_distancia > 0.15
        )

        if asignacion_valida:

            persona = personas[mejor_indice]

            if nombre == "Hardhat":
                persona["casco"] = True

            elif nombre == "Safety Vest":
                persona["chaleco"] = True


# Evaluar los resultados
print("\nRESULTADOS DE CUMPLIMIENTO:")

for indice, persona in enumerate(personas):

    x1, y1, x2, y2 = map(
        int,
        persona["caja"]
    )

    casco = persona["casco"]
    chaleco = persona["chaleco"]

    if casco and chaleco:
        estado = "EPP detectado"
        color = (0, 180, 0)

    else:
        estado = "Revision pendiente"
        color = (0, 165, 255)

    cv2.rectangle(
        imagen,
        (x1, y1),
        (x2, y2),
        color,
        2
    )

    cv2.putText(
        imagen,
        f"Persona {indice + 1}: {estado}",
        (x1, max(y1 - 10, 20)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        color,
        2
    )

    print(
        f"Persona {indice + 1}: "
        f"Casco={casco}, "
        f"Chaleco={chaleco}, "
        f"Estado={estado}"
    )


salida = (
    BASE_DIR
    / "pruebas_ia"
    / "resultado_cumplimiento.jpg"
)

cv2.imwrite(str(salida), imagen)

print(f"\nResultado guardado en: {salida}")
