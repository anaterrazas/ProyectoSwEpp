"""Decisiones de fixtures en output/tests; nunca se adjudican referencias reales."""
import json
from pathlib import Path
import shutil
import uuid
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase, Client, override_settings
from .fuentes import ROOT
from . import adjudicacion_tapa as a


class AdjudicacionTapaTests(TestCase):
    def setUp(self):
        self.temp=ROOT/'output/tests'/uuid.uuid4().hex
        self.addCleanup(lambda:shutil.rmtree(self.temp,ignore_errors=True))
        cfg=override_settings(ROOT_URLCONF='experimentos.pilotos.urls',TAPA_ADJUDICACIONES_ROOT=self.temp)
        cfg.enable();self.addCleanup(cfg.disable)
        self.user=get_user_model().objects.create_user(username='revisor_fixture')
        self.user.user_permissions.set(Permission.objects.filter(codename__in=['view_analisisproduccion','change_inspeccioncalidad']))
        self.client=Client(enforce_csrf_checks=True);self.client.force_login(self.user)
        self.url='/demo/calidad/adjudicacion/'

    def datos(self):
        return dict(version='0',estado='ADJUDICADO',clase='TAPA',autor='REVISOR_FIXTURE',justificacion='Fixture técnico de guardado, no adjudicación real',usuario='fixture')

    def test_sin_decisiones_es_pendiente_y_sin_clase_preseleccionada(self):
        r=self.client.get(self.url)
        self.assertContains(r,'0 adjudicados · 7 pendientes')
        self.assertContains(r,'Seleccione una decisión',count=7)
        self.assertFalse(self.temp.exists())

    def test_autenticacion_y_permisos_lectura_escritura(self):
        self.assertEqual(Client().get(self.url).status_code,302)
        self.user.user_permissions.set(Permission.objects.filter(codename='view_analisisproduccion'))
        self.assertContains(self.client.get(self.url),'Solo consulta')
        client=Client();client.force_login(self.user)
        self.assertEqual(client.post(self.url,{'caso':'1',**self.datos()}).status_code,403)

    def test_csrf_y_guardado_real_http_en_fixture(self):
        self.assertEqual(self.client.post(self.url,{'caso':'1',**self.datos()}).status_code,403)
        from django.conf import settings
        self.client.get(self.url);token=self.client.cookies[settings.CSRF_COOKIE_NAME].value
        r=self.client.post(self.url,{'caso':'1',**self.datos(),'csrfmiddlewaretoken':token})
        self.assertEqual(r.status_code,302)
        h=a.historial(1)[0]
        self.assertEqual(h['clase_original'],'ENVASE');self.assertEqual(h['clase_adjudicada'],'TAPA')
        self.assertEqual(h['cuenta_usuario'],'revisor_fixture');self.assertTrue(h['fecha_utc'])
        self.assertFalse(h['aplicado_a_anotaciones'])

    def test_preserva_historial_y_rechaza_version_obsoleta(self):
        a.guardar_decision(1,**self.datos());p=self.temp/'1/000001.json';antes=p.read_bytes()
        with self.assertRaises(RuntimeError):a.guardar_decision(1,**self.datos())
        datos=self.datos();datos.update(version='1',estado='PENDIENTE',clase='')
        a.guardar_decision(1,**datos)
        self.assertEqual(antes,p.read_bytes());self.assertEqual(len(a.historial(1)),2)
        self.assertEqual(a.historial(1)[-1]['estado'],'PENDIENTE')

    def test_sin_justificacion_y_clases_invalidas_no_guarda(self):
        for cambio in ({'justificacion':''},{'autor':''},{'clase':''},{'clase':'TAPA_AUSENTE'},{'estado':'PENDIENTE'}):
            datos=self.datos();datos.update(cambio)
            with self.assertRaises(ValueError):a.guardar_decision(1,**datos)
        self.assertFalse(self.temp.exists())

    def test_no_evaluable_no_es_clase_tapa(self):
        datos=self.datos();datos['clase']='NO_EVALUABLE';a.guardar_decision(1,**datos)
        h=a.historial(1)[0];self.assertIsNone(h['clase_adjudicada']);self.assertFalse(h['evaluabilidad_adjudicada'])

    def test_notas_html_escapadas(self):
        datos=self.datos();datos['justificacion']='<script>FIXTURE</script>';a.guardar_decision(1,**datos)
        self.assertContains(self.client.get(self.url),'&lt;script&gt;FIXTURE&lt;/script&gt;')

    def test_imagenes_limitadas_a_siete_casos(self):
        for tipo in ['original','caja']:
            r=self.client.get(self.url+'imagen/1/'+tipo+'/');self.assertEqual(r.status_code,200);r.close()
        for suf in ['imagen/0/original/','imagen/8/caja/','imagen/1/archivo/']:
            self.assertEqual(self.client.get(self.url+suf).status_code,404)

    def test_modificacion_historial_detectada(self):
        a.guardar_decision(1,**self.datos());datos=self.datos();datos['version']='1';a.guardar_decision(1,**datos)
        p=self.temp/'1/000001.json';d=json.loads(p.read_text(encoding='utf-8'));d['justificacion']='TAMPER_FIXTURE';p.write_text(json.dumps(d),encoding='utf-8')
        with self.assertRaises(ValueError):a.historial(1)
