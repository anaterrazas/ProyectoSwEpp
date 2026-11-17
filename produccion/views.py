from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess
import traceback
import math
import cv2
import imageio_ffmpeg
from ultralytics import YOLO
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.core.files import File
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from .forms import ClasificacionCalidadForm, NuevoAnalisisForm
from .calidad import actualizar_lote, resumen_calidad
from .detectores import detector_para_producto
from .models import AnalisisProduccion, LoteProduccion, InspeccionCalidad, Producto
from .videos import validar_video

BASE_DIR = Path(__file__).resolve().parent.parent


# ==========================================
# 1. LISTAR ANALISIS DE PRODUCCION
# ==========================================


@login_required(login_url="/admin/login/")
def lista_analisis(request):
    analisis = AnalisisProduccion.objects.select_related("lote", "lote__producto").all()

    return render(request, "produccion/lista_analisis.html", {"analisis": analisis})


# ==========================================
# 2. CREAR NUEVO ANALISIS
# ==========================================


@login_required(login_url="/admin/login/")
@permission_required("produccion.add_analisisproduccion", raise_exception=True)
def crear_analisis(request):
    formulario = NuevoAnalisisForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and formulario.is_valid():
        lote = formulario.cleaned_data["lote"]
        if lote.producto.tipo == Producto.Tipo.BOTELLA:
            analisis = AnalisisProduccion.objects.create(
                lote=lote, video_original=formulario.cleaned_data["video_original"]
            )
        else:
            with transaction.atomic():
                lote = LoteProduccion.objects.select_for_update().get(pk=lote.pk)
                cantidad = formulario.cleaned_data["cantidad"]
                analisis, creado = AnalisisProduccion.objects.get_or_create(
                    solicitud_manual=formulario.cleaned_data["solicitud_manual"],
                    defaults={"lote": lote, "origen": "MANUAL", "cantidad_contada": cantidad,
                              "estado": "COMPLETADO"},
                )
                if analisis.lote_id != lote.pk or analisis.cantidad_contada != cantidad:
                    formulario.add_error(None, "Esta solicitud ya fue usada. Abra un nuevo formulario.")
                elif creado:
                    InspeccionCalidad.objects.bulk_create([
                        InspeccionCalidad(analisis=analisis, identificador=str(n), resultado="REVISION",
                                          observacion="Unidad registrada manualmente. Pendiente de revisión del supervisor.")
                        for n in range(1, cantidad + 1)
                    ])
                    actualizar_lote(lote)
        if not formulario.errors:
            messages.success(request, "Análisis registrado correctamente.")
            return redirect("resultado_analisis", analisis_id=analisis.pk)

    lotes = formulario.fields["lote"].queryset
    return render(request, "produccion/crear_analisis.html", {"lotes": lotes, "formulario": formulario},
                  status=400 if request.method == "POST" else 200)


# ==========================================
# 3. PROCESAR VIDEO CON YOLO, BYTETRACK Y H.264
# ==========================================


@login_required(login_url="/admin/login/")
@permission_required("produccion.change_analisisproduccion", raise_exception=True)
def procesar_analisis(request, analisis_id):
    if request.method != "POST":
        return redirect("resultado_analisis", analisis_id=analisis_id)

    analisis = get_object_or_404(
        AnalisisProduccion.objects.select_related("lote__producto"), id=analisis_id
    )
    if analisis.origen == AnalisisProduccion.Origen.MANUAL:
        messages.error(request, "Un registro manual no se procesa mediante IA. Cree otro análisis si necesita otra medición.")
        return redirect("resultado_analisis", analisis_id=analisis.pk)
    try:
        detector = detector_para_producto(analisis.lote.producto)
    except ValueError as error:
        messages.error(request, str(error))
        return redirect("resultado_analisis", analisis_id=analisis.id)

    modelo_path = BASE_DIR / detector.pesos

    if not modelo_path.exists():
        messages.error(request, "No se encontró yolo11n.pt.")
        return redirect("resultado_analisis", analisis_id=analisis.id)

    # También validar archivos anteriores o cargados desde el administrador.
    try:
        with analisis.video_original.open("rb") as archivo:
            validar_video(archivo)
    except (ValidationError, OSError, ValueError):
        messages.error(request, "Video rechazado: debe ser un MP4 válido dentro de los límites permitidos.")
        return redirect("resultado_analisis", analisis_id=analisis.id)

    adquirido = AnalisisProduccion.objects.filter(pk=analisis.pk).exclude(
        estado="PROCESANDO"
    ).update(estado="PROCESANDO", mensaje_error="")
    if not adquirido:
        messages.warning(request, "Este analisis ya se esta procesando.")
        return redirect("resultado_analisis", analisis_id=analisis.id)

    writer = None
    ruta_temporal = None
    ruta_salida = None
    trabajo = None
    resultados = None
    archivo_guardado = None

    try:
        print("Cargando modelo YOLO11n...")
        modelo = YOLO(str(modelo_path))

        ruta_video = analisis.video_original.path

        captura = cv2.VideoCapture(ruta_video)

        if not captura.isOpened():
            raise ValueError("No se pudo abrir el video original.")

        fps = captura.get(cv2.CAP_PROP_FPS)
        ancho = int(captura.get(cv2.CAP_PROP_FRAME_WIDTH))
        alto = int(captura.get(cv2.CAP_PROP_FRAME_HEIGHT))
        captura.release()

        if not math.isfinite(fps) or fps <= 0:
            fps = 25

        if ancho <= 0 or alto <= 0:
            raise ValueError("Dimensiones de video inválidas.")

        # Línea virtual para el movimiento de derecha a izquierda.
        linea_x = ancho // 2

        trabajo = TemporaryDirectory(prefix=f"analisis_{analisis.id}_")
        ruta_temporal = Path(trabajo.name) / "temporal.mp4"
        ruta_salida = Path(trabajo.name) / "resultado_h264.mp4"

        # OpenCV genera primero un video temporal.
        writer = cv2.VideoWriter(
            str(ruta_temporal), cv2.VideoWriter_fourcc(*"mp4v"), fps, (ancho, alto)
        )

        if not writer.isOpened():
            raise RuntimeError(
                f"No se pudo abrir el escritor de video: {ruta_temporal}"
            )

        print("Escritor de video iniciado correctamente.")
        print(f"Ruta temporal: {ruta_temporal}")
        print(f"Resolución: {ancho}x{alto}")

        posiciones_anteriores = {}
        botellas_contadas = set()

        total_botellas = 0
        fotogramas = 0

        print("Analizando video de producción...")
        print("Dirección: DERECHA A IZQUIERDA")

        resultados = modelo.track(
            source=ruta_video,
            classes=list(detector.clases),
            conf=detector.confianza,
            imgsz=detector.tamano,
            tracker="bytetrack.yaml",
            persist=True,
            stream=True,
            save=False,
            device="cpu",
            verbose=False,
        )

        for resultado in resultados:
            imagen = resultado.plot()

            # Asegurar dimensiones correctas del fotograma
            if imagen.shape[1] != ancho or imagen.shape[0] != alto:
                imagen = cv2.resize(imagen, (ancho, alto))

            cajas = resultado.boxes

            if cajas is not None and cajas.id is not None:
                coordenadas = cajas.xyxy.cpu().numpy()
                identificadores = cajas.id.cpu().numpy()

                for caja, identificador in zip(coordenadas, identificadores):
                    id_botella = int(identificador)

                    x1, y1, x2, y2 = map(int, caja)
                    centro_x = (x1 + x2) // 2

                    posicion_anterior = posiciones_anteriores.get(id_botella)

                    # Contar las botellas visibles en el primer fotograma.
                    if fotogramas == 0:
                        if id_botella not in botellas_contadas:
                            total_botellas += 1
                            botellas_contadas.add(id_botella)

                            print(
                                f"Botella inicial ID {id_botella} "
                                f"| Total: {total_botellas}"
                            )

                    # Contar cuando una botella cruza de derecha a izquierda.
                    elif posicion_anterior is not None:
                        if (
                            posicion_anterior > linea_x
                            and centro_x <= linea_x
                            and id_botella not in botellas_contadas
                        ):
                            total_botellas += 1
                            botellas_contadas.add(id_botella)

                            print(
                                f"Botella contabilizada ID {id_botella} "
                                f"| Total: {total_botellas}"
                            )

                    posiciones_anteriores[id_botella] = centro_x

            # Dibujar línea virtual.
            cv2.line(imagen, (linea_x, 0), (linea_x, alto), (0, 255, 255), 3)

            cv2.putText(
                imagen,
                "LINEA DE CONTEO",
                (min(linea_x + 10, ancho - 220), 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 255),
                2,
            )

            # Mostrar contador.
            cv2.rectangle(imagen, (15, 15), (430, 105), (0, 0, 0), -1)

            cv2.putText(
                imagen,
                f"BOTELLAS CONTADAS: {total_botellas}",
                (30, 55),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.85,
                (0, 255, 0),
                2,
            )

            cv2.putText(
                imagen,
                "DERECHA -> IZQUIERDA",
                (30, 85),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (255, 255, 255),
                1,
            )

            # Guardar fotograma procesado.
            writer.write(imagen)
            fotogramas += 1

            if fotogramas % 50 == 0:
                print(f"Fotogramas: {fotogramas} " f"| Botellas: {total_botellas}")

        # IMPORTANTE: cerrar el escritor después de terminar el bucle.

        # ==========================================
        # FINALIZAR VIDEO TEMPORAL
        # ==========================================

        writer.release()
        writer = None

        if fotogramas == 0:
            raise ValueError("No se procesaron fotogramas.")

        if not ruta_temporal.exists():
            raise ValueError("No se generó el video temporal.")

        if ruta_temporal.stat().st_size == 0:
            raise ValueError("El video temporal está vacío.")

        # ==========================================
        # CONVERTIR A MP4 H.264
        # ==========================================
        comando = [
            imageio_ffmpeg.get_ffmpeg_exe(),
            "-y",
            "-i",
            str(ruta_temporal),
            "-vf",
            "pad=ceil(iw/2)*2:ceil(ih/2)*2",
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
            str(ruta_salida),
        ]

        conversion = subprocess.run(comando, capture_output=True, text=True, errors="replace", timeout=600)

        if conversion.returncode != 0:
            raise RuntimeError("Error convirtiendo video: " + conversion.stderr[-2000:])

        if not ruta_salida.exists() or ruta_salida.stat().st_size == 0:
            raise ValueError("El video H.264 no se generó correctamente.")

        print("Video convertido correctamente.")

        with transaction.atomic():
            lote = LoteProduccion.objects.select_for_update().get(pk=analisis.lote_id)
            anteriores = set(analisis.inspecciones.values_list("identificador", flat=True))
            actuales = {str(i) for i in botellas_contadas}
            if anteriores and anteriores != actuales:
                raise ValueError("Los identificadores cambiaron. Cree otro analisis para conservar las inspecciones anteriores.")
            for identificador in sorted(actuales):
                InspeccionCalidad.objects.get_or_create(
                    analisis=analisis, identificador=identificador,
                    defaults={"resultado": "REVISION", "observacion":
                        "Unidad detectada y contabilizada. Pendiente de evaluacion visual."},
                )
            with ruta_salida.open("rb") as archivo:
                analisis.video_procesado.save(
                    f"analisis_{analisis.id}_h264.mp4", File(archivo), save=False
                )
            archivo_guardado = analisis.video_procesado.name
            analisis.cantidad_contada = total_botellas
            analisis.estado = "COMPLETADO"
            analisis.mensaje_error = ""
            analisis.save()
            actualizar_lote(lote)
        archivo_guardado = None

        messages.success(request, f"Análisis completado: {total_botellas} unidades.")

    except Exception as error:
        traceback.print_exc()
        if archivo_guardado:
            analisis.video_procesado.storage.delete(archivo_guardado)
        AnalisisProduccion.objects.filter(pk=analisis.pk).update(estado="ERROR", mensaje_error=str(error))
        messages.error(request, f"Error al procesar el video: {error}")
    finally:
        if resultados is not None:
            resultados.close()
        if writer is not None:
            writer.release()
        if trabajo is not None:
            trabajo.cleanup()

    return redirect("resultado_analisis", analisis_id=analisis.id)


# ==========================================
# 4. MOSTRAR RESULTADO
# ==========================================


@login_required(login_url="/admin/login/")
def resultado_analisis(request, analisis_id):
    analisis = get_object_or_404(
        AnalisisProduccion.objects.select_related("lote", "lote__producto"),
        id=analisis_id,
    )

    return _mostrar_resultado(request, analisis)


def _mostrar_resultado(request, analisis, *, formulario=None, inspeccion_id=None, status=200):
    inspecciones = list(analisis.inspecciones.select_related("criterio").order_by("pk"))
    filas = []
    for inspeccion in inspecciones:
        form = formulario if inspeccion.pk == inspeccion_id else ClasificacionCalidadForm(
            instance=inspeccion, producto_id=analisis.lote.producto_id,
            prefix=f"unidad-{inspeccion.pk}",
        )
        filas.append((inspeccion, form))
    vigente = analisis.lote.analisis.filter(estado="COMPLETADO").order_by("-fecha_analisis", "-pk").first()
    return render(request, "produccion/resultado_analisis.html", {
        "analisis": analisis, "filas_inspeccion": filas,
        "resumen": resumen_calidad(analisis),
        "es_vigente": vigente is not None and vigente.pk == analisis.pk,
    }, status=status)


@login_required(login_url="/admin/login/")
@permission_required("produccion.change_inspeccioncalidad", raise_exception=True)
@require_POST
def clasificar_inspeccion(request, analisis_id, inspeccion_id):
    analisis = get_object_or_404(
        AnalisisProduccion.objects.select_related("lote", "lote__producto"), pk=analisis_id
    )
    with transaction.atomic():
        lote = LoteProduccion.objects.select_for_update().get(pk=analisis.lote_id)
        analisis = get_object_or_404(
            AnalisisProduccion.objects.select_for_update().select_related("lote", "lote__producto"),
            pk=analisis_id,
        )
        inspeccion = get_object_or_404(
            InspeccionCalidad.objects.select_for_update(), pk=inspeccion_id, analisis=analisis
        )
        if analisis.estado != "COMPLETADO":
            messages.error(request, "Solo se pueden clasificar unidades de un analisis completado.")
            return redirect("resultado_analisis", analisis_id=analisis.pk)
        formulario = ClasificacionCalidadForm(
            request.POST, instance=inspeccion, producto_id=lote.producto_id,
            prefix=f"unidad-{inspeccion.pk}",
        )
        if formulario.is_valid():
            inspeccion = formulario.save(commit=False)
            # Una revision manual no tiene una probabilidad de IA asociada.
            inspeccion.confianza = None
            inspeccion.save(update_fields=["resultado", "criterio", "tipo_defecto", "observacion", "confianza"])
            actualizar_lote(lote)
            messages.success(request, "Clasificacion manual guardada.")
            return redirect("resultado_analisis", analisis_id=analisis.pk)
    return _mostrar_resultado(
        request, analisis, formulario=formulario, inspeccion_id=inspeccion.pk, status=400
    )
