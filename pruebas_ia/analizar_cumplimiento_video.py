
from pathlib import Path
import subprocess
from collections import defaultdict

import cv2
import imageio_ffmpeg
from ultralytics import YOLO


BASE_DIR = Path(__file__).resolve().parent.parent

VIDEO = BASE_DIR / "pruebas_ia" / "trabajador_prueba.mp4"
MODELO_PERSONAS = BASE_DIR / "yolo11n.pt"
MODELO_EPP = BASE_DIR / "modelos" / "best.pt"

SALIDA = BASE_DIR / "pruebas_ia" / "cumplimiento_video.mp4"

# Verificar archivos
for archivo in [VIDEO, MODELO_PERSONAS, MODELO_EPP]:
    if not archivo.exists():
        raise FileNotFoundError(f"No existe: {archivo}")

print("Cargando modelos de IA...")

modelo_personas = YOLO(str(MODELO_PERSONAS))
modelo_epp = YOLO(str(MODELO_EPP))

captura = cv2.VideoCapture(str(VIDEO))

if not captura.isOpened():
    raise ValueError("No se pudo abrir el video.")

fps = captura.get(cv2.CAP_PROP_FPS)
ancho = int(captura.get(cv2.CAP_PROP_FRAME_WIDTH))
alto = int(captura.get(cv2.CAP_PROP_FRAME_HEIGHT))

if fps <= 0:
    fps = 25

if ancho <= 0 or alto <= 0:
    captura.release()
    raise ValueError("Dimensiones de video inválidas.")

# H.264 necesita dimensiones pares
ancho -= ancho % 2
alto -= alto % 2

# Crear video MP4 compatible
comando = [
    imageio_ffmpeg.get_ffmpeg_exe(),
    "-y",
    "-f", "rawvideo",
    "-vcodec", "rawvideo",
    "-s", f"{ancho}x{alto}",
    "-pix_fmt", "bgr24",
    "-r", str(fps),
    "-i", "-",
    "-an",
    "-c:v", "libx264",
    "-preset", "ultrafast",
    "-pix_fmt", "yuv420p",
    "-movflags", "+faststart",
    str(SALIDA)
]


def asociar_equipo(caja_equipo, personas, tipo):
    """Asocia el EPP solo si hay un candidato claro."""

    x1, y1, x2, y2 = caja_equipo

    cx = (x1 + x2) / 2
    cy = (y1 + y2) / 2

    candidatos = []

    for identificador, persona in personas.items():

        px1, py1, px2, py2 = persona["caja"]

        ancho_persona = px2 - px1
        alto_persona = py2 - py1

        if ancho_persona <= 0 or alto_persona <= 0:
            continue

        if tipo == "Hardhat":
            limite = py1 + alto_persona * 0.35
        elif tipo == "Safety Vest":
            limite = py1 + alto_persona * 0.70
        else:
            continue

        if not (
            px1 <= cx <= px2
            and py1 <= cy <= limite
        ):
            continue

        centro_persona = (px1 + px2) / 2

        distancia = abs(
            cx - centro_persona
        ) / ancho_persona

        candidatos.append(
            (distancia, identificador)
        )

    candidatos.sort()

    if not candidatos:
        return None

    if len(candidatos) > 1:
        diferencia = candidatos[1][0] - candidatos[0][0]

        if diferencia <= 0.15:
            return None

    return candidatos[0][1]


# Estadísticas por identificador temporal
estadisticas = defaultdict(
    lambda: {
        "observaciones": 0,
        "casco": 0,
        "chaleco": 0,
        "ambos": 0
    }
)

proceso = None
fotogramas = 0

try:
    proceso = subprocess.Popen(
        comando,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    print("Analizando video completo...")

    while True:
        correcto, imagen = captura.read()

        if not correcto:
            break

        imagen = cv2.resize(imagen, (ancho, alto))

        # Detectar y seguir personas
        resultado_personas = modelo_personas.track(
            imagen,
            classes=[0],
            conf=0.25,
            persist=True,
            tracker="bytetrack.yaml",
            verbose=False
        )[0]

        # Detectar equipos de protección
        resultado_epp = modelo_epp.predict(
            imagen,
            conf=0.30,
            verbose=False
        )[0]

        personas = {}

        if (
            resultado_personas.boxes is not None
            and resultado_personas.boxes.id is not None
        ):
            for caja in resultado_personas.boxes:

                identificador = int(caja.id.item())

                personas[identificador] = {
                    "caja": caja.xyxy[0].tolist(),
                    "casco": False,
                    "chaleco": False
                }

        # Asociar cascos y chalecos
        for caja in resultado_epp.boxes:

            clase = int(caja.cls[0])
            tipo = modelo_epp.names[clase]

            if tipo not in ["Hardhat", "Safety Vest"]:
                continue

            identificador = asociar_equipo(
                caja.xyxy[0].tolist(),
                personas,
                tipo
            )

            if identificador is not None:

                if tipo == "Hardhat":
                    personas[identificador]["casco"] = True

                elif tipo == "Safety Vest":
                    personas[identificador]["chaleco"] = True

        # Dibujar resultados y registrar estadísticas
        for identificador, persona in personas.items():

            casco = persona["casco"]
            chaleco = persona["chaleco"]

            datos = estadisticas[identificador]
            datos["observaciones"] += 1
            datos["casco"] += int(casco)
            datos["chaleco"] += int(chaleco)
            datos["ambos"] += int(casco and chaleco)

            if casco and chaleco:
                estado = "EPP detectado"
                color = (0, 180, 0)

            elif casco or chaleco:
                estado = "Revision pendiente"
                color = (0, 165, 255)

            else:
                estado = "No evaluable"
                color = (150, 150, 150)

            x1, y1, x2, y2 = map(
                int,
                persona["caja"]
            )

            cv2.rectangle(
                imagen,
                (x1, y1),
                (x2, y2),
                color,
                2
            )

            texto = f"ID {identificador}: {estado}"

            cv2.putText(
                imagen,
                texto,
                (x1, max(y1 - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                color,
                2
            )

        # Enviar fotograma a FFmpeg
        proceso.stdin.write(imagen.tobytes())
        fotogramas += 1

    proceso.stdin.close()
    codigo = proceso.wait()

    if codigo != 0 or fotogramas == 0:
        raise RuntimeError("No se pudo generar el video MP4.")

finally:
    captura.release()

    if proceso is not None:
        if proceso.stdin and not proceso.stdin.closed:
            proceso.stdin.close()

        if proceso.poll() is None:
            proceso.kill()
            proceso.wait()


print("\nANÁLISIS FINALIZADO")
print(f"Fotogramas procesados: {fotogramas}")

print("\nRESUMEN DE OBSERVACIONES:")

for identificador, datos in sorted(estadisticas.items()):

    total = datos["observaciones"]

    if total == 0:
        continue

    porcentaje_casco = datos["casco"] / total * 100
    porcentaje_chaleco = datos["chaleco"] / total * 100
    porcentaje_ambos = datos["ambos"] / total * 100

    print(f"\nID temporal {identificador}")
    print(f"Fotogramas observado: {total}")
    print(f"Casco asociado: {porcentaje_casco:.1f}%")
    print(f"Chaleco asociado: {porcentaje_chaleco:.1f}%")
    print(f"Ambos asociados: {porcentaje_ambos:.1f}%")

print(f"\nVideo guardado en: {SALIDA}")
