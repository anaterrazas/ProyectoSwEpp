"""Pruebas de fixtures; nunca guardan adjudicaciones en el dataset real."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import uuid
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.middleware.csrf import CsrfViewMiddleware
from django.test import SimpleTestCase, RequestFactory, override_settings

from . import revision_tapa_v4 as v


class Usuario:
    is_authenticated = True
    def __init__(self, escribir=True, leer=True):
        self.escribir=escribir; self.leer=leer
    def has_perm(self, perm):
        return self.escribir if perm=='produccion.change_inspeccioncalidad' else self.leer
    def has_perms(self, perms):
        return all(self.has_perm(p) for p in perms)
    def get_username(self):
        return 'fixture_no_humano'


class RevisionV4Tests(SimpleTestCase):
    def test_javascript_localizable_en_windows(self):
        from django.contrib.staticfiles import finders
        self.assertIsNotNone(finders.find('laboratorio/revision_tapa_v4.js'))

    def setUp(self):
        self.temp=v.ROOT/'output/tests'/uuid.uuid4().hex
        self.addCleanup(lambda:shutil.rmtree(self.temp, ignore_errors=True))
        cfg=override_settings(ROOT_URLCONF='experimentos.pilotos.urls', TAPA_V4_REVISION_ROOT=self.temp)
        cfg.enable();self.addCleanup(cfg.disable)
        self.rf=RequestFactory()
        self.records=v.fuente();self.r=next(r for r in self.records if r['image_id']==9)

    def payload(self):
        return dict(version=0,image_id=9,expected_sha256=self.r['sha256'],autor='AUTOR_FIXTURE_NO_HUMANO',
                    justificacion='Fixture de prueba: no es una adjudicación real',exhaustividad='PENDIENTE',
                    decisiones=[dict(annotation_id=31,clase='ENVASE',visibilidad='NO_REVISADA',justificacion='Fixture técnico')],nuevas_cajas=[])

    def test_generacion_conserva_geometria_y_fuente_y_no_autoriza(self):
        source=v.sha(v.BASE/'dataset_candidato.jsonl')
        result=v.guardar(9,self.payload(),'fixture')
        self.assertEqual(result['conflictos_resueltos'],[31])
        self.assertFalse(result['entrenamiento_autorizado'])
        history=v.generaciones();self.assertEqual(len(history),1)
        ds=[json.loads(s) for s in (self.temp/'versiones/000001/dataset.jsonl').read_text(encoding='utf-8').splitlines()]
        actual=next(r for r in ds if r['image_id']==9)
        self.assertEqual(actual['source_annotations_cap'],self.r['source_annotations_cap'])
        self.assertEqual(actual['effective_annotations'][0]['clase'],'ENVASE')
        self.assertEqual(source,v.sha(v.BASE/'dataset_candidato.jsonl'))
        self.assertTrue(all(r['negative_confirmed'] is None for r in ds))

    def test_version_obsoleta_y_cadena_de_historial(self):
        v.guardar(9,self.payload(),'fixture');p=self.temp/'versiones/000001/decision.json';original=p.read_bytes()
        with self.assertRaises(RuntimeError):v.guardar(9,self.payload(),'fixture')
        d=self.payload();d['version']=1;d['decisiones'][0]['clase']='PENDIENTE'
        v.guardar(9,d,'fixture')
        self.assertEqual(p.read_bytes(),original)
        self.assertEqual(v.generaciones()[-1]['hash_decision_anterior'],v.sha(p))
        p.write_text('{}',encoding='utf-8')
        with self.assertRaises((ValueError,KeyError)):v.generaciones()

    def test_desconocidos_no_son_negativos_ni_tapa_adjudicada(self):
        ds=v.derivar(self.records,[])
        b=next(r for r in ds if r['image_id']==42)['effective_annotations'][0]
        self.assertEqual(b['clase'],'PENDIENTE');self.assertFalse(b['evaluable'])
        self.assertTrue(all(r['negative_confirmed'] is None and not r['training_approved'] for r in ds))

    def test_caja_manual_solo_coordenadas_humanas_no_clipping(self):
        p=self.payload();box=dict(id='manual-fixture',clase='TAPA',visibilidad='PARCIAL',bbox_xyxy=[1.25,2.5,12.75,18.25],justificacion='Fixture de coordenadas explícitas')
        p['nuevas_cajas']=[box]
        d=v.validar(p,self.r);self.assertEqual(d['nuevas_cajas'][0]['bbox_xyxy'],box['bbox_xyxy'])
        for coords in ([-1,0,10,10],[0,0,0,10],[0,0,float('nan'),10],[0,0,100000,10]):
            q=deepcopy(p);q['nuevas_cajas'][0]['bbox_xyxy']=coords
            with self.assertRaises(ValueError):v.validar(q,self.r)

    def test_campos_obligatorios_cajas_ajenas_y_falsa_cobertura(self):
        for patch_data in ({'autor':''},{'justificacion':''},{'expected_sha256':'incorrecto'},{'decisiones':[{'annotation_id':204,'clase':'TAPA'}]}):
            p=self.payload();p.update(patch_data)
            with self.assertRaises(ValueError):v.validar(p,self.r)
        p=self.payload();p['decisiones'][0]['clase']='PENDIENTE';p['exhaustividad']='COMPLETA'
        with self.assertRaises(ValueError):v.validar(p,self.r)

    def test_imagenes_y_archivos_en_catalogo_cerrado(self):
        request=self.rf.get('/');request.user=Usuario()
        response=v.imagen(request,24,'original');self.assertEqual(response.status_code,200);response.close()
        from django.http import Http404
        for image_id,tipo in ((999,'original'),(24,'../../db.sqlite3')):
            with self.assertRaises(Http404):v.imagen(request,image_id,tipo)
        with self.assertRaises(Http404):v.descarga(request,0,'dataset.jsonl')
        v.guardar(9,self.payload(),'fixture')
        with self.assertRaises(Http404):v.descarga(request,1,'../../db.sqlite3')

    def test_auth_permisos_csrf_y_render_sin_rutas_absolutas(self):
        request=self.rf.get('/demo/calidad/tapa-v4/');request.user=AnonymousUser()
        self.assertEqual(v.revision(request).status_code,302)
        from django.core.exceptions import PermissionDenied
        request.user=Usuario(leer=False)
        with self.assertRaises(PermissionDenied):v.revision(request)
        request=self.rf.post('/demo/calidad/tapa-v4/',data=json.dumps(self.payload()),content_type='application/json');request.user=Usuario(escribir=False)
        self.assertEqual(v.revision(request).status_code,403)
        denied=CsrfViewMiddleware(lambda r:None).process_view(request,v.revision,(),{})
        self.assertEqual(denied.status_code,403)
        request=self.rf.get('/demo/calidad/tapa-v4/');request.user=Usuario()
        response=v.revision(request);self.assertEqual(response.status_code,200)
        body=response.content.decode();self.assertNotIn(str(v.ROOT),body);self.assertIn('csrfmiddlewaretoken',body)
        self.assertFalse(self.temp.exists())

    def test_particiones_y_preparacion_sin_humanos_inventados(self):
        folder=v.preparar();state=v.leer(folder/'estado.json')
        self.assertEqual(state['conflictos_pendientes'],sorted(v.CONFLICTOS))
        self.assertEqual(state['cajas_nuevas'],0)
        self.assertEqual(len(v.leer(folder/'manifest.json')['grupos']),14)
        with self.assertRaises(FileExistsError):v.preparar()

    def test_fallo_de_publicacion_no_deja_decision_parcial(self):
        with patch.object(v.os,'rename',side_effect=OSError('fixture fallo de disco')):
            with self.assertRaises(OSError):v.guardar(9,self.payload(),'fixture')
        self.assertEqual(v.generaciones(),[])
        self.assertFalse((self.temp/'revision.lock').exists())
