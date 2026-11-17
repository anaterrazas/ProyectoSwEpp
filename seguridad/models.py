
from django.db import models
from administracion.models import Camara


class DeteccionEPP(models.Model):

    TIPOS_DETECCION = [
        ("Person", "Persona"),
        ("Hardhat", "Casco"),
        ("NO-Hardhat", "Sin casco"),
        ("Safety Vest", "Chaleco"),
        ("NO-Safety Vest", "Sin chaleco"),
        ("Gloves", "Guantes"),
        ("NO-Gloves", "Sin guantes"),
        ("Goggles", "Gafas"),
        ("NO-Goggles", "Sin gafas"),
        ("Mask", "Mascarilla"),
        ("NO-Mask", "Sin mascarilla"),
    ]

    camara = models.ForeignKey(
        Camara,
        on_delete=models.PROTECT,
        related_name="detecciones_epp"
    )

    tipo = models.CharField(
        max_length=50,
        choices=TIPOS_DETECCION
    )

    confianza = models.FloatField()

    segundo_video = models.FloatField(
        default=0
    )

    fecha_deteccion = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.camara.nombre}"

    class Meta:
        verbose_name = "Detección de EPP"
        verbose_name_plural = "Detecciones de EPP"
        ordering = ["-fecha_deteccion"]
