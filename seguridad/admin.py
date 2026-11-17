
from django.contrib import admin
from django.utils.html import format_html
from .models import DeteccionEPP


@admin.register(DeteccionEPP)
class DeteccionEPPAdmin(admin.ModelAdmin):

    list_display = (
        "tipo",
        "camara",
        "confianza_porcentaje",
        "segundo_video",
        "fecha_deteccion",
    )

    list_filter = (
        "tipo",
        "camara",
        "fecha_deteccion",
    )

    search_fields = ("camara__nombre",)

    readonly_fields = ("fecha_deteccion",)

    @admin.display(description="Confianza")
    def confianza_porcentaje(self, obj):
        return f"{obj.confianza * 100:.1f}%"
