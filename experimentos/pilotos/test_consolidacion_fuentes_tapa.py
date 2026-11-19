"""Comprueba el índice de candidatos; no modifica fuentes ni adjudica cajas."""
from collections import Counter
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'datasets/calidad_botellas/v003/tapa_multifuente_candidato_001'


def rows(p):return [json.loads(s) for s in p.read_text(encoding='utf-8').splitlines() if s]


class ConsolidacionFuentesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=rows(DATA/'samples.candidate.jsonl')

    def test_conteos_sin_duplicados_ni_referencias_propias(self):
        self.assertEqual(len(self.data),284)
        self.assertEqual(len({r['image_sha256'] for r in self.data}),284)
        self.assertEqual(Counter(r['source'] for r in self.data),{'roboflow_caps_v26':272,'roboflow_bottle_v4':12})
        self.assertTrue(all(r['negative_confirmed'] is None for r in self.data))

    def test_grupos_no_divididos_y_no_test_fingido(self):
        groups={}
        for r in self.data:groups.setdefault(r['group_id'],set()).add(r['proposed_partition'])
        self.assertEqual(len(groups),8)
        self.assertTrue(all(len(p)==1 for p in groups.values()))
        self.assertEqual(Counter(r['proposed_partition'] for r in self.data),{'train':137,'validation':135,'RESERVA_SIN_TEST_INDEPENDIENTE':12})
        self.assertTrue(all(not r['training_approved'] and not r['partition_approved'] for r in self.data))

    def test_cajas_v26_se_conservan_sin_convertir_gap_ring_no_cap(self):
        source={r['sample_id']:r for r in rows(ROOT/'datasets/publicos_calidad_botellas/imports/roboflow_caps_v26_001/samples.public.jsonl')}
        for r in self.data:
            if r['source']!='roboflow_caps_v26':continue
            self.assertEqual(len(r['source_annotations']),1)
            a=r['source_annotations'][0]
            self.assertIn(a['source_class'],('Good Cap','Broken Cap'))
            self.assertIn(a,[b for o in source[r['sample_id']]['source_occurrences'] for b in o['annotations']])
            x,y,w,h=a['bbox_xywh_pixels']
            self.assertTrue(0<=x<x+w<=r['width'] and 0<=y<y+h<=r['height'])

    def test_convenciones_diferentes_identificadas_no_export_silencioso(self):
        self.assertEqual({r['geometry_convention'] for r in self.data},{'ROI_CAP_CON_ANILLO_Y_CONTEXTO_DE_CUELLO','CAP_COCO_FUENTE_V4'})
        self.assertTrue(all(not r['mapping_approved'] for r in self.data))
        self.assertFalse(list(DATA.glob('*.yaml')))


if __name__=='__main__':unittest.main()
