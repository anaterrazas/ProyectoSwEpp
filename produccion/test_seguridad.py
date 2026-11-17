from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from uuid import uuid4
import subprocess

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import ValidationError
from django.core.files import File
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.uploadhandler import StopUpload
from django.test import RequestFactory
from django.test import TestCase, SimpleTestCase, override_settings
from django.urls import reverse

from .admin import AnalisisAdminForm
from .forms import NuevoAnalisisForm
from .models import AnalisisProduccion, InspeccionCalidad, LoteProduccion, Producto
from .videos import validar_video
from .uploads import LimiteVideoUploadHandler


class PermisosProduccionTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(username="sin_permiso", is_staff=True)
        self.grupo = Group.objects.create(name="Supervisor")
        self.usuario.groups.add(self.grupo)
        self.lote = LoteProduccion.objects.create(codigo="SEG", producto=Producto.objects.create(nombre="Caja", tipo="CAJA"))
        self.analisis = AnalisisProduccion.objects.create(lote=self.lote, origen="MANUAL", estado="COMPLETADO", cantidad_contada=1)
        self.unidad = InspeccionCalidad.objects.create(analisis=self.analisis, identificador="1")
        self.urls = [reverse("crear_analisis"), reverse("procesar_analisis", args=[self.analisis.pk]),
                     reverse("clasificar_inspeccion", args=[self.analisis.pk, self.unidad.pk])]
        self.client.force_login(self.usuario)

    def permitir(self, *codigos):
        self.grupo.permissions.add(*Permission.objects.filter(content_type__app_label="produccion", codename__in=codigos))

    def test_staff_y_nombre_grupo_no_otorgan_autorizacion(self):
        for url in self.urls:
            self.assertEqual(self.client.post(url, {}).status_code, 403)
        self.assertEqual(self.client.get(self.urls[0]).status_code, 403)
        self.assertEqual(self.client.post(reverse("procesar_analisis", args=[9999])).status_code, 403)
        self.assertEqual(AnalisisProduccion.objects.count(), 1)
        self.unidad.refresh_from_db()
        self.assertEqual(self.unidad.resultado, "REVISION")
        self.assertEqual(self.client.get(reverse("admin:produccion_loteproduccion_add")).status_code, 403)

    def test_supervisor_con_permisos_del_grupo(self):
        self.permitir("add_analisisproduccion", "change_analisisproduccion", "change_inspeccioncalidad", "add_loteproduccion")
        self.assertEqual(self.client.get(self.urls[0]).status_code, 200)
        response = self.client.post(self.urls[0], {"lote": self.lote.pk, "cantidad": 2, "solicitud_manual": uuid4()})
        self.assertEqual(response.status_code, 302)
        with patch("produccion.views.YOLO") as yolo:
            self.assertEqual(self.client.post(self.urls[1]).status_code, 302)
            yolo.assert_not_called()
        self.assertEqual(self.client.post(self.urls[2], {f"unidad-{self.unidad.pk}-resultado": "CONFORME"}).status_code, 302)
        self.unidad.refresh_from_db()
        self.assertEqual(self.unidad.resultado, "CONFORME")
        self.assertEqual(self.client.get(reverse("admin:produccion_loteproduccion_add")).status_code, 200)

    def test_permiso_creacion_no_permite_procesar_o_clasificar(self):
        self.permitir("add_analisisproduccion")
        self.assertEqual(self.client.get(self.urls[0]).status_code, 200)
        for url in self.urls[1:]:
            self.assertEqual(self.client.post(url).status_code, 403)

    def test_superusuario_conserva_acceso(self):
        administrador = get_user_model().objects.create_superuser(username="admin", password="test-only")
        self.client.force_login(administrador)
        self.assertEqual(self.client.get(self.urls[0]).status_code, 200)
        self.assertEqual(self.client.post(self.urls[1]).status_code, 302)
        self.assertEqual(self.client.post(self.urls[2], {f"unidad-{self.unidad.pk}-resultado": "CONFORME"}).status_code, 302)
        self.assertEqual(self.client.get(reverse("admin:produccion_loteproduccion_add")).status_code, 200)

    def test_formulario_rechaza_archivo_disfrazado_sin_crear_analisis(self):
        self.permitir("add_analisisproduccion")
        self.lote.producto.tipo = "BOTELLA"
        self.lote.producto.save()
        response = self.client.post(self.urls[0], {"lote": self.lote.pk, "video_original": SimpleUploadedFile("video.mp4", b"<script>bad</script>", content_type="video/mp4")})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(AnalisisProduccion.objects.count(), 1)

    def test_archivo_guardado_invalido_no_llega_a_yolo(self):
        self.permitir("change_analisisproduccion")
        self.lote.producto.tipo = "BOTELLA"
        self.lote.producto.save()
        self.analisis.origen = "IA"
        self.analisis.video_original = "inexistente.mp4"
        self.analisis.save()
        with patch("produccion.views.YOLO") as yolo:
            self.assertEqual(self.client.post(self.urls[1]).status_code, 302)
            yolo.assert_not_called()
        self.analisis.refresh_from_db()
        self.assertEqual(self.analisis.estado, "COMPLETADO")

    def test_carga_video_real_autorizada(self):
        self.permitir("add_analisisproduccion")
        self.lote.producto.tipo = "BOTELLA"
        self.lote.producto.save()
        with TemporaryDirectory() as temporal, override_settings(MEDIA_ROOT=temporal):
            with (Path(settings.BASE_DIR) / "pruebas_ia/produccion.mp4").open("rb") as video:
                response = self.client.post(self.urls[0], {"lote": self.lote.pk, "video_original": video})
            self.assertEqual(response.status_code, 302)
            nuevo = AnalisisProduccion.objects.exclude(pk=self.analisis.pk).get()
            self.assertEqual(nuevo.estado, "PENDIENTE")
            self.assertTrue(Path(nuevo.video_original.path).exists())


class ValidacionVideoTests(SimpleTestCase):
    def test_corte_de_carga_solo_en_produccion(self):
        for ruta in ("/produccion/nuevo/", "/admin/produccion/analisisproduccion/add/"):
            handler = LimiteVideoUploadHandler(RequestFactory().post(ruta))
            with patch("produccion.uploads.MAX_BYTES", 5):
                self.assertEqual(handler.receive_data_chunk(b"123", 0), b"123")
                with self.assertRaises(StopUpload):
                    handler.receive_data_chunk(b"456", 3)
        handler = LimiteVideoUploadHandler(RequestFactory().post("/monitoreo/"))
        with patch("produccion.uploads.MAX_BYTES", 1):
            self.assertEqual(handler.receive_data_chunk(b"123", 0), b"123")

    def archivo(self, nombre="video.mp4", contenido=b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 20):
        return SimpleUploadedFile(nombre, contenido, content_type="video/mp4")

    def test_video_real_y_cursor(self):
        with (Path(settings.BASE_DIR) / "pruebas_ia/produccion.mp4").open("rb") as origen:
            archivo = File(origen)
            archivo.seek(4)
            validar_video(archivo)
            self.assertEqual(archivo.tell(), 4)

    def test_extension_firma_vacio_y_tamano(self):
        for archivo in [self.archivo("video.html"), self.archivo(contenido=b"bad"), self.archivo(contenido=b"")]:
            with self.assertRaises(ValidationError):
                validar_video(archivo)
        with patch("produccion.videos.MAX_BYTES", 10), self.assertRaises(ValidationError):
            validar_video(self.archivo())

    def test_limites_y_codec_antes_de_decodificar(self):
        for texto in ["Duration: 00:02:01.00 Video: h264, yuv420p, 1280x720, 50 fps",
                      "Duration: 00:00:08.00 Video: h264, yuv420p, 3840x2160, 50 fps",
                      "Duration: 00:00:08.00 Video: h264, yuv420p, 1280x720, 120 fps",
                      "Duration: 00:00:08.00 Video: hevc, yuv420p, 1280x720, 50 fps"]:
            with patch("produccion.videos._ejecutar", return_value=subprocess.CompletedProcess([], 1, "", texto)) as ejecutar:
                with self.assertRaises(ValidationError):
                    validar_video(self.archivo())
                self.assertEqual(ejecutar.call_count, 1)

    def test_timeout_y_video_corrupto(self):
        with patch("produccion.videos._ejecutar", side_effect=subprocess.TimeoutExpired("ffmpeg", 10)):
            with self.assertRaises(ValidationError):
                validar_video(self.archivo())
        with self.assertRaises(ValidationError):
            validar_video(self.archivo())

    def test_rechaza_fallo_decodificacion_y_tiempo_real_excesivo(self):
        info = subprocess.CompletedProcess([], 1, "", "Duration: 00:00:08.00 Video: h264, yuv420p, 1280x720, 50 fps")
        for resultado in [subprocess.CompletedProcess([], 1, "", "dañado"),
                          subprocess.CompletedProcess([], 0, "frame=8000\nout_time_us=121000000", ""),
                          subprocess.CompletedProcess([], 0, "frame=0\nout_time_us=0", "")]:
            with patch("produccion.videos._ejecutar", side_effect=[info, resultado]):
                with self.assertRaises(ValidationError):
                    validar_video(self.archivo())

    def test_admin_tambien_valida_video(self):
        form = AnalisisAdminForm(files={"video_original": self.archivo(contenido=b"bad")})
        self.assertFalse(form.is_valid())
        self.assertIn("video_original", form.errors)
