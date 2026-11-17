
from django.urls import path
from . import views

urlpatterns = [
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
