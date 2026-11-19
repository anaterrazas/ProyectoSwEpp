import json
from pathlib import Path
import shutil
import uuid
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from administracion.models import AreaTrabajo, Camara
from .fuentes import ROOT


class RevisionLaboratorioTests(TestCase):
    def setUp(self):
        self.root = ROOT / "output/tests" / uuid.uuid4().hex
        self.root.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, self.root)
        override = override_settings(MEDIA_ROOT=self.root, ROOT_URLCONF="experimentos.pilotos.urls")
        override.enable()
        self.addCleanup(override.disable)
        area = AreaTrabajo.objects.create(nombre="Área de prueba")
        self.camara = Camara.objects.create(nombre="Prueba funcional", area=area, tipo_monitoreo="EPP",
                                            archivo_video="videos/trabajadores.mp4")
        self.usuario = get_user_model().objects.create_user(username="revisor")
        self.usuario.user_permissions.set(Permission.objects.filter(content_type__app_label="seguridad"))
        self.cliente = Client(enforce_csrf_checks=True)
        self.cliente.force_login(self.usuario)
        self.ejecucion = uuid.uuid4()
        self.carpeta = self.root / f"resultados_ia/camara_{self.camara.pk}/{self.ejecucion.hex}"
        self.carpeta.mkdir(parents=True)
        self.ruta = self.carpeta / "reporte.json"
        # Fixture de interfaz: no es una predicción ni anotación para evaluar IA.
        self.ruta.write_text(json.dumps({"area": "Área de prueba", "eventos": [
            {"equipo": "CASCO", "track_id": "FIXTURE", "revision": "PENDIENTE", "evidencia": "ausente.jpg"}],
            "observaciones_por_estado": {"CUMPLE": 3, "NO_EVALUABLE": 1}}), encoding="utf-8")
        self.url = reverse("reporte_piloto", args=[self.camara.pk, self.ejecucion])

    def test_render_contexto_y_archivos_ausentes(self):
        r = self.cliente.get(self.url)
        self.assertContains(r, "Prueba funcional")
        self.assertContains(r, "75,00")
        self.assertNotContains(r, "{{")
        self.assertNotContains(r, "{%")
        self.assertContains(r, "Evidencia no disponible")
        self.assertContains(r, "No hay video procesado")
        self.assertContains(r, 'name="csrfmiddlewaretoken"')
        self.assertEqual(r.context["video_original_url"], "/media/videos/trabajadores.mp4")

    def test_csrf_historial_y_escapado(self):
        datos = {"evento": "0", "version": "0", "revision": "DESCARTADO", "nota": "<script>test</script>"}
        self.assertEqual(self.cliente.post(self.url, datos).status_code, 403)
        r = self.cliente.get(self.url)
        datos["csrfmiddlewaretoken"] = self.cliente.cookies[settings.CSRF_COOKIE_NAME].value
        self.assertEqual(self.cliente.post(self.url, datos).status_code, 302)
        self.assertContains(self.cliente.get(self.url), "&lt;script&gt;test&lt;/script&gt;")
        self.assertEqual(self.cliente.post(self.url, datos).status_code, 409)
        evento = json.loads(self.ruta.read_text(encoding="utf-8"))["eventos"][0]
        self.assertEqual(len(evento["historial"]), 1)
        self.assertEqual(evento["historial"][0]["usuario_id"], self.usuario.pk)

    def test_medios_autenticados_y_range(self):
        url = "/media/videos/trabajadores.mp4"
        self.assertEqual(Client().get(url).status_code, 302)
        r = self.cliente.get(url, HTTP_RANGE="bytes=0-127")
        self.assertEqual(r.status_code, 206)
        self.assertEqual(len(b"".join(r.streaming_content)), 128)
        self.assertEqual(r["Content-Type"], "video/mp4")
        self.assertEqual(self.cliente.get(url, HTTP_RANGE="bytes=999999999999-").status_code, 416)
        self.assertEqual(self.cliente.get("/media/../db.sqlite3").status_code, 404)

    def test_fuentes_no_se_sobrescriben(self):
        from .storage import FuentesStorage
        from django.core.files.base import ContentFile
        from django.core.exceptions import SuspiciousFileOperation
        with self.assertRaises(SuspiciousFileOperation):
            FuentesStorage().save("videos/trabajadores.mp4", ContentFile(b"no"))
        with self.assertRaises(SuspiciousFileOperation):
            FuentesStorage().delete("videos/trabajadores.mp4")

    def test_imagen_evidencia_existente(self):
        from PIL import Image
        Image.new("RGB", (20, 20), "white").save(self.carpeta / "fixture.jpg")
        datos = json.loads(self.ruta.read_text(encoding="utf-8"))
        datos["eventos"][0]["evidencia"] = "fixture.jpg"
        self.ruta.write_text(json.dumps(datos), encoding="utf-8")
        r = self.cliente.get(self.url)
        url = f"/media/resultados_ia/camara_{self.camara.pk}/{self.ejecucion.hex}/fixture.jpg"
        self.assertContains(r, f'src="{url}"')
        imagen = self.cliente.get(url)
        self.assertEqual(imagen.status_code, 200)
        self.assertEqual(imagen["Content-Type"], "image/jpeg")
        self.assertTrue(b"".join(imagen.streaming_content).startswith(b"\xff\xd8"))

    def test_permisos_y_calidad_sin_clasificacion(self):
        otro = get_user_model().objects.create_user(username="sin_permiso")
        self.cliente.force_login(otro)
        self.assertEqual(self.cliente.get(self.url).status_code, 403)
        self.assertEqual(self.cliente.get("/media/videos/trabajadores.mp4").status_code, 403)
        self.cliente.force_login(self.usuario)
        r = self.cliente.get("/calidad/")
        self.assertContains(r, "NO DISPONIBLE")
        self.assertContains(r, "<video", count=5)
