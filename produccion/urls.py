
from django.urls import path
from . import views, consultas

urlpatterns = [
    path("resultados/", consultas.panel_resultados, name="panel_resultados"),
    path("resultados/informe/", consultas.descargar_resultados, name="descargar_resultados"),
    path("lotes/<int:lote_id>/", consultas.detalle_lote, name="detalle_lote"),
    path("lotes/<int:lote_id>/informe/", consultas.descargar_resultados, name="descargar_resultados_lote"),
    path("resultado/<int:analisis_id>/inspecciones/<int:inspeccion_id>/clasificar/",
         views.clasificar_inspeccion, name="clasificar_inspeccion"),
    path(
        "",
        views.lista_analisis,
        name="lista_analisis"
    ),

    path(
        "nuevo/",
        views.crear_analisis,
        name="crear_analisis"
    ),

    path(
        "procesar/<int:analisis_id>/",
        views.procesar_analisis,
        name="procesar_analisis"
    ),

    path(
        "resultado/<int:analisis_id>/",
        views.resultado_analisis,
        name="resultado_analisis"
    ),
]
