
from django.urls import path
from . import views

urlpatterns = [
    path(
        "seguridad/",
        views.dashboard_seguridad,
        name="dashboard_seguridad"
    ),
]
