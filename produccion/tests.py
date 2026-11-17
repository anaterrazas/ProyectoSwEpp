from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess
from unittest.mock import patch

import cv2
import imageio_ffmpeg
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files import File
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Producto, LoteProduccion, AnalisisProduccion
from .test_support import autorizar_supervisor


class FlujoProduccionTests(TestCase):
    def setUp(self):
        self.media = TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        self.config = override_settings(MEDIA_ROOT=self.media.name)
        self.config.enable()
        self.addCleanup(self.config.disable)
        self.client.force_login(autorizar_supervisor(get_user_model().objects.create_user(username="prueba")))
        self.lote = LoteProduccion.objects.create(
            codigo="PRUEBA", producto=Producto.objects.create(nombre="Botella")
        )
        with (Path(settings.BASE_DIR) / "pruebas_ia/produccion.mp4").open("rb") as video:
            self.analisis = AnalisisProduccion.objects.create(lote=self.lote, video_original=File(video, name="prueba.mp4"))

    def test_video_real_y_reprocesamiento(self):
        for nombre in ("lista_analisis", "crear_analisis"):
            self.assertEqual(self.client.get(reverse(nombre)).status_code, 200)
        url = reverse("procesar_analisis", args=[self.analisis.pk])
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.post(url)
        self.analisis.refresh_from_db()
        self.assertEqual(self.analisis.estado, "COMPLETADO", self.analisis.mensaje_error)
        self.assertEqual(self.analisis.cantidad_contada, 8)
        self.assertEqual(self.analisis.inspecciones.count(), 8)
        self.assertEqual(self.analisis.inspecciones.filter(resultado="REVISION").count(), 8)
        ids = list(self.analisis.inspecciones.order_by("pk").values_list("pk", flat=True))
        ruta = self.analisis.video_procesado.path
        cap = cv2.VideoCapture(ruta)
        try:
            self.assertTrue(cap.isOpened())
            self.assertEqual(int(cap.get(cv2.CAP_PROP_FRAME_COUNT)), 434)
            self.assertTrue(cap.read()[0])
        finally:
            cap.release()
        probe = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-i", ruta, "-f", "null", "-"], capture_output=True, text=True)
        self.assertEqual(probe.returncode, 0, probe.stderr)
        self.assertIn("h264", probe.stderr)
        self.assertIn("yuv420p", probe.stderr)
        data = Path(ruta).read_bytes()
        self.assertLess(data.index(b"moov"), data.index(b"mdat"))
        unidad = self.analisis.inspecciones.order_by("pk").first()
        respuesta = self.client.post(
            reverse("clasificar_inspeccion", args=[self.analisis.pk, unidad.pk]),
            {f"unidad-{unidad.pk}-resultado": "CONFORME",
             f"unidad-{unidad.pk}-observacion": "Conforme tras revision manual"},
        )
        self.assertEqual(respuesta.status_code, 302)
        self.client.post(url)
        self.analisis.refresh_from_db()
        self.assertEqual(self.analisis.estado, "COMPLETADO", self.analisis.mensaje_error)
        self.assertEqual(list(self.analisis.inspecciones.order_by("pk").values_list("pk", flat=True)), ids)
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.cantidad_producida, 8)
        self.assertEqual(self.lote.cantidad_conforme, 1)
        self.assertEqual(self.lote.cantidad_defectuosa, 0)
        self.assertEqual(self.lote.estado, "EN_PROCESO")
        unidad.refresh_from_db()
        self.assertEqual(unidad.resultado, "CONFORME")
        self.assertEqual(unidad.observacion, "Conforme tras revision manual")
        cap_original = cv2.VideoCapture(self.analisis.video_original.path)
        try:
            self.assertTrue(cap_original.read()[0])
        finally:
            cap_original.release()

        resultado = self.client.get(reverse("resultado_analisis", args=[self.analisis.pk]))
        self.assertContains(resultado, "Inspecciones individuales")
        self.assertContains(resultado, self.analisis.video_procesado.url)
        with patch("produccion.views.YOLO", side_effect=RuntimeError("fallo simulado")):
            self.client.post(url)
        self.analisis.refresh_from_db()
        self.assertEqual(self.analisis.estado, "ERROR")
        self.assertEqual(self.analisis.inspecciones.count(), 8)
        self.assertTrue(Path(self.analisis.video_procesado.path).exists())


class ClasificacionCalidadTests(TestCase):
    def setUp(self):
        from .models import CriterioCalidad, InspeccionCalidad
        self.client.force_login(autorizar_supervisor(get_user_model().objects.create_user(username="supervisor")))
        self.producto = Producto.objects.create(nombre="Producto configurable")
        self.lote = LoteProduccion.objects.create(codigo="CALIDAD", producto=self.producto)
        self.analisis = AnalisisProduccion.objects.create(
            lote=self.lote, cantidad_contada=8, estado="COMPLETADO",
            video_original="produccion/videos/original.mp4", video_procesado="produccion/resultados/procesado.mp4",
        )
        self.unidades = [InspeccionCalidad.objects.create(analisis=self.analisis, identificador=str(i)) for i in range(8)]
        self.criterio = CriterioCalidad.objects.create(producto=self.producto, nombre="Defecto configurable")
        self.otro = CriterioCalidad.objects.create(producto=Producto.objects.create(nombre="Otro"), nombre="Otro defecto")
        self.inactivo = CriterioCalidad.objects.create(producto=self.producto, nombre="Inactivo", activo=False)

    def guardar(self, unidad=None, resultado="CONFORME", criterio="", **extra):
        unidad = unidad or self.unidades[0]
        datos = {f"unidad-{unidad.pk}-resultado": resultado,
                 f"unidad-{unidad.pk}-criterio": criterio,
                 f"unidad-{unidad.pk}-observacion": "Revision del supervisor"}
        datos.update({f"unidad-{unidad.pk}-{k}": v for k, v in extra.items()})
        return self.client.post(reverse("clasificar_inspeccion", args=[unidad.analisis_id, unidad.pk]), datos)

    def test_conforme_y_revision(self):
        self.assertEqual(self.guardar().status_code, 302)
        unidad = self.unidades[0]; unidad.refresh_from_db()
        self.assertEqual(unidad.resultado, "CONFORME")
        self.assertIsNone(unidad.criterio)
        self.assertIsNone(unidad.confianza)
        self.assertEqual(unidad.observacion, "Revision del supervisor")
        self.lote.refresh_from_db()
        self.assertEqual((self.lote.cantidad_producida, self.lote.cantidad_conforme, self.lote.cantidad_defectuosa, self.lote.estado), (8, 1, 0, "EN_PROCESO"))
        self.assertEqual(self.guardar(resultado="REVISION").status_code, 302)
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.cantidad_conforme, 0)
        unidad.refresh_from_db(); self.assertEqual(unidad.resultado, "REVISION")

    def test_defectuoso_y_finalizacion(self):
        self.assertEqual(self.guardar(resultado="DEFECTUOSO", criterio=self.criterio.pk, tipo_defecto="Danio visible").status_code, 302)
        unidad = self.unidades[0]; unidad.refresh_from_db()
        self.assertEqual((unidad.resultado, unidad.criterio_id, unidad.tipo_defecto), ("DEFECTUOSO", self.criterio.pk, "Danio visible"))
        for unidad in self.unidades[1:]:
            self.assertEqual(self.guardar(unidad).status_code, 302)
        self.lote.refresh_from_db()
        self.assertEqual((self.lote.cantidad_producida, self.lote.cantidad_conforme, self.lote.cantidad_defectuosa, self.lote.estado), (8, 7, 1, "FINALIZADO"))
        page = self.client.get(reverse("resultado_analisis", args=[self.analisis.pk]))
        self.assertEqual(page.context["resumen"]["porcentaje_conformidad"], 87.5)
        self.assertEqual(page.context["resumen"]["porcentaje_defectos"], 12.5)
        self.assertEqual(page.context["resumen"]["pendientes"], 0)
        self.assertEqual(self.analisis.inspecciones.count(), 8)
        self.guardar(resultado="REVISION")
        self.lote.refresh_from_db(); self.assertEqual(self.lote.estado, "EN_PROCESO")

    def test_rechaza_clasificaciones_invalidas(self):
        for criterio in ("", self.otro.pk, self.inactivo.pk, "abc", 99999):
            with self.subTest(criterio=criterio):
                self.assertEqual(self.guardar(resultado="DEFECTUOSO", criterio=criterio).status_code, 400)
                self.unidades[0].refresh_from_db()
                self.assertEqual(self.unidades[0].resultado, "REVISION")
        self.assertEqual(self.guardar(resultado="INVENTADO").status_code, 400)
        self.assertEqual(self.guardar(tipo_defecto="x" * 151).status_code, 400)

    def test_historico_no_reemplaza_vigente(self):
        from .models import InspeccionCalidad
        nuevo = AnalisisProduccion.objects.create(lote=self.lote, estado="COMPLETADO", cantidad_contada=1, video_original="nuevo.mp4")
        unidad = InspeccionCalidad.objects.create(analisis=nuevo, identificador="1")
        self.guardar(unidad)
        self.guardar(resultado="DEFECTUOSO", criterio=self.criterio.pk)
        self.lote.refresh_from_db()
        self.assertEqual((self.lote.cantidad_producida, self.lote.cantidad_conforme, self.lote.cantidad_defectuosa, self.lote.estado), (1, 1, 0, "FINALIZADO"))
        self.assertEqual(self.analisis.inspecciones.count(), 8)
        self.analisis.refresh_from_db()
        self.assertEqual(self.analisis.video_original.name, "produccion/videos/original.mp4")
        self.assertEqual(self.analisis.video_procesado.name, "produccion/resultados/procesado.mp4")

    def test_autenticacion_csrf_metodo_e_identificadores(self):
        from django.test import Client
        url = reverse("clasificar_inspeccion", args=[self.analisis.pk, self.unidades[0].pk])
        anonimo = Client()
        self.assertEqual(anonimo.post(url).status_code, 302)
        self.assertEqual(self.client.get(url).status_code, 405)
        protegido = Client(enforce_csrf_checks=True)
        protegido.force_login(get_user_model().objects.get(username="supervisor"))
        self.assertEqual(protegido.post(url, {}).status_code, 403)
        otro = AnalisisProduccion.objects.create(lote=self.lote, video_original="otro.mp4", estado="COMPLETADO")
        self.assertEqual(self.client.post(reverse("clasificar_inspeccion", args=[otro.pk, self.unidades[0].pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("clasificar_inspeccion", args=[self.analisis.pk, 99999])).status_code, 404)
        for estado in ("PENDIENTE", "PROCESANDO", "ERROR"):
            self.analisis.estado = estado; self.analisis.save()
            self.assertEqual(self.guardar().status_code, 302)
            self.unidades[0].refresh_from_db()
            self.assertEqual(self.unidades[0].resultado, "REVISION")

    def test_resumen_vacio(self):
        vacio = AnalisisProduccion.objects.create(lote=self.lote, video_original="vacio.mp4")
        page = self.client.get(reverse("resultado_analisis", args=[vacio.pk]))
        self.assertEqual(page.status_code, 200)
        self.assertEqual(page.context["resumen"]["porcentaje_conformidad"], 0)
        self.assertEqual(page.context["resumen"]["porcentaje_defectos"], 0)
