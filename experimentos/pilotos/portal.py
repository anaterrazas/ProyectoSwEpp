"""Presentación de resultados existentes; sin invocar motores de IA."""
from pathlib import Path
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_safe
from .catalogo import ROOT, LAB, SIM, MODULOS, EJECUCIONES, DOCUMENTOS, leer, permite
from .fuentes import FUENTES


def enlace(nombre, ruta):
    return {"nombre": nombre, "url": reverse("demo_artefacto", args=[ruta]), "disponible": (ROOT/ruta).is_file()}


def contexto(request):
    return {"accesos": [{"id": k, **v} for k, v in MODULOS.items() if permite(request.user, k)], "documentos": [enlace(d.replace("_", " ").removesuffix(".md"), "docs/"+d) for d in DOCUMENTOS]}


@login_required(login_url="/admin/login/")
@require_safe
def inicio(request):
    return render(request, "demo/inicio.html", contexto(request))


@login_required(login_url="/admin/login/")
@require_safe
def modulo(request, modulo):
    if modulo not in MODULOS:
        raise Http404
    if not permite(request.user, modulo):
        return HttpResponseForbidden("No tiene permiso para este módulo.")
    ctx = contexto(request)
    ctx.update(modulo=modulo, ficha=MODULOS[modulo])
    if modulo == "epp":
        pref = LAB+"comparacion_videos_epp_v002_001/"
        ctx["videos"] = [enlace("Comparación base / candidata · "+n, pref+f"epp_{v}_base_vs_candidata.mp4") for v,n in [("corto", "4,88 s"), ("largo", "10,08 s")]]
        ctx["fuentes"] = [{"nombre": "Original EPP · "+n, "url": "/media/"+a} for n,a in [("corto", "videos/trabajadores.mp4"), ("largo", "fuentes/epp_largo.mp4")]]
        ctx["recursos"] = [enlace("Galería comparativa · 33 referencias", pref+"index.html"), enlace("Galería priorizada · 83 errores", LAB+"auditoria_errores_epp33_v002_001/index.html"), enlace("Informe temporal", pref+"INFORME_VIDEOS_EPP.md"), enlace("Parámetros candidata", pref+"plan.json"), enlace("Modelos y pesos", LAB+"seguridad_epp_v002_001/modelos_y_parametros.json"), enlace("Errores individuales", pref+"errores_33.json"), enlace("Seguimiento y persistencia", pref+"comparacion_temporal.json")]
        filas=[]
        for config in ("base", "candidata"):
            datos=leer(pref+f"metricas_33_{config}.json")
            if datos:
                for clase,m in datos["metricas"]["deteccion"].items():
                    filas.append({"config":config,"clase":clase,**m,"p":porcentaje(m["precision"]),"r":porcentaje(m["recall"]),"f":porcentaje(m["f1"])})
        ctx["metricas"]=filas
    else:
        pref=LAB+"evaluacion_deteccion_v002_001/"
        ctx["videos"]=[enlace("Simulación ENVASE y seguimiento · NO EVALUABLE",SIM+"processed.mp4")]
        ctx["fuentes"]=[{"nombre":p.name,"url":"/media/"+a} for a,p in FUENTES.items() if a.startswith("fuentes/") and a!="fuentes/epp_largo.mp4"]
        ctx["recursos"]=[enlace("Galería ENVASE · 25 referencias",pref+"index.html"),enlace("Informe y limitaciones",pref+"INFORME.md"),enlace("Predicciones y trazabilidad",pref+"predicciones.json"),enlace("Conflictos de referencia",pref+"conflictos_semanticos.json"),enlace("Registro de errores",pref+"errores.csv"),enlace("Reporte de simulación",SIM+"report.json"),enlace("Perfil de dominio",SIM+"reference_domain_profile.json")]
        ctx["evidencias"]=[enlace("Simulación · fotograma "+str(n),SIM+f"screenshots/frame_{n:06d}.jpg") for n in (0,199,398)]
        ctx["recursos"].insert(0,{"nombre":"Adjudicar los siete conflictos · revisión humana","url":reverse("tapa_adjudicacion"),"disponible":True})
        ctx["recursos"].insert(0,{"nombre":"TAPA Roboflow v4 · adjudicación final y exhaustividad","url":reverse("tapa_v4_revision"),"disponible":True})
        ctx["recursos"].insert(0,{"nombre":"TAPA · ajuste humano de geometría v26 y reserva v4","url":reverse("tapa_geometria"),"disponible":True})
        datos=leer(pref+"comparacion.json")
        ctx["calidad_metricas"]=datos.get("por_clase",{}).get("ENVASE") if datos else None
        if ctx["calidad_metricas"]:
            m=ctx["calidad_metricas"];ctx["calidad_precision"]=porcentaje(m["precision"]);ctx["calidad_recall"]=porcentaje(m["recall"])
    return render(request,"demo/modulo.html",ctx)


def porcentaje(valor):
    return "NO DISPONIBLE" if valor is None else f"{valor*100:.2f} %".replace(".",",")


@login_required(login_url="/admin/login/")
@require_safe
def historial(request):
    ctx=contexto(request);registros=[]
    for mod,titulo,manifiesto,recurso,nota in EJECUCIONES:
        if permite(request.user,mod):
            datos=leer(manifiesto)
            registros.append({"modulo":MODULOS[mod]["nombre"],"titulo":titulo,"nota":nota,"estado":"Disponible" if datos is not None else "Manifiesto no disponible","manifiesto":enlace("Consultar manifiesto",manifiesto),"resultado":enlace("Abrir resultados",recurso)})
    revisiones=[]
    if permite(request.user,"epp"):
        base=Path(settings.MEDIA_ROOT).resolve()
        for ruta in sorted(base.glob("resultados_ia/camara_*/*/reporte.json")):
            if not ruta.resolve().is_relative_to(base):
                continue
            import json
            try:datos=json.loads(ruta.read_text(encoding="utf-8"))
            except (OSError,ValueError):continue
            for indice,evento in enumerate(datos.get("eventos",[])):
                for revision in evento.get("historial",[]):
                    revisiones.append({"ejecucion":ruta.parent.name,"evento":indice,"equipo":evento.get("equipo"),"fecha":revision.get("fecha"),"autor":revision.get("usuario"),"decision":revision.get("decision"),"nota":revision.get("nota")})
    ctx.update(registros=registros,revisiones=revisiones)
    return render(request,"demo/historial.html",ctx)
