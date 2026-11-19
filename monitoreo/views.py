
from pathlib import Path
import subprocess
import json
import uuid
import hashlib
import math
from collections import Counter

import cv2
import imageio_ffmpeg

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render, redirect, get_object_or_404

from ultralytics import YOLO
from administracion.models import Camara
from seguridad.models import DeteccionEPP
from seguridad.piloto import equipos_piloto, estados, Persistencia

BASE_DIR = Path(__file__).resolve().parent.parent


@login_required(login_url="/admin/login/")
def lista_camaras(request):
    camaras = Camara.objects.filter(
        activa=True
    ).select_related("area")

    for camara in camaras:
        carpeta = Path(settings.MEDIA_ROOT) / "resultados_ia" / f"camara_{camara.pk}"
        reportes = []
        if carpeta.is_dir():
            for ruta in carpeta.glob("*/reporte.json"):
                try:
                    ejecucion = uuid.UUID(ruta.parent.name)
                except ValueError:
                    continue
                reportes.append((ruta.stat().st_mtime, str(ejecucion)))
        camara.reportes_piloto = [ejecucion for _, ejecucion in sorted(reportes, reverse=True)[:10]]

    return render(
        request,
        "monitoreo/camaras.html",
        {"camaras": camaras}
    )


@login_required(login_url="/admin/login/")
@permission_required("seguridad.add_deteccionepp", raise_exception=True)
def analizar_camara(request, camara_id):

    if request.method != "POST":
        return redirect("lista_camaras")

    camara = get_object_or_404(
        Camara,
        id=camara_id,
        activa=True
    )

    if camara.tipo_monitoreo != "EPP" or camara.tipo_fuente != "VIDEO":
        messages.error(request, "Este piloto requiere una cámara EPP con archivo de video.")
        return redirect("lista_camaras")

    try:
        obligatorios = equipos_piloto(camara.area.equipos_obligatorios.values_list("nombre", flat=True))
    except ValueError as error:
        messages.error(request, str(error))
        return redirect("lista_camaras")

    if not camara.archivo_video:
        messages.error(request, "La cámara no tiene video.")
        return redirect("lista_camaras")

    ruta_modelo = BASE_DIR / "Modelos" / "best.pt"

    if not ruta_modelo.exists() or not (BASE_DIR / "yolo11n.pt").exists():
        messages.error(request, "No se encontró el modelo de IA.")
        return redirect("lista_camaras")

    proceso = None
    resultados = None

    try:
        print("Iniciando análisis con YOLO...")

        modelo = YOLO(str(ruta_modelo))
        modelo_personas = YOLO(str(BASE_DIR / "yolo11n.pt"))
        persistencia = Persistencia()
        cobertura = Counter()
        ejecucion = uuid.uuid4().hex

        carpeta_salida = (
            Path(settings.MEDIA_ROOT)
            / "resultados_ia"
            / f"camara_{camara.id}"
            / ejecucion
        )

        carpeta_salida.mkdir(
            parents=True,
            exist_ok=True
        )

        video_salida = carpeta_salida / "resultado_epp.mp4"

        # Obtener características del video original
        captura = cv2.VideoCapture(camara.archivo_video.path)

        if not captura.isOpened():
            raise ValueError("No se pudo abrir el video original.")

        fps = captura.get(cv2.CAP_PROP_FPS)
        ancho = int(captura.get(cv2.CAP_PROP_FRAME_WIDTH))
        alto = int(captura.get(cv2.CAP_PROP_FRAME_HEIGHT))

        captura.release()

        if not math.isfinite(fps) or fps <= 0:
            fps = 25

        if ancho <= 0 or alto <= 0:
            raise ValueError("El video tiene dimensiones inválidas.")

        # H.264 utiliza dimensiones pares
        ancho -= ancho % 2
        alto -= alto % 2

        # Crear MP4 directamente con FFmpeg
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
            str(video_salida)
        ]

        proceso = subprocess.Popen(
            comando,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        resultados = modelo.predict(
            source=camara.archivo_video.path,
            conf=0.30,
            imgsz=640,
            stream=True,
            save=False,
            device="cpu",
            verbose=False
        )

        fotogramas = 0
        detecciones_guardadas = 0
        ultimo_segundo = -1

        # Cada ejecución conserva su evidencia y sus IDs temporales.
        for resultado in resultados:

            # Calcular el segundo actual del video
            segundo_actual = int(fotogramas / fps)

            # Guardar detecciones una vez por segundo
            if segundo_actual != ultimo_segundo:

                detecciones = []

                for caja in resultado.boxes:
                    clase = int(caja.cls[0])
                    confianza = float(caja.conf[0])
                    tipo = modelo.names[clase]

                    # Tipos permitidos en nuestro modelo
                    if tipo in [
                        "Person",
                        "Hardhat",
                        "NO-Hardhat",
                        "Safety Vest",
                        "NO-Safety Vest",
                        "Gloves",
                        "NO-Gloves",
                        "Goggles",
                        "NO-Goggles",
                        "Mask",
                        "NO-Mask",
                    ]:
                        detecciones.append(
                            DeteccionEPP(
                                camara=camara,
                                tipo=tipo,
                                confianza=confianza,
                                segundo_video=segundo_actual
                            )
                        )

                if detecciones:
                    DeteccionEPP.objects.bulk_create(
                        detecciones
                    )

                    detecciones_guardadas += len(detecciones)

                ultimo_segundo = segundo_actual

            # Ausencia de detección nunca prueba ausencia de EPP.
            personas_resultado = modelo_personas.track(
                resultado.orig_img, classes=[0], conf=.30, tracker="bytetrack.yaml",
                persist=True, device="cpu", verbose=False,
            )[0]
            personas = {}
            if personas_resultado.boxes is not None and personas_resultado.boxes.id is not None:
                for caja in personas_resultado.boxes:
                    personas[int(caja.id.item())] = caja.xyxy[0].tolist()
            observaciones = estados(personas, [
                (modelo.names[int(caja.cls[0])], float(caja.conf[0]), caja.xyxy[0].tolist())
                for caja in resultado.boxes
            ], obligatorios)
            cobertura.update(observaciones.values())
            nuevos = persistencia.observar(fotogramas / fps, observaciones)
            imagen = resultado.plot()
            for track, (x1, y1, x2, y2) in personas.items():
                cv2.rectangle(imagen, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 255), 2)
                texto = f"ID {track}: " + ", ".join(
                    f"{e}: {observaciones[track, e]}" for e in obligatorios)
                cv2.putText(imagen, texto, (max(0, int(x1)), max(20, int(y1))),
                            cv2.FONT_HERSHEY_SIMPLEX, .45, (0, 255, 255), 1)
            for evento in nuevos:
                nombre = f"evidencia_{len(persistencia.eventos)}_{evento['track_id']}_{evento['equipo']}.jpg"
                evidencia = carpeta_salida / nombre
                if not cv2.imwrite(str(evidencia), imagen):
                    raise ValueError("No se pudo guardar la evidencia del evento.")
                evento["evidencia"] = nombre
                evento["persona_xyxy"] = personas[evento["track_id"]]
                evento["evidencia_sha256"] = hashlib.sha256(evidencia.read_bytes()).hexdigest()

            imagen = cv2.resize(
                imagen,
                (ancho, alto)
            )

            proceso.stdin.write(imagen.tobytes())

            fotogramas += 1


        proceso.stdin.close()
        codigo_salida = proceso.wait()

        if codigo_salida != 0 or fotogramas == 0:
            raise ValueError(
                "No se pudo generar el video procesado."
            )

        print(f"Fotogramas procesados: {fotogramas}")
        print(f"Detecciones guardadas: {detecciones_guardadas}")

        with open(camara.archivo_video.path, "rb") as fuente:
            video_hash = hashlib.file_digest(fuente, "sha256").hexdigest()
        reporte = {
            "version": 1, "ejecucion": ejecucion, "camara_id": camara.id,
            "modo": "PRUEBA_VIDEO", "validado_en_planta": False,
            "area": camara.area.nombre, "obligatorios": obligatorios,
            "video_sha256": video_hash, "fotogramas": fotogramas,
            "observaciones_por_estado": dict(cobertura), "eventos": persistencia.eventos,
            "umbral_segundos": persistencia.segundos,
            "nota": "Prueba con video de referencia, sin validación en planta. Candidatos de revisión humana. IDs temporales; no identifican trabajadores. Las observaciones repetidas no son personas únicas.",
        }
        for clave, ruta in (("epp", ruta_modelo), ("personas", BASE_DIR / "yolo11n.pt")):
            with ruta.open("rb") as pesos:
                reporte[f"modelo_{clave}_sha256"] = hashlib.file_digest(pesos, "sha256").hexdigest()
        (carpeta_salida / "reporte.json").write_text(
            json.dumps(reporte, ensure_ascii=False, indent=2), encoding="utf-8")
        request.session[f"piloto_{camara.id}"] = str(uuid.UUID(ejecucion))

        # Dirección del video para Django
        url_video = (
            settings.MEDIA_URL.rstrip("/")
            + f"/resultados_ia/camara_{camara.id}/{ejecucion}/resultado_epp.mp4"
        )

        request.session[f"resultado_{camara.id}"] = (
            url_video
        )

        messages.success(
            request,
             f"Video procesado correctamente. "
             f"Se registraron {detecciones_guardadas} detecciones."
        )

    except Exception as error:

        print("Error durante el análisis:", error)

        if proceso is not None:
            if proceso.stdin and not proceso.stdin.closed:
                proceso.stdin.close()
            if proceso.poll() is None:
                proceso.kill()
                proceso.wait()

        messages.error(
            request,
            f"No se pudo procesar el video: {error}"
        )

    finally:
        if resultados is not None and hasattr(resultados, "close"):
            resultados.close()

    return redirect("lista_camaras")
