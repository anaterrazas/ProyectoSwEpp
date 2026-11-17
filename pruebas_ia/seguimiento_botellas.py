
from pathlib import Path
import cv2
from ultralytics import YOLO

# ==========================================
# CONFIGURACION
# ==========================================

BASE_DIR = Path(__file__).resolve().parent.parent

VIDEO = BASE_DIR / "pruebas_ia" / "produccion.mp4"
MODELO = BASE_DIR / "yolo11n.pt"

CARPETA_SALIDA = (
    BASE_DIR / "pruebas_ia" / "seguimiento" / "conteo"
)

CARPETA_SALIDA.mkdir(parents=True, exist_ok=True)

SALIDA = CARPETA_SALIDA / "conteo_botellas.mp4"

# ==========================================
# VALIDACIONES
# ==========================================

if not VIDEO.exists():
    raise FileNotFoundError(f"No existe el video: {VIDEO}")

if not MODELO.exists():
    raise FileNotFoundError(f"No existe el modelo: {MODELO}")

# ==========================================
# CARGAR MODELO
# ==========================================

print("Cargando modelo YOLO11n...")

modelo = YOLO(str(MODELO))

# ==========================================
# INFORMACION DEL VIDEO
# ==========================================

captura = cv2.VideoCapture(str(VIDEO))

if not captura.isOpened():
    raise ValueError("No se pudo abrir el video.")

fps = captura.get(cv2.CAP_PROP_FPS)
ancho = int(captura.get(cv2.CAP_PROP_FRAME_WIDTH))
alto = int(captura.get(cv2.CAP_PROP_FRAME_HEIGHT))

captura.release()

if fps <= 0:
    fps = 25

if ancho <= 0 or alto <= 0:
    raise ValueError("Dimensiones del video invalidas.")

# Linea virtual
LINEA_X = ancho // 2

# ==========================================
# CREAR VIDEO DE SALIDA
# ==========================================

codec = cv2.VideoWriter_fourcc(*"mp4v")

writer = cv2.VideoWriter(
    str(SALIDA),
    codec,
    fps,
    (ancho, alto)
)

if not writer.isOpened():
    raise RuntimeError("No se pudo crear el video.")

# ==========================================
# VARIABLES DE SEGUIMIENTO
# ==========================================

posiciones_anteriores = {}

botellas_contadas = set()

total_botellas = 0
fotogramas = 0

print("Iniciando seguimiento de botellas...")
print("Direccion: DERECHA A IZQUIERDA")
print("Analizando video completo...")

# ==========================================
# SEGUIMIENTO CON BYTETRACK
# ==========================================

try:

    resultados = modelo.track(
        source=str(VIDEO),
        classes=[39],
        conf=0.30,
        imgsz=640,
        tracker="bytetrack.yaml",
        persist=True,
        stream=True,
        save=False,
        device="cpu",
        verbose=False
    )

    for resultado in resultados:

        imagen = resultado.plot()

        cajas = resultado.boxes

        if cajas is not None and cajas.id is not None:

            coordenadas = cajas.xyxy.cpu().numpy()
            identificadores = cajas.id.cpu().numpy()

            for caja, identificador in zip(
                coordenadas,
                identificadores
            ):

                id_botella = int(identificador)

                x1, y1, x2, y2 = map(int, caja)

                centro_x = (x1 + x2) // 2

                posicion_anterior = posiciones_anteriores.get(
                    id_botella
                )

                # ==================================
                # PRIMER FOTOGRAMA
                # Contar todas las botellas visibles
                # ==================================

                if fotogramas == 0:

                    if id_botella not in botellas_contadas:

                        total_botellas += 1

                        botellas_contadas.add(id_botella)

                        print(
                            f"Botella inicial ID {id_botella} "
                            f"| Total: {total_botellas}"
                        )

                # ==================================
                # NUEVOS CRUCES
                # Derecha hacia izquierda
                # ==================================

                elif posicion_anterior is not None:

                    if (
                        posicion_anterior > LINEA_X
                        and centro_x <= LINEA_X
                        and id_botella not in botellas_contadas
                    ):

                        total_botellas += 1

                        botellas_contadas.add(id_botella)

                        print(
                            f"Botella contabilizada ID {id_botella} "
                            f"| Total: {total_botellas}"
                        )

                # Actualizar posicion
                posiciones_anteriores[id_botella] = centro_x

        # ======================================
        # DIBUJAR LINEA VIRTUAL
        # ======================================

        cv2.line(
            imagen,
            (LINEA_X, 0),
            (LINEA_X, alto),
            (0, 255, 255),
            3
        )

        cv2.putText(
            imagen,
            "LINEA DE CONTEO",
            (LINEA_X + 10, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 255),
            2
        )

        # ======================================
        # MOSTRAR CONTADOR
        # ======================================

        cv2.rectangle(
            imagen,
            (15, 15),
            (390, 105),
            (0, 0, 0),
            -1
        )

        cv2.putText(
            imagen,
            f"BOTELLAS CONTADAS: {total_botellas}",
            (30, 55),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.85,
            (0, 255, 0),
            2
        )

        cv2.putText(
            imagen,
            "Direccion: DERECHA -> IZQUIERDA",
            (30, 85),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            1
        )

        # Guardar fotograma
        writer.write(imagen)

        fotogramas += 1

        if fotogramas % 50 == 0:

            print(
                f"Fotogramas: {fotogramas} "
                f"| Botellas: {total_botellas}"
            )

finally:
    writer.release()

# ==========================================
# RESULTADO FINAL
# ==========================================

print("\n================================")
print("ANALISIS FINALIZADO")
print("================================")

print(f"Fotogramas procesados: {fotogramas}")
print(f"Botellas contabilizadas: {total_botellas}")

print(f"Video guardado en: {SALIDA}")

print("================================")
