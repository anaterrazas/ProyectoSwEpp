
from django.urls import path
from . import views
from .piloto import reporte_piloto

urlpatterns = [
    path("piloto/<int:camara_id>/<uuid:ejecucion>/", reporte_piloto, name="reporte_piloto"),
    path(
        "",
        views.lista_camaras,
        name="lista_camaras"
    ),

    path(
        "analizar/<int:camara_id>/",
        views.analizar_camara,
        name="analizar_camara"
    ),
]
