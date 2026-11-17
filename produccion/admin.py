from django.contrib import admin
from django import forms
from .videos import validar_video

from .models import (
    Producto,
    CriterioCalidad,
    LoteProduccion,
    AnalisisProduccion,
    InspeccionCalidad,
)

# ==========================================
# CRITERIOS DE CALIDAD DENTRO DEL PRODUCTO
# ==========================================


class CriterioCalidadInline(admin.TabularInline):
    model = CriterioCalidad
    extra = 1


# ==========================================
# PRODUCTOS
# ==========================================


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):

    list_display = (
        "nombre",
        "tipo",
        "activo",
    )

    search_fields = ("nombre",)

    list_filter = ("tipo", "activo")

    inlines = [CriterioCalidadInline]


# ==========================================
# CRITERIOS DE CALIDAD
# ==========================================


@admin.register(CriterioCalidad)
class CriterioCalidadAdmin(admin.ModelAdmin):

    list_display = (
        "nombre",
        "producto",
        "activo",
    )

    search_fields = (
        "nombre",
        "producto__nombre",
    )

    list_filter = (
        "producto",
        "activo",
    )


# ==========================================
# LOTES DE PRODUCCION
# ==========================================


@admin.register(LoteProduccion)
class LoteProduccionAdmin(admin.ModelAdmin):

    list_display = (
        "codigo",
        "producto",
        "estado",
        "cantidad_producida",
        "cantidad_conforme",
        "cantidad_defectuosa",
        "fecha_creacion",
    )

    list_filter = (
        "estado",
        "producto",
    )

    search_fields = ("codigo",)


# ==========================================
# ANALISIS DE PRODUCCION
# ==========================================


class AnalisisAdminForm(forms.ModelForm):
    class Meta:
        model = AnalisisProduccion
        fields = "__all__"

    def clean_video_original(self):
        archivo = self.cleaned_data.get("video_original")
        if archivo and "video_original" in self.changed_data:
            validar_video(archivo)
        return archivo


@admin.register(AnalisisProduccion)
class AnalisisProduccionAdmin(admin.ModelAdmin):
    form = AnalisisAdminForm

    list_display = (
        "id",
        "lote",
        "cantidad_contada",
        "estado",
        "fecha_analisis",
    )

    list_filter = (
        "estado",
        "fecha_analisis",
    )

    search_fields = (
        "lote__codigo",
        "lote__producto__nombre",
    )

    readonly_fields = (
        "cantidad_contada",
        "estado",
        "video_procesado",
        "fecha_analisis",
        "mensaje_error",
    )

    list_select_related = ("lote",)

    date_hierarchy = "fecha_analisis"


# ==========================================
# INSPECCIONES DE CALIDAD
# ==========================================


@admin.register(InspeccionCalidad)
class InspeccionCalidadAdmin(admin.ModelAdmin):

    list_display = (
        "identificador",
        "analisis",
        "criterio",
        "resultado",
        "tipo_defecto",
        "confianza",
        "fecha_inspeccion",
    )

    list_filter = (
        "resultado",
        "criterio__producto",
        "fecha_inspeccion",
    )

    search_fields = (
        "identificador",
        "tipo_defecto",
        "analisis__lote__codigo",
        "criterio__nombre",
    )

    list_select_related = (
        "analisis",
        "analisis__lote",
        "criterio",
    )

    readonly_fields = ("fecha_inspeccion",)

    date_hierarchy = "fecha_inspeccion"
