import mimetypes
import re
from pathlib import Path
from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from django.http import FileResponse, Http404, HttpResponse, StreamingHttpResponse, HttpResponseForbidden
from django.views.decorators.http import require_safe
from .fuentes import FUENTES


@login_required(login_url="/admin/login/")
@require_safe
def archivo(request, nombre):
    epp = request.user.has_perm("seguridad.view_deteccionepp")
    fuente_calidad = nombre.startswith("fuentes/") and nombre != "fuentes/epp_largo.mp4"
    if not (epp or (fuente_calidad and request.user.has_perm("produccion.view_analisisproduccion"))):
        return HttpResponseForbidden("No tiene permiso para estos medios.")
    if nombre in FUENTES:
        ruta = FUENTES[nombre]
    else:
        raiz = Path(settings.MEDIA_ROOT).resolve()
        ruta = (raiz / nombre).resolve()
        if not ruta.is_relative_to(raiz):
            raise Http404
    if not ruta.is_file() or ruta.suffix.lower() not in (".mp4", ".jpg", ".jpeg", ".png"):
        raise Http404
    return respuesta_archivo(request, ruta)


def respuesta_archivo(request, ruta):
    """Respuesta de lectura compartida con el catálogo cerrado de artefactos."""
    tamano = ruta.stat().st_size
    tipo = mimetypes.guess_type(ruta.name)[0] or "application/octet-stream"
    rango = request.headers.get("Range")
    if rango:
        match = re.fullmatch(r"bytes=(\d*)-(\d*)", rango)
        if not match or not any(match.groups()):
            return HttpResponse(status=416, headers={"Content-Range": f"bytes */{tamano}"})
        inicio, fin = match.groups()
        if inicio:
            inicio = int(inicio)
            fin = min(int(fin), tamano - 1) if fin else tamano - 1
        else:
            inicio, fin = max(0, tamano - int(fin)), tamano - 1
        if inicio > fin or inicio >= tamano:
            return HttpResponse(status=416, headers={"Content-Range": f"bytes */{tamano}"})
        def partes():
            with ruta.open("rb") as fuente:
                fuente.seek(inicio)
                faltan = fin - inicio + 1
                while faltan:
                    trozo = fuente.read(min(64 * 1024, faltan))
                    if not trozo:
                        break
                    faltan -= len(trozo)
                    yield trozo
        respuesta = StreamingHttpResponse(partes() if request.method != "HEAD" else [], status=206, content_type=tipo)
        respuesta["Content-Range"] = f"bytes {inicio}-{fin}/{tamano}"
        respuesta["Content-Length"] = fin - inicio + 1
    else:
        respuesta = FileResponse(ruta.open("rb"), content_type=tipo)
    respuesta["Accept-Ranges"] = "bytes"
    respuesta["Cache-Control"] = "private, no-cache"
    return respuesta
