from django import forms
from uuid import uuid4

from .models import CriterioCalidad, InspeccionCalidad, LoteProduccion, Producto
from .videos import validar_video


class NuevoAnalisisForm(forms.Form):
    lote = forms.ModelChoiceField(queryset=LoteProduccion.objects.select_related("producto"))
    video_original = forms.FileField(required=False, validators=[validar_video], label="Video de producción",
                                    widget=forms.ClearableFileInput(attrs={"accept": "video/mp4"}))
    cantidad = forms.IntegerField(required=False, min_value=1, max_value=10000,
                                 label="Cantidad de unidades producidas")
    solicitud_manual = forms.UUIDField(required=False, initial=uuid4, widget=forms.HiddenInput)

    def clean(self):
        datos = super().clean()
        lote = datos.get("lote")
        if lote is None:
            return datos
        if lote.producto.tipo == Producto.Tipo.BOTELLA:
            if not datos.get("video_original"):
                self.add_error("video_original", "Cargue el video para el conteo de botellas.")
        else:
            if datos.get("cantidad") is None:
                self.add_error("cantidad", "Indique un entero positivo de unidades.")
            if datos.get("solicitud_manual") is None:
                self.add_error("solicitud_manual", "Recargue el formulario e intente nuevamente.")
            if datos.get("video_original"):
                self.add_error("video_original", "El registro manual no requiere video. Retire el archivo.")
        return datos


class ClasificacionCalidadForm(forms.ModelForm):
    class Meta:
        model = InspeccionCalidad
        fields = ["resultado", "criterio", "tipo_defecto", "observacion"]
        widgets = {"observacion": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, producto_id, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["criterio"].queryset = CriterioCalidad.objects.filter(
            producto_id=producto_id, activo=True
        ).order_by("nombre")
        for field in self.fields.values():
            field.widget.attrs["class"] = (
                "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            )

    def clean(self):
        datos = super().clean()
        resultado = datos.get("resultado")
        if resultado == "DEFECTUOSO" and not datos.get("criterio"):
            self.add_error("criterio", "Seleccione un criterio activo del producto para registrar un defecto.")
        if resultado in ("CONFORME", "REVISION"):
            datos["criterio"] = None
            datos["tipo_defecto"] = ""
        return datos
