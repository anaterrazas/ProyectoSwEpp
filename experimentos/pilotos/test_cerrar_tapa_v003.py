"""Contabilidad y bloqueos sobre fixtures; no guarda decisiones humanas."""
from copy import deepcopy
import unittest

from .cerrar_tapa_v003 import analizar


def imagen(i, aid, digest, grupo='g1', split='train'):
    return dict(image_id=i, sha256=digest, group_id=grupo, proposed_partition=split,
                source_annotations_cap=[dict(id=aid,image_id=i,category_id=1,bbox=[1,2,10,12])])


def decision(i, aid, revision, clase, cobertura='PENDIENTE'):
    return dict(image_id=i,revision_global=revision,autor='AUTOR_FIXTURE',fecha_utc='2026-11-18T00:00:00+00:00',
                justificacion='Fixture, no anotación humana real',exhaustividad=cobertura,nuevas_cajas=[],
                decisiones=[dict(annotation_id=aid,clase=clase,visibilidad='TOTAL',justificacion='Fixture',clase_original='cap',bbox_original=[1,2,10,12])])


class CierreV003Tests(unittest.TestCase):
    def setUp(self):
        self.records=[imagen(9,31,'a'),imagen(38,123,'b'),imagen(60,203,'c','g2','validation'),imagen(24,76,'d','g3','PENDIENTE')]
        self.history=[decision(9,31,1,'ENVASE'),decision(9,31,2,'ENVASE'),decision(38,123,3,'ENVASE','COMPLETA'),decision(60,203,4,'TAPA','NO_EVALUABLE')]

    def test_cuenta_ultima_revision_sin_sumar_guardados(self):
        _,boxes,s=analizar(self.records,self.history,{31,123})
        self.assertEqual(s['cajas_finales'],{'ENVASE':2,'TAPA':2})
        self.assertEqual(len(boxes),4);self.assertEqual(s['imagenes_revisadas'],3)
        self.assertEqual(s['cajas_nuevas'],0);self.assertEqual(s['tapa_con_revision_humana'],1)
        self.assertEqual(len(s['revisiones_repetidas_conservadas']),1)
        self.assertFalse(s['entrenamiento_autorizado'])

    def test_no_modifica_fuentes_y_conserva_cajas(self):
        antes=deepcopy(self.records);history=deepcopy(self.history)
        samples,_,_=analizar(self.records,self.history,{31,123})
        self.assertEqual(self.records,antes);self.assertEqual(self.history,history)
        for original,nueva in zip(antes,samples):
            self.assertEqual(original['source_annotations_cap'],nueva['source_annotations_cap'])
            self.assertIsNone(nueva['negative_confirmed'])
            self.assertFalse(nueva['partition_approved'])

    def test_detecta_cobertura_inconsistente_y_revision_ausente(self):
        _,_,s=analizar(self.records,self.history,{31,123})
        codes={(p['image_id'],p['codigo']) for p in s['incidencias']}
        self.assertIn((24,'REVISION_NO_GUARDADA'),codes)
        self.assertIn((38,'TAPA_DESCRITA_SIN_CAJA_TAPA'),codes)
        self.assertIn((60,'POSITIVO_LOCAL_EN_IMAGEN_NO_EVALUABLE'),codes)
        self.assertEqual(s['cobertura_declarada']['COMPLETA'],1)

    def test_rechaza_cruces_duplicados_y_geometria_distinta(self):
        for mutation in ('grupo','hash','geometria'):
            records=deepcopy(self.records);history=deepcopy(self.history)
            if mutation=='grupo':records[2]['group_id']='g1'
            elif mutation=='hash':records[2]['sha256']='a'
            else:history[0]['decisiones'][0]['bbox_original'][0]=999;history[1]['decisiones'][0]['bbox_original'][0]=999
            with self.assertRaises(ValueError):analizar(records,history,{31,123})

    def test_no_evaluable_no_se_convierte_en_tapa_ni_negativo(self):
        history=deepcopy(self.history);history[-1]['decisiones'][0]['clase']='NO_EVALUABLE'
        _,boxes,s=analizar(self.records,history,{31,123})
        self.assertEqual(s['cajas_excluidas_de_positivos'],1)
        self.assertTrue(next(b for b in boxes if b['image_id']==60)['excluded_from_positive_labels'])
        self.assertEqual(s['negativos_inferidos'],0)

    def test_cajas_manuales_conservan_coordenadas_y_cuentan_una_vez(self):
        history=deepcopy(self.history)
        history[2]['nuevas_cajas']=[dict(id='manual-fixture',clase='TAPA',bbox_xyxy=[1.2,2.3,4.5,6.7],visibilidad='PARCIAL',justificacion='Fixture')]
        _,boxes,s=analizar(self.records,history,{31,123})
        self.assertEqual(s['cajas_nuevas'],1)
        self.assertEqual(next(b for b in boxes if b['annotation_id']=='manual-fixture')['bbox_xyxy'],[1.2,2.3,4.5,6.7])
        self.assertNotIn('TAPA_DESCRITA_SIN_CAJA_TAPA',[p['codigo'] for p in s['incidencias'] if p['image_id']==38])


if __name__=='__main__':
    unittest.main()
