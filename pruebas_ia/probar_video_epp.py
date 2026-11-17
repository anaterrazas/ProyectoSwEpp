
from pathlib import Path
from ultralytics import YOLO

BASE_DIR = Path(__file__).resolve().parent.parent

ruta_modelo = BASE_DIR / "modelos" / "best.pt"
ruta_video = BASE_DIR / "pruebas_ia" / "trabajadores.mp4"
ruta_resultados = BASE_DIR / "pruebas_ia" / "resultados_video"

if not ruta_modelo.exists():
    raise FileNotFoundError("No se encontró el modelo best.pt")

if not ruta_video.exists():
    raise FileNotFoundError("No se encontró trabajadores.mp4")

print("Cargando modelo EPP...")

modelo = YOLO(str(ruta_modelo))

print("Analizando video...")


resultados = modelo.predict(
    source=str(ruta_video),
    conf=0.30,
    imgsz=640,
    save=True,
    stream=True,
    project=str(ruta_resultados),
    name="detecciones",
    exist_ok=True,
    device="cpu",
    verbose=False
)

for resultado in resultados:
    pass


print("Video procesado correctamente.")
print("Resultado guardado en:")
print(ruta_resultados / "detecciones")
