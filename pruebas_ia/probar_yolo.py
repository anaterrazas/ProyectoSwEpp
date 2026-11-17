
from ultralytics import YOLO
from pathlib import Path

# Carpeta donde se guardarán los resultados
carpeta_resultados = Path("pruebas_ia/resultados")
carpeta_resultados.mkdir(parents=True, exist_ok=True)

# Cargar modelo YOLO preentrenado
modelo = YOLO("yolo11n.pt")

# Analizar una imagen de prueba
resultados = modelo.predict(
    source="https://ultralytics.com/images/bus.jpg",
    conf=0.25,
    save=True,
    project=str(carpeta_resultados),
    name="primera_prueba",
    exist_ok=True,
    device="cpu"
)

# Mostrar objetos detectados
for resultado in resultados:
    for caja in resultado.boxes:
        clase = int(caja.cls[0])
        confianza = float(caja.conf[0])

        nombre = modelo.names[clase]

        print(f"Detectado: {nombre} | Confianza: {confianza:.2f}")

print("Prueba finalizada correctamente.")
