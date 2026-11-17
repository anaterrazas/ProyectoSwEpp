
from pathlib import Path
from ultralytics import YOLO

# Carpeta principal del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent

# Rutas
ruta_modelo = BASE_DIR / "modelos" / "best.pt"
ruta_imagen = BASE_DIR / "pruebas_ia" / "trabajadores.jpg"
ruta_resultados = BASE_DIR / "pruebas_ia" / "resultados_epp"

# Verificar archivos
if not ruta_modelo.exists():
    raise FileNotFoundError("No se encontró modelos/best.pt")

if not ruta_imagen.exists():
    raise FileNotFoundError(
        "No se encontró pruebas_ia/trabajadores.jpg"
    )

# Cargar modelo de seguridad industrial
print("Cargando modelo de EPP...")
modelo = YOLO(str(ruta_modelo))

# Procesar imagen
print("Analizando trabajadores...")

resultados = modelo.predict(
    source=str(ruta_imagen),
    conf=0.20,
    save=True,
    project=str(ruta_resultados),
    name="detecciones",
    exist_ok=True,
    device="cpu"
)

# Mostrar detecciones
for resultado in resultados:
    print("\nRESULTADOS DE LA DETECCIÓN:")

    for caja in resultado.boxes:
        clase = int(caja.cls[0])
        confianza = float(caja.conf[0])
        nombre = modelo.names[clase]

        print(
            f"{nombre} - Confianza: {confianza:.2%}"
        )

print("\nAnálisis finalizado correctamente.")
print(f"Resultados guardados en: {ruta_resultados}")
