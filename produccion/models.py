from django.db import models


class Producto(models.Model):
    class Tipo(models.TextChoices):
        BOTELLA = "BOTELLA", "Botellas"
        CAJA = "CAJA", "Cajas"
        BOLSA = "BOLSA", "Bolsas"

    tipo = models.CharField(max_length=10, choices=Tipo.choices, default=Tipo.BOTELLA)
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(tipo__in=["BOTELLA", "CAJA", "BOLSA"]),
                name="producto_tipo_admitido",
            )
        ]


class CriterioCalidad(models.Model):
    producto = models.ForeignKey(
        Producto, on_delete=models.CASCADE, related_name="criterios"
    )

    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.producto.nombre} - {self.nombre}"

    class Meta:
        verbose_name = "Criterio de calidad"
        verbose_name_plural = "Criterios de calidad"
        constraints = [
            models.UniqueConstraint(
                fields=["producto", "nombre"], name="criterio_unico_por_producto"
            )
        ]


class LoteProduccion(models.Model):

    ESTADOS = [
        ("PENDIENTE", "Pendiente"),
        ("EN_PROCESO", "En proceso"),
        ("FINALIZADO", "Finalizado"),
    ]

    codigo = models.CharField(max_length=30, unique=True)

    producto = models.ForeignKey(
        Producto, on_delete=models.PROTECT, related_name="lotes"
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)

    estado = models.CharField(max_length=20, choices=ESTADOS, default="PENDIENTE")

    cantidad_producida = models.PositiveIntegerField(default=0)

    cantidad_conforme = models.PositiveIntegerField(default=0)

    cantidad_defectuosa = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.codigo

    class Meta:
        verbose_name = "Lote de producción"
        verbose_name_plural = "Lotes de producción"


class AnalisisProduccion(models.Model):
    class Origen(models.TextChoices):
        IA = "IA", "Conteo IA"
        MANUAL = "MANUAL", "Registro manual"

    origen = models.CharField(max_length=10, choices=Origen.choices, default=Origen.IA)
    solicitud_manual = models.UUIDField(null=True, blank=True, unique=True, editable=False)

    ESTADOS = [
        ("PENDIENTE", "Pendiente"),
        ("PROCESANDO", "Procesando"),
        ("COMPLETADO", "Completado"),
        ("ERROR", "Error"),
    ]

    lote = models.ForeignKey(
        LoteProduccion, on_delete=models.PROTECT, related_name="analisis"
    )

    video_original = models.FileField(upload_to="produccion/videos/", blank=True)

    video_procesado = models.FileField(
        upload_to="produccion/resultados/", blank=True, null=True
    )

    cantidad_contada = models.PositiveIntegerField(default=0)

    estado = models.CharField(max_length=20, choices=ESTADOS, default="PENDIENTE")

    fecha_analisis = models.DateTimeField(auto_now_add=True)

    mensaje_error = models.TextField(blank=True)

    def __str__(self):
        return f"Análisis {self.id} - {self.lote.codigo}"

    class Meta:
        verbose_name = "Análisis de producción"
        verbose_name_plural = "Análisis de producción"
        ordering = ["-fecha_analisis"]


class InspeccionCalidad(models.Model):

    RESULTADOS = [
        ("CONFORME", "Conforme"),
        ("DEFECTUOSO", "Defectuoso"),
        ("REVISION", "Pendiente de revisión"),
    ]

    analisis = models.ForeignKey(
        AnalisisProduccion, on_delete=models.CASCADE, related_name="inspecciones"
    )

    criterio = models.ForeignKey(
        CriterioCalidad,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inspecciones",
    )

    identificador = models.CharField(max_length=50)

    resultado = models.CharField(max_length=20, choices=RESULTADOS, default="REVISION")

    tipo_defecto = models.CharField(max_length=150, blank=True)

    confianza = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )

    observacion = models.TextField(blank=True)

    fecha_inspeccion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Unidad {self.identificador} - " f"{self.get_resultado_display()}"

    class Meta:
        verbose_name = "Inspección de calidad"
        verbose_name_plural = "Inspecciones de calidad"
        ordering = ["-fecha_inspeccion"]

        constraints = [
            models.UniqueConstraint(
                fields=["analisis", "identificador"], name="inspeccion_unica_por_unidad"
            )
        ]
