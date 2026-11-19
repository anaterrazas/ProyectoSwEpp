import json
import uuid
import shutil
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import cv2
import numpy as np
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files import File
from django.test import TestCase, override_settings
from django.urls import reverse

from administracion.models import AreaTrabajo, Camara, EquipoProteccion


class PilotoWebTests(TestCase):
    def setUp(self):
        carpeta = Path(__file__).resolve().parents[1] / "output" / "tests" / uuid.uuid4().hex
        carpeta.mkdir(parents=True)
        self.temp = SimpleNamespace(name=str(carpeta))
        self.addCleanup(shutil.rmtree, carpeta)
        override = override_settings(MEDIA_ROOT=self.temp.name)
        override.enable()
        self.addCleanup(override.disable)
        self.usuario = get_user_model().objects.create_user(username="supervisor")
        self.usuario.user_permissions.set(Permission.objects.filter(content_type__app_label="seguridad"))
        self.client.force_login(self.usuario)
        self.area = AreaTrabajo.objects.create(nombre="Área piloto")
        self.area.equipos_obligatorios.add(EquipoProteccion.objects.create(nombre="Casco"))
        self.camara = Camara.objects.create(nombre="Piloto", area=self.area,
                                            tipo_monitoreo="EPP", tipo_fuente="VIDEO")

    def reporte(self):
        ejecucion = uuid.uuid4()
        carpeta = Path(self.temp.name) / f"resultados_ia/camara_{self.camara.pk}/{ejecucion.hex}"
        carpeta.mkdir(parents=True)
        ruta = carpeta / "reporte.json"
        ruta.write_text(json.dumps({"eventos": [{"revision": "PENDIENTE"}]}), encoding="utf-8")
        return reverse("reporte_piloto", args=[self.camara.pk, ejecucion]), ruta

    def test_revision_con_historial_y_conflicto(self):
        url, ruta = self.reporte()
        self.assertEqual(self.client.get(url).status_code, 200)
        datos = {"evento": "0", "revision": "DESCARTADO", "nota": "Reflejo", "version": "0"}
        self.assertEqual(self.client.post(url, datos).status_code, 302)
        evento = json.loads(ruta.read_text(encoding="utf-8"))["eventos"][0]
        self.assertEqual(evento["historial"][0]["usuario_id"], self.usuario.pk)
        self.assertEqual(evento["revision"], "DESCARTADO")
        self.assertEqual(self.client.post(url, datos).status_code, 409)
        self.assertEqual(len(json.loads(ruta.read_text())["eventos"][0]["historial"]), 1)

    def test_permisos_revision(self):
        url, _ = self.reporte()
        otro = get_user_model().objects.create_user(username="lector")
        otro.user_permissions.add(Permission.objects.get(codename="view_deteccionepp"))
        self.client.force_login(otro)
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.post(url, {}).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code, 302)

    def test_area_sin_reglas_no_inicia_modelos(self):
        self.area.equipos_obligatorios.clear()
        with patch("monitoreo.views.YOLO") as modelo:
            self.assertEqual(self.client.post(reverse("analizar_camara", args=[self.camara.pk])).status_code, 302)
            modelo.assert_not_called()

    def test_video_y_reporte_con_inferencia_simulada(self):
        fuente = Path(self.temp.name) / "fuente.mp4"
        writer = cv2.VideoWriter(str(fuente), cv2.VideoWriter_fourcc(*"mp4v"), 2, (100, 200))
        self.assertTrue(writer.isOpened())
        imagen = np.zeros((200, 100, 3), dtype=np.uint8)
        for _ in range(6):
            writer.write(imagen)
        writer.release()
        with fuente.open("rb") as archivo:
            self.camara.archivo_video.save("piloto.mp4", File(archivo))
        caja = SimpleNamespace(cls=[0], conf=[.9], xyxy=np.array([[20, 0, 70, 35]]))
        resultado = SimpleNamespace(boxes=[caja], orig_img=imagen, plot=lambda: imagen.copy())
        persona = SimpleNamespace(id=SimpleNamespace(item=lambda: 1), xyxy=np.array([[0, 0, 100, 200]]))
        class Cajas(list):
            id = True
        modelo = SimpleNamespace(names={0: "NO-Hardhat"}, predict=lambda **kw: iter([resultado] * 6))
        personas = SimpleNamespace(track=lambda *a, **kw: [SimpleNamespace(boxes=Cajas([persona]))])
        with patch("monitoreo.views.YOLO", side_effect=[modelo, personas]):
            respuesta = self.client.post(reverse("analizar_camara", args=[self.camara.pk]))
        self.assertEqual(respuesta.status_code, 302)
        ejecucion = self.client.session[f"piloto_{self.camara.pk}"]
        url = reverse("reporte_piloto", args=[self.camara.pk, ejecucion])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertContains(self.client.get(reverse("lista_camaras")), url)
        carpeta = Path(self.temp.name) / f"resultados_ia/camara_{self.camara.pk}/{uuid.UUID(ejecucion).hex}"
        datos = json.loads((carpeta / "reporte.json").read_text(encoding="utf-8"))
        self.assertEqual(len(datos["eventos"]), 1)
        self.assertEqual(datos["eventos"][0]["revision"], "PENDIENTE")
        self.assertTrue((carpeta / datos["eventos"][0]["evidencia"]).is_file())
        video = cv2.VideoCapture(str(carpeta / "resultado_epp.mp4"))
        self.assertTrue(video.isOpened())
        self.assertEqual(int(video.get(cv2.CAP_PROP_FRAME_COUNT)), 6)
        video.release()
