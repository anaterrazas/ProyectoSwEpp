import csv
import io

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from .models import AnalisisProduccion, InspeccionCalidad, LoteProduccion, Producto


from .test_support import autorizar_supervisor


class ConsultasResultadosTests(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_user(username="consulta"))
        self.producto = Producto.objects.create(nombre="Producto configurable")
        self.lote = LoteProduccion.objects.create(
            producto=self.producto, codigo="LOTE-A", cantidad_producida=999,
            cantidad_conforme=999, estado="FINALIZADO",
        )
        self.anterior = self.crear_analisis(self.lote, ["CONFORME"] * 8)
        self.vigente = self.crear_analisis(self.lote, ["CONFORME", "DEFECTUOSO", "REVISION", "REVISION"])
        self.error = self.crear_analisis(self.lote, ["CONFORME"] * 10, estado="ERROR")
        self.otro = LoteProduccion.objects.create(producto=self.producto, codigo="LOTE-B")
        self.crear_analisis(self.otro, ["CONFORME", "CONFORME"])
        self.sin_analisis = LoteProduccion.objects.create(
            producto=self.producto, codigo="SIN-ANALISIS", cantidad_producida=20
        )

    def crear_analisis(self, lote, resultados, estado="COMPLETADO"):
        a = AnalisisProduccion.objects.create(
            lote=lote, estado=estado, cantidad_contada=len(resultados),
            video_original="produccion/videos/prueba.mp4",
        )
        InspeccionCalidad.objects.bulk_create([
            InspeccionCalidad(analisis=a, identificador=str(n), resultado=r,
                             observacion="Observacion historica")
            for n, r in enumerate(resultados)
        ])
        return a

    def test_panel_solo_suma_vigentes_y_no_modifica_datos(self):
        with CaptureQueriesContext(connection) as consultas:
            response = self.client.get(reverse("panel_resultados"))
        self.assertEqual(response.status_code, 200)
        resumen = response.context["resumen"]
        self.assertEqual((resumen["total"], resumen["conformes"], resumen["defectuosas"], resumen["pendientes"]), (6, 3, 1, 2))
        self.assertEqual(resumen["porcentaje_conformidad"], 50)
        self.assertAlmostEqual(resumen["porcentaje_defectos"], 100 / 6)
        self.assertEqual(response.context["total_lotes"], 3)
        self.assertEqual(response.context["con_resultados"], 2)
        self.assertContains(response, "Distribución de calidad")
        self.assertContains(response, "Producción por lote")
        self.assertTrue(all(q["sql"].lstrip().upper().startswith("SELECT") for q in consultas))
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.cantidad_producida, 999)
        self.assertEqual(self.lote.cantidad_conforme, 999)

    def test_detalle_historico_y_separacion(self):
        response = self.client.get(reverse("detalle_lote", args=[self.lote.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["vigente"].pk, self.vigente.pk)
        self.assertEqual(response.context["resumen"]["total"], 4)
        self.assertEqual(len(response.context["analisis"]), 3)
        for a in (self.anterior, self.vigente, self.error):
            self.assertContains(response, reverse("resultado_analisis", args=[a.pk]))
        response = self.client.get(reverse("resultado_analisis", args=[self.anterior.pk]))
        self.assertContains(response, "Observacion historica")
        self.assertEqual(self.anterior.inspecciones.count(), 8)
        self.assertEqual(self.client.get(reverse("detalle_lote", args=[99999])).status_code, 404)

    def test_datos_antiguos_sin_inspecciones_y_cero(self):
        a = AnalisisProduccion.objects.create(lote=self.sin_analisis, cantidad_contada=5, estado="COMPLETADO")
        response = self.client.get(reverse("panel_resultados"))
        self.assertEqual(response.context["resumen"]["sin_registro"], 5)
        self.assertEqual(response.context["resumen"]["pendientes"], 2)
        self.assertContains(response, "no tienen registro de inspección")
        vacio = LoteProduccion.objects.create(producto=self.producto, codigo="VACIO")
        self.crear_analisis(vacio, [])
        response = self.client.get(reverse("detalle_lote", args=[vacio.pk]))
        self.assertEqual(response.context["resumen"]["porcentaje_conformidad"], 0)
        self.assertEqual(response.context["resumen"]["porcentaje_defectos"], 0)
        self.assertEqual(a.inspecciones.count(), 0)

    def test_exportacion_global_lote_y_formulas(self):
        inspeccion = self.vigente.inspecciones.first()
        inspeccion.observacion = '=HYPERLINK("ejemplo")\nObservacion con ; separador'
        inspeccion.save()
        url = reverse("descargar_resultados_lote", args=[self.lote.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response["Content-Disposition"])
        filas = list(csv.DictReader(io.StringIO(response.content.decode("utf-8-sig")), delimiter=";"))
        actuales = [f for f in filas if f["Tipo"] == "LOTE_ACTUAL"]
        self.assertEqual(len(actuales), 1)
        self.assertEqual(actuales[0]["Producidas"], "4")
        self.assertEqual(actuales[0]["Pendientes"], "2")
        historial = [f for f in filas if f["Tipo"] == "ANALISIS"]
        self.assertEqual(len(historial), 3)
        self.assertEqual(sum(f["Vigente"] == "Si" for f in historial), 1)
        self.assertEqual(len([f for f in filas if f["Tipo"] == "INSPECCION"]), 22)
        self.assertTrue(any(f["Observaciones"].startswith("'=HYPERLINK") for f in filas if f["Observaciones"]))
        self.assertTrue(all(f["Lote"] == "LOTE-A" for f in filas))
        global_csv = self.client.get(reverse("descargar_resultados"))
        self.assertContains(global_csv, "LOTE-B")
        self.assertEqual(self.client.get(reverse("descargar_resultados_lote", args=[99999])).status_code, 404)
        inspeccion.refresh_from_db()
        self.assertTrue(inspeccion.observacion.startswith("=HYPERLINK"))

    def test_autenticacion_y_consultas_sin_post(self):
        urls = [reverse("panel_resultados"), reverse("detalle_lote", args=[self.lote.pk]),
                reverse("descargar_resultados"), reverse("descargar_resultados_lote", args=[self.lote.pk])]
        anonimo = Client()
        for url in urls:
            self.assertEqual(anonimo.get(url).status_code, 302)
            self.assertEqual(self.client.post(url).status_code, 405)

    def test_consultas_no_crecen_por_lote_y_paginacion(self):
        with CaptureQueriesContext(connection) as queries:
            self.client.get(reverse("panel_resultados"))
        inicial = len(queries)
        for n in range(22):
            lote = LoteProduccion.objects.create(producto=self.producto, codigo=f"EXTRA-{n}")
            self.crear_analisis(lote, ["REVISION"])
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(reverse("panel_resultados"))
        self.assertEqual(len(queries), inicial)
        self.assertEqual(len(response.context["pagina"]), 20)
        response = self.client.get(reverse("panel_resultados"), {"page": 2})
        self.assertEqual(len(response.context["pagina"]), 5)
        self.assertEqual(response.context["resumen"]["total"], 28)

    def test_filtros_por_tipo_indicadores_graficos_y_csv(self):
        caja = Producto.objects.create(nombre="Caja de carton", tipo=Producto.Tipo.CAJA)
        bolsa = Producto.objects.create(nombre="Bolsa industrial", tipo=Producto.Tipo.BOLSA)
        lote_caja = LoteProduccion.objects.create(producto=caja, codigo="CAJAS")
        lote_bolsa = LoteProduccion.objects.create(producto=bolsa, codigo="BOLSAS")
        self.crear_analisis(lote_caja, ["CONFORME", "REVISION", "REVISION"])
        self.crear_analisis(lote_bolsa, ["DEFECTUOSO"])
        for tipo, total, conformes, defectos, pendientes in (
            ("BOTELLA", 6, 3, 1, 2), ("CAJA", 3, 1, 0, 2), ("BOLSA", 1, 0, 1, 0),
        ):
            with self.subTest(tipo=tipo):
                response = self.client.get(reverse("panel_resultados"), {"tipo": tipo})
                self.assertEqual(response.status_code, 200)
                r = response.context["resumen"]
                self.assertEqual((r["total"], r["conformes"], r["defectuosas"], r["pendientes"]),
                                 (total, conformes, defectos, pendientes))
                self.assertTrue(all(f["lote"].producto.tipo == tipo for f in response.context["pagina"]))
                self.assertEqual(sum(b["total"] for b in response.context["grafico"]), total)
                self.assertContains(response, f'?tipo={tipo}')
                csv_response = self.client.get(reverse("descargar_resultados"), {"tipo": tipo})
                filas = list(csv.DictReader(io.StringIO(csv_response.content.decode("utf-8-sig")), delimiter=";"))
                self.assertTrue(filas)
                self.assertTrue(all(f["Tipo producto"] == Producto.Tipo(tipo).label for f in filas))
        general = self.client.get(reverse("panel_resultados"))
        self.assertEqual(general.context["resumen"]["total"], 10)
        self.assertEqual(self.client.get(reverse("panel_resultados"), {"tipo": "OTRO"}).status_code, 400)
        self.assertEqual(self.client.get(reverse("descargar_resultados"), {"tipo": "OTRO"}).status_code, 400)
        self.assertEqual(self.client.get(reverse("descargar_resultados_lote", args=[lote_caja.pk]), {"tipo": "BOLSA"}).status_code, 404)

    def test_filtro_vacio_y_paginacion_conserva_tipo(self):
        response = self.client.get(reverse("panel_resultados"), {"tipo": "BOLSA"})
        self.assertEqual(response.context["resumen"]["total"], 0)
        self.assertEqual(response.context["resumen"]["porcentaje_conformidad"], 0)
        for n in range(21):
            LoteProduccion.objects.create(producto=self.producto, codigo=f"PAG-{n}")
        response = self.client.get(reverse("panel_resultados"), {"tipo": "BOTELLA"})
        self.assertContains(response, '?tipo=BOTELLA&amp;page=2')
        response = self.client.get(reverse("panel_resultados"), {"tipo": "BOTELLA", "page": 2})
        self.assertEqual(response.context["pagina"].number, 2)


class TiposYDetectoresTests(TestCase):
    def test_solo_tres_tipos_validos(self):
        from django.core.exceptions import ValidationError
        from django.db import IntegrityError, transaction
        self.assertEqual(Producto.Tipo.values, ["BOTELLA", "CAJA", "BOLSA"])
        for tipo in Producto.Tipo.values:
            Producto(nombre=f"Producto {tipo}", tipo=tipo).full_clean()
        with self.assertRaises(ValidationError):
            Producto(nombre="No permitido", tipo="OTRO").full_clean()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Producto.objects.create(nombre="No permitido", tipo="OTRO")

    def test_detector_botellas_conserva_parametros_y_otros_no_tienen_fallback(self):
        from .detectores import detector_para_producto
        from unittest.mock import patch
        botella = Producto.objects.create(nombre="Botella", tipo="BOTELLA")
        config = detector_para_producto(botella)
        self.assertEqual((config.pesos, config.clases, config.confianza, config.tamano),
                         ("yolo11n.pt", (39,), 0.30, 640))
        self.client.force_login(autorizar_supervisor(get_user_model().objects.create_user(username="detector")))
        for tipo in ("CAJA", "BOLSA"):
            producto = Producto.objects.create(nombre=tipo, tipo=tipo)
            with self.assertRaises(ValueError):
                detector_para_producto(producto)
            lote = LoteProduccion.objects.create(producto=producto, codigo=tipo)
            a = AnalisisProduccion.objects.create(lote=lote, video_original="no_procesar.mp4")
            with patch("produccion.views.YOLO") as modelo:
                response = self.client.post(reverse("procesar_analisis", args=[a.pk]))
                modelo.assert_not_called()
            self.assertEqual(response.status_code, 302)
            a.refresh_from_db()
            self.assertEqual(a.estado, "PENDIENTE")
            self.assertEqual(a.inspecciones.count(), 0)

    def test_criterios_independientes_por_producto(self):
        from .forms import ClasificacionCalidadForm
        from .models import CriterioCalidad
        for tipo in Producto.Tipo.values:
            producto = Producto.objects.create(nombre=tipo, tipo=tipo)
            criterio = CriterioCalidad.objects.create(producto=producto, nombre="Dano visible")
            form = ClasificacionCalidadForm(producto_id=producto.pk)
            self.assertEqual(list(form.fields["criterio"].queryset), [criterio])
