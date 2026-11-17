
from django.contrib import admin
from .models import (
    Trabajador,
    EquipoProteccion,
    AreaTrabajo,  
    Camara

)


@admin.register(Trabajador)
class TrabajadorAdmin(admin.ModelAdmin):
    list_display = (
        "codigo",
        "nombre",
        "apellido",
        "cargo",
        "activo",
    )

    search_fields = (
        "codigo",
        "nombre",
        "apellido",
    )

    list_filter = ("activo",)


@admin.register(EquipoProteccion)
class EquipoProteccionAdmin(admin.ModelAdmin):
    list_display = ("nombre", "descripcion")
    search_fields = ("nombre",)


@admin.register(AreaTrabajo)
class AreaTrabajoAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "nivel_riesgo",
        "activa",
    )

    search_fields = ("nombre",)

    list_filter = (
        "nivel_riesgo",
        "activa",
    )

    filter_horizontal = ("equipos_obligatorios",)


@admin.register(Camara)
class CamaraAdmin(admin.ModelAdmin):

    list_display = (
        'nombre',
        'area',
        'tipo_monitoreo',
        'tipo_fuente',
        'activa'
    )

    list_filter = (
        'tipo_monitoreo',
        'tipo_fuente',
        'activa'
    )

    search_fields = ('nombre',)

