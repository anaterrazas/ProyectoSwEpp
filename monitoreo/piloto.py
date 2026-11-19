"""Consulta y revisión de candidatos del piloto sin alterar detecciones históricas."""
import json
import os
import uuid
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.urls import reverse

from administracion.models import Camara


@login_required(login_url="/admin/login/")
@permission_required("seguridad.view_deteccionepp", raise_exception=True)
@require_http_methods(["GET", "POST"])
def reporte_piloto(request, camara_id, ejecucion):
    camara = get_object_or_404(Camara, pk=camara_id)
    relativo = f"resultados_ia/camara_{camara.pk}/{ejecucion.hex}"
    carpeta = Path(settings.MEDIA_ROOT) / relativo
    ruta = carpeta / "reporte.json"
    if not ruta.is_file():
        raise Http404("No existe el reporte del piloto.")
    if request.method == "POST":
        if not request.user.has_perm("seguridad.change_deteccionepp"):
            return HttpResponse("No tiene permiso para revisar eventos.", status=403)
        estado = request.POST.get("revision")
        nota = request.POST.get("nota", "").strip()
        try:
            indice = int(request.POST.get("evento", ""))
        except ValueError:
            return HttpResponse("Evento inválido.", status=400)
        if estado not in ("CONFIRMADO", "DESCARTADO", "NO_EVALUABLE") or not nota or len(nota) > 2000:
            return HttpResponse("Indique una decisión y una observación de hasta 2000 caracteres.", status=400)
        bloqueo = carpeta / "revision.lock"
        try:
            descriptor = os.open(bloqueo, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return HttpResponse("Hay otra revisión en curso. Reintente.", status=409)
        temporal = carpeta / f"{uuid.uuid4().hex}.tmp"
        try:
            os.close(descriptor)
            datos = json.loads(ruta.read_text(encoding="utf-8"))
            if indice < 0 or indice >= len(datos["eventos"]):
                return HttpResponse("Evento inválido.", status=400)
            evento = datos["eventos"][indice]
            if request.POST.get("version", "") != str(len(evento.get("historial", []))):
                return HttpResponse("La revisión cambió. Recargue el reporte.", status=409)
            evento.setdefault("historial", []).append({
                "usuario_id": request.user.pk, "usuario": request.user.get_username(),
                "fecha": timezone.now().isoformat(), "decision": estado, "nota": nota,
            })
            evento["revision"] = estado
            temporal.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(temporal, ruta)
        finally:
            temporal.unlink(missing_ok=True)
            bloqueo.unlink(missing_ok=True)
        return redirect("reporte_piloto", camara_id=camara.pk, ejecucion=ejecucion)
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    base_media = settings.MEDIA_URL.rstrip("/") + "/" + relativo
    for evento in datos.get("eventos", []):
        nombre = evento.get("evidencia", "")
        evento["evidencia_url"] = (
            base_media + "/" + nombre
            if nombre and Path(nombre).name == nombre and (carpeta / nombre).is_file()
            else None
        )
    conteos = datos.get("observaciones_por_estado", {})
    total = sum(conteos.get(estado, 0) for estado in ("CUMPLE", "INCUMPLIMIENTO", "NO_EVALUABLE"))
    evaluables = conteos.get("CUMPLE", 0) + conteos.get("INCUMPLIMIENTO", 0)
    return render(request, "monitoreo/piloto.html", {
        "camara": camara, "reporte": datos,
        "renderizado": "si", "base_media": base_media,
        "video_resultado_url": base_media + "/resultado_epp.mp4" if (carpeta / "resultado_epp.mp4").is_file() else None,
        "video_original_url": camara.archivo_video.url if camara.archivo_video else None,
        "revision_url": reverse("reporte_piloto", args=[camara.pk, ejecucion]),
        "total_observaciones": total, "observaciones_evaluables": evaluables,
        "cobertura_porcentaje": 100 * evaluables / total if total else None,
    })
