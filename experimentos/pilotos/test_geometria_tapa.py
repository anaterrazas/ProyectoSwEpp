"""Fixtures aislados; ninguna modificación humana real ni SQLite."""
from copy import deepcopy
import json
import shutil
import uuid
from unittest.mock import patch
from django.contrib.auth.models import AnonymousUser
from django.http import Http404
from django.middleware.csrf import CsrfViewMiddleware
from django.test import SimpleTestCase,RequestFactory,override_settings
from . import geometria_tapa as g


class User:
    is_authenticated=True
    def __init__(self,write=True):self.write=write
    def has_perm(self,p):return self.write if p=='produccion.change_inspeccioncalidad' else True
    def has_perms(self,p):return all(self.has_perm(v) for v in p)
    def get_username(self):return 'fixture_no_humano'


class GeometriaTapaTests(SimpleTestCase):
    def setUp(self):
        self.temp=g.ROOT/'output/tests'/uuid.uuid4().hex
        self.addCleanup(lambda:shutil.rmtree(self.temp,ignore_errors=True))
        cfg=override_settings(ROOT_URLCONF='experimentos.pilotos.urls',TAPA_GEOMETRIA_ROOT=self.temp)
        cfg.enable();self.addCleanup(cfg.disable)
        self.r=g.caso(0);self.rf=RequestFactory()

    def payload(self):
        return dict(version=0,source_sha256=self.r['sha256'],protocolo_sha256=g.sha(g.PROTOCOLO),confirma_protocolo=True,
            decision='CONSERVAR',bbox_xyxy=self.r['bbox_original_xyxy'],visibilidad='TOTAL',autor='AUTOR_FIXTURE_NO_HUMANO',justificacion='Prueba técnica en salida aislada',edicion_humana_explicita=False)

    def test_originales_y_copia_derivada_sin_autorizar_entrenamiento(self):
        before=g.sha(g.AUDIT/'catalogo.json');record=g.guardar(0,self.payload(),'fixture')
        self.assertEqual(record['bbox_xyxy'],self.r['bbox_original_xyxy'])
        self.assertEqual(before,g.sha(g.AUDIT/'catalogo.json'))
        d=g.derivada();self.assertEqual(len(d['records']),284)
        self.assertEqual(d['records'][0]['estado_humano'],'CONSERVAR')
        self.assertFalse(d['entrenamiento_autorizado'])

    def test_edicion_manual_preserva_coordenadas_sin_clipping(self):
        p=self.payload();p.update(decision='AJUSTADA',edicion_humana_explicita=True)
        p['bbox_xyxy']=[1.125,2.25,300.5,400.75]
        d=g.guardar(0,p,'fixture')
        self.assertEqual(d['bbox_xyxy'],p['bbox_xyxy'])
        self.assertEqual(d['bbox_original_xyxy'],self.r['bbox_original_xyxy'])

    def test_rechaza_ajuste_automatico_y_conservar_coordenadas_distintas(self):
        for change in ({'decision':'AJUSTADA'},{'decision':'AJUSTADA','bbox_xyxy':[1,2,3,4]},
                       {'bbox_xyxy':[1,2,3,4]},{'confirma_protocolo':False},{'protocolo_sha256':'otro'}):
            p=self.payload();p.update(change)
            with self.assertRaises(ValueError):g.validar(self.r,p)

    def test_limites_y_campos_requeridos(self):
        for b in ([-1,0,10,10],[0,0,0,10],[0,0,float('nan'),10],[0,0,99999,99999]):
            p=self.payload();p.update(decision='AJUSTADA',edicion_humana_explicita=True,bbox_xyxy=b)
            with self.assertRaises(ValueError):g.validar(self.r,p)
        for change in ({'autor':''},{'justificacion':''},{'source_sha256':'bad'},{'visibilidad':'INFERIDA'}):
            p=self.payload();p.update(change)
            with self.assertRaises(ValueError):g.validar(self.r,p)

    def test_no_evaluable_no_inventa_caja_ni_negativo(self):
        p=self.payload();p.update(decision='NO_EVALUABLE',bbox_xyxy=None,visibilidad='DUDOSA')
        d=g.guardar(0,p,'fixture');self.assertIsNone(d['bbox_xyxy'])
        self.assertIsNone(g.derivada()['records'][0]['bbox_humana_xyxy'])

    def test_historial_versiones_y_alteraciones(self):
        g.guardar(0,self.payload(),'fixture');first=(self.temp/'000001.json').read_bytes()
        with self.assertRaises(RuntimeError):g.guardar(0,self.payload(),'fixture')
        p=self.payload();p['version']=1;g.guardar(0,p,'fixture')
        self.assertEqual(len(g.historial()),2);self.assertEqual(first,(self.temp/'000001.json').read_bytes())
        f=self.temp/'000002.json';d=json.loads(f.read_text(encoding='utf-8'));d['autor']='alterado';f.write_text(json.dumps(d),encoding='utf-8')
        with self.assertRaises(ValueError):g.historial()

    def test_publicacion_fallida_no_deja_historial_parcial(self):
        with patch.object(g.os,'rename',side_effect=OSError('fixture')):
            with self.assertRaises(OSError):g.guardar(0,self.payload(),'fixture')
        self.assertEqual(g.historial(),[]);self.assertFalse((self.temp/'revision.lock').exists())

    def test_permisos_csrf_y_render(self):
        r=self.rf.get('/');r.user=AnonymousUser();self.assertEqual(g.revision(r).status_code,302)
        r=self.rf.post('/',data=json.dumps(self.payload()),content_type='application/json');r.user=User(False)
        self.assertEqual(g.revision(r).status_code,403)
        self.assertEqual(CsrfViewMiddleware(lambda r:None).process_view(r,g.revision,(),{}).status_code,403)
        r=self.rf.get('/');r.user=User();res=g.revision(r)
        self.assertEqual(res.status_code,200);self.assertNotIn(str(g.ROOT),res.content.decode())
        self.assertFalse(self.temp.exists())

    def test_catalogo_cerrado_y_medios(self):
        r=self.rf.get('/');r.user=User()
        for n in (-1,284):
            with self.assertRaises(Http404):g.imagen(r,n)
        res=g.imagen(r,0);self.assertEqual(res.status_code,200);res.close()
