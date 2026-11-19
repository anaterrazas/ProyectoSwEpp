import unittest
import copy
from .referencia_epp import validar_frame, validar_documento
from .seguridad_epp import estados_experimentales


class ReferenciaEPPTests(unittest.TestCase):
    def setUp(self):
        self.frame={"status":"REVIEWED","author":"anotador_fixture","reviewer":"revisor_fixture","exhaustive":True,
            "width":100,"height":100,"objects":[{"id":"obj1","clase":"PERSONA","persona_id":"P1",
            "visibilidad":"PARCIAL","bbox_xyxy":[0,0,100,100]}],"personas":[{"id":"P1",
            "casco_estado":"NO_EVALUABLE","chaleco_estado":"NO_EVALUABLE"}]}

    def test_pendiente_no_se_convierte_en_referencia(self):
        self.assertFalse(validar_frame({"status":"PENDING","objects":[]}))

    def test_region_oculta_no_prueba_ausencia(self):
        self.assertTrue(validar_frame(self.frame))
        self.frame['personas'][0]['casco_estado']='AUSENTE'
        with self.assertRaises(ValueError):validar_frame(self.frame)
        self.frame['personas'][0]['casco_region_visible']=True
        self.assertTrue(validar_frame(self.frame))

    def test_presencia_exige_equipo_asociado(self):
        self.frame['personas'][0]['casco_estado']='PRESENTE'
        with self.assertRaises(ValueError):validar_frame(self.frame)
        self.frame['objects'].append({'id':'obj2','clase':'CASCO','persona_id':'P1','visibilidad':'VISIBLE','bbox_xyxy':[10,10,30,30]})
        self.assertTrue(validar_frame(self.frame))

    def test_lista_vacia_no_es_negativo(self):
        self.frame.update(objects=[],personas=[])
        with self.assertRaises(ValueError):validar_frame(self.frame)
        self.frame['empty_confirmed']=True
        self.assertTrue(validar_frame(self.frame))

    def test_revisor_distinto_y_asociacion_valida(self):
        self.frame['reviewer']=self.frame['author']
        with self.assertRaises(ValueError):validar_frame(self.frame)
        self.frame['reviewer']='otro_fixture'
        self.frame['objects'][0]['persona_id']='inexistente'
        with self.assertRaises(ValueError):validar_frame(self.frame)

    def test_procedencia_no_puede_cambiar_en_copia_humana(self):
        frame={**self.frame,'sample_id':'fixture','video_id':'video_fixture','frame_index':0,
            'image':'fixture.png','image_sha256':'hash_fixture','tiempo_nominal_s':0}
        base={'frames':[frame],'videos':[]}
        documento=copy.deepcopy(base)
        self.assertEqual(validar_documento(documento,base)['frames_revisados'],1)
        documento['frames'][0]['image_sha256']='otra_imagen'
        with self.assertRaises(ValueError):validar_documento(documento,base)

    def test_eventos_exhaustivos_requieren_tiempo_revisado(self):
        frame={**self.frame,'sample_id':'fixture','video_id':'video_fixture','frame_index':0,
            'image':'fixture.png','image_sha256':'hash_fixture','tiempo_nominal_s':0}
        base={'frames':[frame],'videos':[{'video_id':'video_fixture','video_sha256':'hash_fixture','frames':25,'fps_nominal':25}]}
        documento=copy.deepcopy(base);documento.update(eventos_exhaustivos=True,eventos=[])
        with self.assertRaises(ValueError):validar_documento(documento,base)
        documento['videos'][0]['tiempo_exhaustivamente_revisado_s']=1
        self.assertTrue(validar_documento(documento,base)['referencia_temporal_declarada_completa'])

    def test_confianza_candidata_solo_positivo_chaleco(self):
        personas={1:[0,0,100,200]}
        vest=('Safety Vest',.20,[10,50,80,130])
        self.assertEqual(estados_experimentales(personas,[vest],'base')[1,'CHALECO'],'NO_EVALUABLE')
        self.assertEqual(estados_experimentales(personas,[vest],'candidata')[1,'CHALECO'],'CUMPLE')
        negativo=('NO-Safety Vest',.20,[10,50,80,130])
        self.assertEqual(estados_experimentales(personas,[negativo],'candidata')[1,'CHALECO'],'NO_EVALUABLE')
        casco=('Hardhat',.20,[10,0,80,30])
        self.assertEqual(estados_experimentales(personas,[casco],'candidata')[1,'CASCO'],'NO_EVALUABLE')

    def test_conflicto_candidata_se_abstiene(self):
        personas={1:[0,0,100,200]}
        cajas=[('Safety Vest',.20,[10,50,80,130]),('NO-Safety Vest',.40,[10,50,80,130])]
        self.assertEqual(estados_experimentales(personas,cajas,'candidata')[1,'CHALECO'],'NO_EVALUABLE')
