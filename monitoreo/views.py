
from pathlib import Path
import subprocess

import cv2
import imageio_ffmpeg

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

from ultralytics import YOLO
from administracion.models import Camara
from seguridad.models import DeteccionEPP

BASE_DIR = Path(__file__).resolve().parent.parent


@login_required(login_url="/admin/login/")
def lista_camaras(request):
    camaras = Camara.objects.filter(
        activa=True
    ).select_related("area")

    return render(
        request,
        "monitoreo/camaras.html",
        {"camaras": camaras}
    )


@login_required(login_url="/admin/login/")
def analizar_camara(request, camara_id):

    if request.method != "POST":
        return redirect("lista_camaras")

    camara = get_object_or_404(
        Camara,
        id=camara_id,
        activa=True
    )

    if not camara.archivo_video:
        messages.error(request, "La cámara no tiene video.")
        return redirect("lista_camaras")

    ruta_modelo = BASE_DIR / "modelos" / "best.pt"

    if not ruta_modelo.exists():
        messages.error(request, "No se encontró el modelo de IA.")
        return redirect("lista_camaras")

    proceso = None

    try:
        print("Iniciando análisis con YOLO...")

        modelo = YOLO(str(ruta_modelo))

        carpeta_salida = (
            Path(settings.MEDIA_ROOT)
            / "resultados_ia"
            / f"camara_{camara.id}"
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

        if fps <= 0:
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

        # Enviar fotogramas procesados a FFmpeg
        
        # Enviar fotogramas procesados a FFmpeg
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

            # Dibujar las detecciones sobre el video
            imagen = resultado.plot()

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

        # Dirección del video para Django
        url_video = (
            settings.MEDIA_URL.rstrip("/")
            + f"/resultados_ia/camara_{camara.id}/resultado_epp.mp4"
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

    return redirect("lista_camaras")
