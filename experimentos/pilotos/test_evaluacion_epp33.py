import copy
import unittest
from .evaluacion_epp33 import comparar_frame, resumir, normalizar_autor


class EvaluacionEPP33Tests(unittest.TestCase):
    def setUp(self):
        self.frame={'sample_id':'fixture','video_id':'video_fixture','frame_index':0,'tiempo_nominal_s':0,
            'objects':[{'id':'h0','clase':'PERSONA','persona_id':'P1','bbox_xyxy':[0,0,100,200],'visibilidad':'PARCIAL'},
                       {'id':'h1','clase':'CASCO','persona_id':'P1','bbox_xyxy':[10,0,40,30],'visibilidad':'VISIBLE'}],
            'personas':[{'id':'P1','casco_estado':'PRESENTE','chaleco_estado':'NO_EVALUABLE'}]}
        self.preds=[{'clase':'PERSONA','bbox_xyxy':[0,0,100,200],'score':.9,'persona_pred_id':0},
                    {'clase':'CASCO','bbox_xyxy':[10,0,40,30],'score':.8,'persona_pred_id':0}]

    def test_match_y_propietario_cero_validos(self):
        d=comparar_frame(self.frame,self.preds)
        self.assertEqual(d['asociaciones'][0]['resultado'],'CORRECTA')
        self.assertEqual(resumir([d])['deteccion']['CASCO']['f1'],1)

    def test_desconocido_no_es_negativo(self):
        self.frame['objects']=self.frame['objects'][:1]
        self.frame['personas'][0]['casco_estado']='NO_EVALUABLE'
        d=comparar_frame(self.frame,self.preds)
        self.assertEqual(d['cuentas']['CASCO'],{'TP':0,'FP':0,'FN':0,'ignoradas':1})

    def test_positivo_tiene_prioridad_sobre_mascara(self):
        self.frame['personas'].append({'id':'P2','casco_estado':'NO_EVALUABLE','chaleco_estado':'NO_EVALUABLE'})
        self.frame['objects'].append({'id':'h2','clase':'PERSONA','persona_id':'P2','bbox_xyxy':[0,0,100,200],'visibilidad':'PARCIAL'})
        d=comparar_frame(self.frame,self.preds)
        self.assertEqual(d['cuentas']['CASCO']['TP'],1)

    def test_duplicado_y_omision(self):
        d=comparar_frame(self.frame,self.preds+[dict(self.preds[1],score=.4)])
        self.assertEqual(d['cuentas']['CASCO']['FP'],1)
        d=comparar_frame(self.frame,[])
        m=resumir([d])['deteccion']['CASCO']
        self.assertEqual(m['FN'],1);self.assertEqual(m['recall'],0);self.assertEqual(m['f1'],0)
        self.assertIsNone(m['precision'])

    def test_propietario_no_emparejado_no_se_declara_correcto(self):
        self.preds[1]['persona_pred_id']=99
        d=comparar_frame(self.frame,self.preds)
        self.assertEqual(d['asociaciones'][0]['resultado'],'PERSONA_NO_EMPAREJADA')

    def test_normalizacion_sin_mutacion(self):
        autor={'author':' ANa '};original=copy.deepcopy(autor)
        self.assertEqual(normalizar_autor(autor['author']),'ana')
        self.assertEqual(autor,original)

    def test_propietario_incorrecto_emparejado_se_detecta(self):
        self.frame['objects'].append({'id':'h2','clase':'PERSONA','persona_id':'P2','bbox_xyxy':[110,0,210,200],'visibilidad':'VISIBLE'})
        self.frame['personas'].append({'id':'P2','casco_estado':'NO_EVALUABLE','chaleco_estado':'NO_EVALUABLE'})
        self.preds.append({'clase':'PERSONA','bbox_xyxy':[110,0,210,200],'score':.9,'persona_pred_id':1})
        self.preds[1]['persona_pred_id']=1
        d=comparar_frame(self.frame,self.preds)
        self.assertEqual(d['asociaciones'][0]['resultado'],'INCORRECTA')
        self.assertEqual(resumir([d])['asociacion']['CASCO']['exactitud_condicional_verificable'],0)
