import csv
import io
from uuid import uuid4
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .models import AnalisisProduccion, CriterioCalidad, InspeccionCalidad, LoteProduccion, Producto


from .test_support import autorizar_supervisor


class RegistroManualTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(username="manual")
        autorizar_supervisor(self.usuario)
        self.client.force_login(self.usuario)
        self.lotes = {}
        for tipo in Producto.Tipo.values:
            producto = Producto.objects.create(nombre=tipo, tipo=tipo)
            self.lotes[tipo] = LoteProduccion.objects.create(producto=producto, codigo=tipo)
        self.url = reverse("crear_analisis")

    def registrar(self, tipo="CAJA", cantidad=10, token=None):
        return self.client.post(self.url, {
            "lote": self.lotes[tipo].pk, "cantidad": cantidad,
            "solicitud_manual": token or uuid4(),
        })

    def clasificar(self, unidad, resultado, criterio=""):
        return self.client.post(reverse("clasificar_inspeccion", args=[unidad.analisis_id, unidad.pk]), {
            f"unidad-{unidad.pk}-resultado": resultado,
            f"unidad-{unidad.pk}-criterio": criterio,
            f"unidad-{unidad.pk}-observacion": "Evaluada por supervisor",
        })

    def test_diez_cajas_y_diez_bolsas_sin_ia_ni_video(self):
        for tipo in ("CAJA", "BOLSA"):
            with self.subTest(tipo=tipo), patch("produccion.views.YOLO") as yolo:
                response = self.registrar(tipo)
                self.assertEqual(response.status_code, 302)
                a = AnalisisProduccion.objects.get(lote=self.lotes[tipo])
                self.assertEqual((a.origen, a.estado, a.cantidad_contada), ("MANUAL", "COMPLETADO", 10))
                self.assertFalse(a.video_original)
                self.assertFalse(a.video_procesado)
                self.assertEqual(a.inspecciones.count(), 10)
                self.assertEqual(set(a.inspecciones.values_list("identificador", flat=True)), {str(i) for i in range(1, 11)})
                self.assertEqual(a.inspecciones.filter(resultado="REVISION", criterio=None, confianza=None).count(), 10)
                lote = self.lotes[tipo]; lote.refresh_from_db()
                self.assertEqual((lote.cantidad_producida, lote.cantidad_conforme, lote.cantidad_defectuosa, lote.estado), (10, 0, 0, "EN_PROCESO"))
                pagina = self.client.get(response.url)
                self.assertEqual(pagina.status_code, 200)
                self.assertContains(pagina, "Registro manual")
                self.assertNotContains(pagina, "<video")
                self.assertNotContains(pagina, "Analizar video con IA")
                self.client.post(reverse("procesar_analisis", args=[a.pk]))
                yolo.assert_not_called()
                a.refresh_from_db()
                self.assertEqual(a.estado, "COMPLETADO")

    def test_clasificacion_y_finalizacion_reutiliza_cu10(self):
        for tipo in ("CAJA", "BOLSA"):
            self.registrar(tipo)
            a = AnalisisProduccion.objects.get(lote=self.lotes[tipo])
            unidades = list(a.inspecciones.order_by("pk"))
            criterio = CriterioCalidad.objects.create(producto=self.lotes[tipo].producto, nombre="Sin roturas")
            self.assertEqual(self.clasificar(unidades[0], "CONFORME").status_code, 302)
            self.assertEqual(self.clasificar(unidades[1], "DEFECTUOSO", criterio.pk).status_code, 302)
            self.assertEqual(self.clasificar(unidades[2], "REVISION").status_code, 302)
            lote = self.lotes[tipo]; lote.refresh_from_db()
            self.assertEqual((lote.cantidad_producida, lote.cantidad_conforme, lote.cantidad_defectuosa, lote.estado), (10, 1, 1, "EN_PROCESO"))
            for unidad in unidades[2:]:
                self.clasificar(unidad, "CONFORME")
            lote.refresh_from_db()
            self.assertEqual((lote.cantidad_conforme, lote.cantidad_defectuosa, lote.estado), (9, 1, "FINALIZADO"))

    def test_criterios_invalidos_no_cambian_la_inspeccion(self):
        self.registrar()
        a = AnalisisProduccion.objects.get()
        unidad = a.inspecciones.first()
        otro = CriterioCalidad.objects.create(producto=self.lotes["BOLSA"].producto, nombre="Ajeno")
        inactivo = CriterioCalidad.objects.create(producto=a.lote.producto, nombre="Inactivo", activo=False)
        for criterio in ("", otro.pk, inactivo.pk):
            self.assertEqual(self.clasificar(unidad, "DEFECTUOSO", criterio).status_code, 400)
            unidad.refresh_from_db()
            self.assertEqual(unidad.resultado, "REVISION")

    def test_reenvio_no_duplica_y_nueva_medicion_conserva_historia(self):
        token = uuid4()
        primera = self.registrar(token=token)
        a = AnalisisProduccion.objects.get()
        unidad = a.inspecciones.first()
        self.clasificar(unidad, "CONFORME")
        ids = list(a.inspecciones.order_by("pk").values_list("pk", flat=True))
        self.assertEqual(self.registrar(token=token).url, primera.url)
        self.assertEqual(AnalisisProduccion.objects.count(), 1)
        self.assertEqual(list(a.inspecciones.order_by("pk").values_list("pk", flat=True)), ids)
        self.assertEqual(self.registrar(cantidad=11, token=token).status_code, 400)
        self.assertEqual(self.registrar("BOLSA", token=token).status_code, 400)
        self.registrar(cantidad=3)
        self.assertEqual(AnalisisProduccion.objects.count(), 2)
        unidad.refresh_from_db()
        self.assertEqual(unidad.resultado, "CONFORME")
        lote = self.lotes["CAJA"]; lote.refresh_from_db()
        self.assertEqual(lote.cantidad_producida, 3)
        # Volver a enviar un formulario anterior no lo convierte en vigente.
        self.registrar(token=token)
        lote.refresh_from_db(); self.assertEqual(lote.cantidad_producida, 3)
        self.clasificar(unidad, "REVISION")
        lote.refresh_from_db(); self.assertEqual(lote.cantidad_producida, 3)

    def test_cu11_filtros_porcentajes_y_exportacion_manual(self):
        self.registrar("CAJA")
        self.registrar("BOLSA")
        a = AnalisisProduccion.objects.get(lote=self.lotes["CAJA"])
        self.clasificar(a.inspecciones.first(), "CONFORME")
        page = self.client.get(reverse("panel_resultados"), {"tipo": "CAJA"})
        self.assertEqual((page.context["resumen"]["total"], page.context["resumen"]["pendientes"]), (10, 9))
        self.assertEqual(page.context["resumen"]["porcentaje_conformidad"], 10)
        self.assertContains(page, "Registro manual")
        self.assertEqual(self.client.get(reverse("detalle_lote", args=[a.lote_id])).status_code, 200)
        export = self.client.get(reverse("descargar_resultados"), {"tipo": "CAJA"})
        filas = list(csv.DictReader(io.StringIO(export.content.decode("utf-8-sig")), delimiter=";"))
        self.assertTrue(all(f["Origen unidades"] == "Registro manual" for f in filas))
        self.assertTrue(all(f["Tipo producto"] == "Cajas" for f in filas))
        self.assertEqual(len([f for f in filas if f["Tipo"] == "INSPECCION"]), 10)

    def test_cantidades_e_identificadores_invalidos(self):
        for valor in (0, -1, "", "texto", "1.5", 10001):
            self.assertEqual(self.registrar(cantidad=valor).status_code, 400)
        self.assertEqual(self.client.post(self.url, {"lote": "abc", "cantidad": 10}).status_code, 400)
        self.assertEqual(self.client.post(self.url, {"lote": 99999, "cantidad": 10}).status_code, 400)
        self.assertEqual(self.client.post(self.url, {"lote": self.lotes["CAJA"].pk, "cantidad": 10}).status_code, 400)
        self.assertEqual(AnalisisProduccion.objects.count(), 0)

    def test_botellas_siguen_exigiendo_video(self):
        self.assertEqual(self.registrar("BOTELLA").status_code, 400)
        self.assertEqual(AnalisisProduccion.objects.count(), 0)

    def test_atomicidad_autenticacion_y_csrf(self):
        with patch("produccion.views.InspeccionCalidad.objects.bulk_create", side_effect=RuntimeError("fallo")):
            with self.assertRaises(RuntimeError):
                self.registrar()
        self.assertEqual(AnalisisProduccion.objects.count(), 0)
        self.assertEqual(InspeccionCalidad.objects.count(), 0)
        self.lotes["CAJA"].refresh_from_db()
        self.assertEqual(self.lotes["CAJA"].cantidad_producida, 0)
        self.assertEqual(Client().post(self.url).status_code, 302)
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.usuario)
        self.assertEqual(cliente.post(self.url).status_code, 403)
