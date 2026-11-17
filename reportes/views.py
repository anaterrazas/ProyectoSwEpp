
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import render

from administracion.models import Camara
from seguridad.models import DeteccionEPP


@login_required(login_url="/admin/login/")
def dashboard_seguridad(request):

    # Estadísticas generales
    total_detecciones = DeteccionEPP.objects.count()

    cascos = DeteccionEPP.objects.filter(
        tipo="Hardhat"
    ).count()

    chalecos = DeteccionEPP.objects.filter(
        tipo="Safety Vest"
    ).count()

    camaras_activas = Camara.objects.filter(
        activa=True
    ).count()

    # Conteo agrupado por tipo de detección
    datos_grafico = list(
        DeteccionEPP.objects
        .values("tipo")
        .annotate(total=Count("id"))
        .order_by("tipo")
    )

    # Últimas 10 detecciones
    ultimas_detecciones = (
        DeteccionEPP.objects
        .select_related("camara")
        .order_by("-fecha_deteccion", "-id")[:10]
    )

    contexto = {
        "total_detecciones": total_detecciones,
        "cascos": cascos,
        "chalecos": chalecos,
        "camaras_activas": camaras_activas,
        "datos_grafico": datos_grafico,
        "ultimas_detecciones": ultimas_detecciones,
    }

    return render(
        request,
        "reportes/dashboard_seguridad.html",
        contexto
    )
