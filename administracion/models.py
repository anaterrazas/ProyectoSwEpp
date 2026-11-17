
from django.db import models


class Trabajador(models.Model):
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    codigo = models.CharField(max_length=20, unique=True)
    cargo = models.CharField(max_length=100)
    activo = models.BooleanField(default=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre} {self.apellido}"

    class Meta:
        verbose_name = "Trabajador"
        verbose_name_plural = "Trabajadores"


class EquipoProteccion(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.CharField(
        max_length=200,
        blank=True
    )

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Equipo de protección"
        verbose_name_plural = "Equipos de protección"


class AreaTrabajo(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)

    NIVEL_RIESGO = [
        ('BAJO', 'Bajo'),
        ('MEDIO', 'Medio'),
        ('ALTO', 'Alto'),
    ]

    nivel_riesgo = models.CharField(
        max_length=10,
        choices=NIVEL_RIESGO,
        default='BAJO'
    )

    equipos_obligatorios = models.ManyToManyField(
        EquipoProteccion,
        blank=True,
        related_name='areas'
    )

    activa = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Área de trabajo"
        verbose_name_plural = "Áreas de trabajo"


class Camara(models.Model):

    TIPOS_MONITOREO = [
        ('EPP', 'Seguridad EPP'),
        ('PRODUCCION', 'Control de producción'),
        ('CALIDAD', 'Control de calidad'),
    ]

    TIPOS_FUENTE = [
        ('VIDEO', 'Archivo de video MP4'),
        ('WEBCAM', 'Cámara web'),
        ('RTSP', 'Cámara IP / RTSP'),
    ]

    nombre = models.CharField(max_length=100)

    area = models.ForeignKey(
        AreaTrabajo,
        on_delete=models.PROTECT,
        related_name='camaras'
    )

    tipo_monitoreo = models.CharField(
        max_length=20,
        choices=TIPOS_MONITOREO
    )

    tipo_fuente = models.CharField(
        max_length=10,
        choices=TIPOS_FUENTE,
        default='VIDEO'
    )

    archivo_video = models.FileField(
        upload_to='videos/',
        blank=True,
        null=True
    )

    url_rtsp = models.CharField(
        max_length=255,
        blank=True
    )

    activa = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Cámara"
        verbose_name_plural = "Cámaras"
