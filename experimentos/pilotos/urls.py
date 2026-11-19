from django.contrib import admin
from django.urls import include, path
from django.contrib.staticfiles.views import serve as static_local
from .media import archivo
from .panel import calidad
from . import portal
from .artefactos import artefacto
from . import adjudicacion_tapa
from . import revision_tapa_v4
from . import geometria_tapa

urlpatterns = [
    # Estáticos encontrados por Django, solo en este servidor local sin DEBUG.
    path("static/<path:path>", static_local, {"insecure": True}),
    path("", portal.inicio, name="demo_inicio"),
    path("demo/historial/", portal.historial, name="demo_historial"),
    path("demo/calidad/tapa-geometria/", geometria_tapa.revision, name="tapa_geometria"),
    path("demo/calidad/tapa-geometria/imagen/<int:numero>/", geometria_tapa.imagen, name="tapa_geometria_imagen"),
    path("demo/calidad/tapa-geometria/exportar/", geometria_tapa.exportar, name="tapa_geometria_exportar"),
    path("demo/calidad/tapa-v4/", revision_tapa_v4.revision, name="tapa_v4_revision"),
    path("demo/calidad/tapa-v4/imagen/<int:image_id>/<str:tipo>/", revision_tapa_v4.imagen, name="tapa_v4_imagen"),
    path("demo/calidad/tapa-v4/version/<int:numero>/<str:nombre>/", revision_tapa_v4.descarga, name="tapa_v4_descarga"),
    path("demo/calidad/adjudicacion/", adjudicacion_tapa.revision, name="tapa_adjudicacion"),
    path("demo/calidad/adjudicacion/imagen/<int:numero>/<str:tipo>/", adjudicacion_tapa.imagen, name="tapa_adjudicacion_imagen"),
    path("demo/<slug:modulo>/", portal.modulo, name="demo_modulo"),
    path("artefactos/<path:nombre>", artefacto, name="demo_artefacto"),
    path("admin/", admin.site.urls),
    path("monitoreo/", include("monitoreo.urls")),
    path("calidad/", calidad, name="laboratorio_calidad"),
    path("media/<path:nombre>", archivo, name="laboratorio_media"),
]
