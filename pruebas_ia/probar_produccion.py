
from pathlib import Path
import cv2
from ultralytics import YOLO

BASE_DIR = Path(__file__).resolve().parent.parent

VIDEO = BASE_DIR / "pruebas_ia" / "produccion.mp4"
SALIDA = BASE_DIR / "pruebas_ia" / "deteccion_produccion.avi"

if not VIDEO.exists():
    raise FileNotFoundError("No se encontro produccion.mp4")

modelo = YOLO(str(BASE_DIR / "yolo11n.pt"))

captura = cv2.VideoCapture(str(VIDEO))

if not captura.isOpened():
    raise ValueError("No se pudo abrir el video")

fps = captura.get(cv2.CAP_PROP_FPS)
ancho = int(captura.get(cv2.CAP_PROP_FRAME_WIDTH))
alto = int(captura.get(cv2.CAP_PROP_FRAME_HEIGHT))

if fps <= 0:
    fps = 25

salida = cv2.VideoWriter(
    str(SALIDA),
    cv2.VideoWriter_fourcc(*"MJPG"),
    fps,
    (ancho, alto)
)

if not salida.isOpened():
    captura.release()
    raise RuntimeError("No se pudo crear el video de salida")

fotogramas = 0
maximo_botellas = 0

print("Analizando video de produccion...")

try:
    while True:
        correcto, imagen = captura.read()

        if not correcto:
            break

        resultado = modelo.predict(
            imagen,
            classes=[39],
            conf=0.25,
            verbose=False
        )[0]

        cantidad = len(resultado.boxes)
        maximo_botellas = max(maximo_botellas, cantidad)

        imagen_procesada = resultado.plot()

        salida.write(imagen_procesada)

        fotogramas += 1

finally:
    captura.release()
    salida.release()

print("Analisis finalizado.")
print(f"Fotogramas procesados: {fotogramas}")
print(
    f"Maximo de botellas detectadas "
    f"en un fotograma: {maximo_botellas}"
)
print(f"Video guardado en: {SALIDA}")
