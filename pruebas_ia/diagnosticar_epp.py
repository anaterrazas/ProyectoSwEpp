
from pathlib import Path
import cv2
from ultralytics import YOLO

print("INICIANDO DIAGNÓSTICO EPP")
BASE_DIR = Path(__file__).resolve().parent.parent

video = BASE_DIR / "pruebas_ia" / "trabajadores.mp4"

modelo_personas = YOLO(str(BASE_DIR / "yolo11n.pt"))
modelo_epp = YOLO(str(BASE_DIR / "modelos" / "best.pt"))

captura = cv2.VideoCapture(str(video))
captura.set(cv2.CAP_PROP_POS_FRAMES, 50)

ok, imagen = captura.read()
captura.release()

if not ok:
    raise ValueError("No se pudo leer el fotograma")

personas = modelo_personas.predict(
    imagen,
    classes=[0],
    conf=0.25,
    verbose=False
)[0]

equipos = modelo_epp.predict(
    imagen,
    conf=0.20,
    verbose=False
)[0]

print("\nPERSONAS DETECTADAS:")

for indice, caja in enumerate(personas.boxes):
    x1, y1, x2, y2 = map(int, caja.xyxy[0])

    cv2.rectangle(
        imagen, (x1, y1), (x2, y2),
        (255, 0, 0), 2
    )

    cv2.putText(
        imagen, f"Persona {indice + 1}",
        (x1, max(20, y1 + 25)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6, (255, 0, 0), 2
    )

    print(f"Persona {indice + 1}: {[x1, y1, x2, y2]}")

print("\nEPP DETECTADOS:")

for caja in equipos.boxes:
    clase = int(caja.cls[0])
    nombre = modelo_epp.names[clase]
    confianza = float(caja.conf[0])

    if nombre not in ["Hardhat", "Safety Vest"]:
        continue

    x1, y1, x2, y2 = map(int, caja.xyxy[0])

    cv2.rectangle(
        imagen, (x1, y1), (x2, y2),
        (0, 255, 0), 2
    )

    cv2.putText(
        imagen,
        f"{nombre} {confianza:.2f}",
        (x1, max(20, y1 - 8)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5, (0, 255, 0), 2
    )

    print(f"{nombre}: {confianza:.2%}")

salida = BASE_DIR / "pruebas_ia" / "diagnostico_epp.jpg"

cv2.imwrite(str(salida), imagen)

print("\nDiagnóstico generado correctamente.")

