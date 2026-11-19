"""Regresiones del acceso a artefactos y separación de módulos, sin IA."""
import json
import uuid
import shutil
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, TestCase, override_settings
from .catalogo import LAB, ROOT


@override_settings(ROOT_URLCONF="experimentos.pilotos.urls")
class PortalTests(TestCase):
    def setUp(self):
        self.user=get_user_model().objects.create_user(username="demo")
        self.user.user_permissions.set(Permission.objects.filter(codename__in=["view_deteccionepp","view_analisisproduccion"]))
        self.client.force_login(self.user)
        self.artefacto="/artefactos/"+LAB+"comparacion_videos_epp_v002_001/index.html"

    def test_autenticacion_y_solo_lectura(self):
        for url in ["/","/demo/epp/","/demo/calidad/","/demo/historial/",self.artefacto]:
            self.assertEqual(Client().get(url).status_code,302)
            self.assertEqual(self.client.post(url).status_code,405)

    def test_portal_y_metricas_separadas(self):
        self.assertContains(self.client.get("/"),"Inspección inteligente")
        epp=self.client.get("/demo/epp/")
        self.assertContains(epp,"72,88 %")
        self.assertContains(epp,"CHALECO 0,15")
        calidad=self.client.get("/demo/calidad/")
        self.assertContains(calidad,"Sin detector evaluado")
        self.assertContains(calidad,"NO DISPONIBLE")
        self.assertContains(calidad,"71,74 %")
        self.assertNotContains(calidad,"72,88 %")

    def test_retorno_desde_pantallas_existentes(self):
        self.assertContains(self.client.get("/monitoreo/"),"Plataforma de demostración")
        self.assertContains(self.client.get("/calidad/"),"Plataforma de demostración")

    def test_permisos_independientes(self):
        self.user.user_permissions.set(Permission.objects.filter(codename="view_analisisproduccion"))
        self.assertEqual(self.client.get("/demo/epp/").status_code,403)
        self.assertEqual(self.client.get(self.artefacto).status_code,403)
        self.assertEqual(self.client.get("/demo/calidad/").status_code,200)
        self.assertEqual(self.client.get("/media/fuentes/prueba2.mp4",HTTP_RANGE="bytes=0-15").status_code,206)
        self.assertEqual(self.client.get("/media/videos/trabajadores.mp4").status_code,403)
        self.assertContains(self.client.get("/demo/historial/"),"Simulación con abstención")
        self.assertNotContains(self.client.get("/demo/historial/"),"Base temporal")
        self.user.user_permissions.clear()
        self.assertEqual(self.client.get("/demo/calidad/").status_code,403)

    def test_rutas_no_permitidas(self):
        for nombre in ["db.sqlite3","config/settings.py","output/experimental_pilotos/acceso_local.json",LAB+"laboratorio.sqlite3",LAB+"comparacion_videos_epp_v002_001/../../acceso_local.json",LAB+"comparacion_videos_epp_v002_001/protegidos_antes.json","C:/Windows/win.ini","docs/DEPURACION.md"]:
            self.assertEqual(self.client.get("/artefactos/"+nombre).status_code,404,nombre)

    @override_settings(DEBUG=False)
    def test_errores_sin_rutas_y_estaticos_login(self):
        r=self.client.get("/artefactos/config/settings.py")
        self.assertNotContains(r,str(ROOT),status_code=404)
        r=Client().get("/static/admin/css/login.css")
        self.assertEqual(r.status_code,200)
        r.close()

    def test_enlace_fuera_de_raiz(self):
        from .artefactos import resolver
        from django.http import Http404
        from pathlib import Path
        original=Path.resolve
        # Simula el destino real de un enlace, sin privilegios symlink Windows.
        def destino(path,*args,**kwargs):
            return ROOT/"db.sqlite3" if path.name=="index.html" else original(path,*args,**kwargs)
        with patch.object(Path,"resolve",destino):
            with self.assertRaises(Http404):
                resolver(LAB+"comparacion_videos_epp_v002_001/index.html")

    def test_galeria_y_range(self):
        r=self.client.get(self.artefacto)
        self.assertContains(r,"33 referencias")
        self.assertIn("sandbox",r["Content-Security-Policy"])
        url="/artefactos/"+LAB+"comparacion_videos_epp_v002_001/epp_corto_base_vs_candidata.mp4"
        r=self.client.get(url,HTTP_RANGE="bytes=0-127")
        self.assertEqual(r.status_code,206)
        self.assertEqual(len(b"".join(r.streaming_content)),128)
        self.assertEqual(r["Content-Type"],"video/mp4")
        self.assertEqual(self.client.get(url,HTTP_RANGE="bytes=999999999999-").status_code,416)

    def test_informes_sin_rutas_absolutas(self):
        url="/artefactos/"+LAB+"seguridad_epp_v002_001/modelos_y_parametros.json"
        r=self.client.get(url)
        self.assertEqual(r.status_code,200)
        self.assertNotContains(r,"C:\\Users")
        from .artefactos import ocultar_rutas
        texto=ocultar_rutas(str(ROOT)+"/video.mp4 "+json.dumps(str(ROOT))+" D:/privado/pesos.pt")
        self.assertNotIn("C:",texto)
        self.assertNotIn("D:",texto)

    def test_historial_escapa_notas_sin_escritura(self):
        carpeta=ROOT/"output/tests"/uuid.uuid4().hex
        reporte=carpeta/"resultados_ia/camara_1/run/reporte.json"
        reporte.parent.mkdir(parents=True)
        self.addCleanup(shutil.rmtree,carpeta)
        reporte.write_text(json.dumps({"eventos":[{"equipo":"CASCO","historial":[{"usuario":"revisor","decision":"DESCARTADO","nota":"<script>alert(1)</script>"}]}]}),encoding="utf-8")
        original=reporte.read_bytes()
        with override_settings(MEDIA_ROOT=carpeta):
            self.assertContains(self.client.get("/demo/historial/"),"&lt;script&gt;alert(1)&lt;/script&gt;")
        self.assertEqual(original,reporte.read_bytes())
