"""Solo pruebas nuevas de integración; fixtures no son adjudicaciones reales."""
from copy import deepcopy
import unittest
from .integrar_adjudicaciones_tapa import aplicar_decisiones


class IntegracionTapaTests(unittest.TestCase):
    def setUp(self):
        self.anot={'sample_id':'FIXTURE','boxes':[{'box_id':'b','class_name':'ENVASE','bbox_xyxy':[0,0,10,10],'notes':'nota','not_evaluable':False,'parent_envase_box_id':None}]}
        self.d={'estado':'ADJUDICADO','sample_id':'FIXTURE','box_id':'b','clase_original':'ENVASE','bbox_original':[0,0,10,10],'nota_original':'nota','clase_adjudicada':'TAPA','evaluabilidad_adjudicada':None,'autor':'REVISOR_FIXTURE','fecha_utc':'2026-11-18T00:00:00Z','justificacion':'Fixture de integración'}

    def test_solo_cambia_clase_y_preserva_original(self):
        antes=deepcopy(self.anot);nuevo=aplicar_decisiones(self.anot,[self.d])
        self.assertEqual(self.anot,antes);self.assertEqual(nuevo['boxes'][0]['class_name'],'TAPA')
        esperado=deepcopy(antes);esperado['boxes'][0]['class_name']='TAPA';self.assertEqual(nuevo,esperado)

    def test_pendiente_incompleta_o_origen_distinto_no_integra(self):
        for k,v in [('estado','PENDIENTE'),('autor',''),('justificacion',''),('fecha_utc',''),('clase_original','TAPA'),('bbox_original',[1,2,3,4]),('sample_id','OTRA'),('box_id','OTRA'),('nota_original','otra')]:
            with self.subTest(campo=k):
                d={**self.d,k:v}
                with self.assertRaises(ValueError):aplicar_decisiones(self.anot,[d])

    def test_no_evaluable_conserva_clase_no_inventa_tapa(self):
        d={**self.d,'clase_adjudicada':None,'evaluabilidad_adjudicada':False}
        b=aplicar_decisiones(self.anot,[d])['boxes'][0]
        self.assertEqual(b['class_name'],'ENVASE');self.assertTrue(b['not_evaluable'])

    def test_rechaza_decision_duplicada_y_clase_incompatible(self):
        with self.assertRaises(ValueError):aplicar_decisiones(self.anot,[self.d,self.d])
        with self.assertRaises(ValueError):aplicar_decisiones(self.anot,[{**self.d,'clase_adjudicada':'TAPA_AUSENTE'}])
