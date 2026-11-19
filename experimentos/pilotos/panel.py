from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render
from .fuentes import FUENTES


@login_required(login_url="/admin/login/")
@permission_required("seguridad.view_deteccionepp", raise_exception=True)
def calidad(request):
    return render(request, "monitoreo/calidad_laboratorio.html", {
        "videos": [(ruta.name, "/media/" + alias) for alias, ruta in FUENTES.items()
                   if alias.startswith("fuentes/") and alias != "fuentes/epp_largo.mp4"],
    })
