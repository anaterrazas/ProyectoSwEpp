
from pathlib import Path
from ultralytics import YOLO

BASE_DIR = Path(__file__).resolve().parent.parent

ruta_video = BASE_DIR / "pruebas_ia" / "trabajadores.mp4"

if not ruta_video.exists():
    raise FileNotFoundError(
        "No se encontró el video trabajadores.mp4"
    )

# Modelo general de YOLO
modelo = YOLO("yolo11n.pt")

print("Analizando personas en el video...")

resultados = modelo.predict(
    source=str(ruta_video),
    classes=[0],
    conf=0.25,
    imgsz=640,
    stream=True,
    save=True,
    project=str(BASE_DIR / "pruebas_ia" / "resultados_personas"),
    name="detecciones",
    exist_ok=True,
    device="cpu",
    verbose=False
)

fotogramas = 0
fotogramas_con_personas = 0
maximo_personas = 0

for resultado in resultados:
    cantidad = len(resultado.boxes)
    fotogramas += 1

    if cantidad > 0:
        fotogramas_con_personas += 1

    maximo_personas = max(maximo_personas, cantidad)

print("Análisis finalizado.")
print(f"Fotogramas procesados: {fotogramas}")
print(f"Fotogramas con personas: {fotogramas_con_personas}")
print(f"Máximo de personas detectadas en un fotograma: {maximo_personas}")
