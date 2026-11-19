"""Acceso autenticado por catálogo, sin rutas arbitrarias ni escritura."""
import html
import base64
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.views.decorators.http import require_safe
from .catalogo import RAICES, DOCUMENTOS, permite
from .fuentes import ROOT
from .media import respuesta_archivo

EXTENSIONES = {".html", ".json", ".jsonl", ".csv", ".md", ".png", ".jpg", ".jpeg", ".mp4"}


def resolver(nombre):
    partes = PurePosixPath(nombre).parts
    if not partes or "\\" in nombre or ":" in nombre or any(p in ("..", ".") for p in partes) or nombre.startswith("/"):
        raise Http404
    modulo = next((m for raiz, m in RAICES.items() if nombre.startswith(raiz + "/")), None)
    documento = nombre in {"docs/" + d for d in DOCUMENTOS}
    if modulo is None and not documento:
        raise Http404
    ruta = ROOT / nombre
    # También rechazar enlaces y junctions que escapen de la carpeta aprobada.
    limite = ROOT / ("docs" if documento else next(r for r in RAICES if nombre.startswith(r + "/")))
    if not limite.resolve().is_relative_to(ROOT.resolve()) or not ruta.resolve().is_relative_to(limite.resolve()) or not ruta.is_file() or ruta.suffix.lower() not in EXTENSIONES:
        raise Http404
    if ruta.name in {"protegidos_antes.json", "codigo_previo_seguridad_epp.py"}:
        raise Http404
    return ruta, modulo


def ocultar_rutas(texto):
    for raiz in (str(ROOT), ROOT.as_posix(), str(ROOT).replace("\\", "\\\\")):
        texto = texto.replace(raiz, "[proyecto]")
    return re.sub(r"[A-Za-z]:[\\/][^\s<>\"']+", "[ruta local omitida]", texto)


@login_required(login_url="/admin/login/")
@require_safe
def artefacto(request, nombre):
    ruta, modulo = resolver(nombre)
    if not (permite(request.user, modulo) if modulo else any(permite(request.user, m) for m in ("epp", "calidad"))):
        return HttpResponseForbidden("No tiene permiso para este módulo.")
    if ruta.suffix.lower() in {".mp4", ".png", ".jpg", ".jpeg"}:
        respuesta = respuesta_archivo(request, ruta)
    else:
        texto = ocultar_rutas(ruta.read_text(encoding="utf-8"))
        if ruta.suffix.lower() == ".html":
            # Solo se permite el filtro original conocido; ningún script arbitrario.
            texto = texto.replace("<head>", '<head><meta name="viewport" content="width=device-width, initial-scale=1"><style>img,video{max-width:100%}body{overflow-wrap:anywhere}@media(max-width:700px){.grid,.paneles{display:block!important}figure{width:100%!important}}</style>', 1)
            texto = '<nav style="padding:12px;background:#142235;color:white"><a style="color:white" href="/" target="_top">Sistema de Inspección IA</a> · Artefacto experimental conservado</nav>' + texto
            respuesta = HttpResponse(texto, content_type="text/html; charset=utf-8")
            filtro = "document.querySelectorAll('article').forEach(a=>a.hidden=this.value!=='TODAS'&&a.dataset.clase!==this.value)"
            firma = base64.b64encode(hashlib.sha256(filtro.encode()).digest()).decode()
            # same-origin conserva cookies para imágenes y videos autenticados.
            respuesta["Content-Security-Policy"] = f"sandbox allow-same-origin allow-scripts allow-top-navigation-by-user-activation; default-src 'self' data:; script-src 'unsafe-hashes' 'sha256-{firma}'; style-src 'unsafe-inline'; object-src 'none'; base-uri 'none'; form-action 'none'"
        else:
            # Informes visibles como texto escapado; no renderizar notas como HTML.
            respuesta = HttpResponse('<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Informe experimental</title><a href="/">Volver al sistema</a><pre style="white-space:pre-wrap;overflow-wrap:anywhere;font:14px monospace">' + html.escape(texto) + '</pre>', content_type="text/html; charset=utf-8")
    respuesta["X-Content-Type-Options"] = "nosniff"
    respuesta["Referrer-Policy"] = "same-origin"
    respuesta["Cache-Control"] = "private, no-store"
    return respuesta
