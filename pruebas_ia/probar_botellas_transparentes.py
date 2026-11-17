from pathlib import Path
import cv2
import subprocess
import imageio_ffmpeg

from ultralytics import YOLO

# RUTAS
BASE_DIR = Path(__file__).resolve().parent.parent

VIDEO = BASE_DIR / "pruebas_ia" / "produccion_prueba_02.mp4"
MODELO = BASE_DIR / "yolo11n.pt"

CARPETA_SALIDA = BASE_DIR / "pruebas_ia" / "resultados_preformas"

# CONFIGURACION
CLASE_BOTELLA = 39
CONFIANZA = 0.20
TAMANO_IMAGEN = 960

# VALIDACIONES
if not VIDEO.exists():
    raise FileNotFoundError(f"No existe el video: {VIDEO}")

if not MODELO.exists():
    raise FileNotFoundError(f"No existe el modelo: {MODELO}")

# CARGAR MODELO
print("Cargando YOLO11n...")
modelo = YOLO(str(MODELO))

# =====================================================
# INFORMACION DEL VIDEO Y CREACION DEL ESCRITOR
# =====================================================

captura = cv2.VideoCapture(str(VIDEO))

if not captura.isOpened():
    raise ValueError("No se pudo abrir el video.")

fps = captura.get(cv2.CAP_PROP_FPS)
ancho = int(captura.get(cv2.CAP_PROP_FRAME_WIDTH))
alto = int(captura.get(cv2.CAP_PROP_FRAME_HEIGHT))
total_fotogramas = int(captura.get(cv2.CAP_PROP_FRAME_COUNT))

captura.release()

if fps <= 0:
    fps = 25

if ancho <= 0 or alto <= 0:
    raise ValueError("Dimensiones de video invalidas.")

# Ajustar dimensiones para compatibilidad con H.264
ancho_salida = ancho - (ancho % 2)
alto_salida = alto - (alto % 2)

# Crear carpeta de resultados
CARPETA_SALIDA.mkdir(parents=True, exist_ok=True)

VIDEO_TEMPORAL = CARPETA_SALIDA / "deteccion_preformas_temporal.mp4"
VIDEO_FINAL = CARPETA_SALIDA / "deteccion_preformas.mp4"

# Crear escritor de video
writer = cv2.VideoWriter(
    str(VIDEO_TEMPORAL),
    cv2.VideoWriter_fourcc(*"mp4v"),
    fps,
    (ancho_salida, alto_salida),
)

if not writer.isOpened():
    raise RuntimeError("No se pudo crear el video temporal.")

print("Iniciando prueba de deteccion de preformas PET...")
print(f"Resolucion original: {ancho}x{alto}")
print(f"Fotogramas del video: {total_fotogramas}")
print("Modelo: YOLO11n")
print("Clase: bottle (39)")

fotogramas = 0
fotogramas_con_deteccion = 0
maximo_detecciones = 0
ids_observados = set()
confianzas = []

try:
    resultados = modelo.track(
        source=str(VIDEO),
        classes=[CLASE_BOTELLA],
        conf=CONFIANZA,
        imgsz=TAMANO_IMAGEN,
        tracker="bytetrack.yaml",
        persist=True,
        stream=True,
        save=False,
        device="cpu",
        verbose=False,
    )

    for resultado in resultados:
        imagen = resultado.plot()
        cajas = resultado.boxes

        cantidad = 0

        if cajas is not None and len(cajas) > 0:
            cantidad = len(cajas)

            if cajas.id is not None:
                identificadores = cajas.id.cpu().numpy()
                for identificador in identificadores:
                    ids_observados.add(int(identificador))

            if cajas.conf is not None:
                confianzas.extend(cajas.conf.cpu().numpy().tolist())

        if cantidad > 0:
            fotogramas_con_deteccion += 1

        maximo_detecciones = max(maximo_detecciones, cantidad)

        cv2.rectangle(imagen, (15, 15), (650, 105), (0, 0, 0), -1)

        cv2.putText(
            imagen,
            f"DETECCIONES: {cantidad}",
            (30, 55),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (0, 255, 0),
            2,
        )

        cv2.putText(
            imagen,
            f"IDs observados: {len(ids_observados)}",
            (30, 88),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.75,
            (255, 255, 255),
            2,
        )

        imagen = cv2.resize(imagen, (ancho_salida, alto_salida))

        writer.write(imagen)
        fotogramas += 1

        if fotogramas % 100 == 0:
            print(
                f"Fotogramas: {fotogramas} | "
                f"Detecciones actuales: {cantidad} | "
                f"IDs observados: {len(ids_observados)}"
            )

finally:
    writer.release()


# =====================================================
# CONVERSION A H.264
# =====================================================

if not VIDEO_TEMPORAL.exists() or VIDEO_TEMPORAL.stat().st_size == 0:
    raise RuntimeError("No se genero el video temporal.")

print("Convirtiendo resultado a MP4 H.264...")

comando = [
    imageio_ffmpeg.get_ffmpeg_exe(),
    "-y",
    "-i",
    str(VIDEO_TEMPORAL),
    "-c:v",
    "libx264",
    "-preset",
    "fast",
    "-crf",
    "23",
    "-pix_fmt",
    "yuv420p",
    "-movflags",
    "+faststart",
    "-an",
    str(VIDEO_FINAL),
]

conversion = subprocess.run(comando, capture_output=True, text=True)

if conversion.returncode != 0:
    raise RuntimeError("Fallo la conversion H.264:\n" + conversion.stderr[-2500:])

VIDEO_TEMPORAL.unlink(missing_ok=True)


# =====================================================
# RESUMEN
# =====================================================

promedio_confianza = sum(confianzas) / len(confianzas) if confianzas else 0

print("\n======================================")
print("PRUEBA DE DETECCION FINALIZADA")
print("======================================")
print(f"Fotogramas procesados: {fotogramas}")
print(f"Fotogramas con detecciones: {fotogramas_con_deteccion}")
print(f"Maximo de detecciones en un fotograma: {maximo_detecciones}")
print(f"IDs distintos observados: {len(ids_observados)}")
print(f"Confianza promedio: {promedio_confianza:.3f}")
print(f"Video generado: {VIDEO_FINAL}")
print("======================================")
print(
    "IMPORTANTE: los IDs observados no representan necesariamente "
    "el numero real de preformas. El modelo COCO no fue entrenado "
    "especificamente para detectar preformas PET."
)
