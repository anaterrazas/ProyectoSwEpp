"""Indicadores técnicos con fixtures, sin modificar referencias humanas."""
import unittest
from .auditoria_tapa import medidas, duplicados_visuales


class AuditoriaTapaTests(unittest.TestCase):
    def test_tamano_en_entrada_de_modelo(self):
        m=medidas([10,20,40,80],1920,1080)
        self.assertEqual(m['min_lado_entrada640'],10)
        self.assertTrue(m['pequena_640_menor16'])

    def test_rechaza_caja_fuera_de_imagen(self):
        for b in ([0,0,1001,10],[0,10,20,5],[0,0,float('nan'),10]):
            with self.assertRaises(ValueError):medidas(b,1000,500)

    def test_dhash_es_candidato_no_borrado(self):
        frames=[{'sample_id':'FIXTURE_A','dhash':'0'},{'sample_id':'FIXTURE_B','dhash':'1'},{'sample_id':'FIXTURE_C','dhash':'ffff'}]
        r=duplicados_visuales(frames)
        self.assertEqual(len(r),1)
        self.assertEqual(r[0]['distancia_dhash'],1)
        self.assertEqual(len(frames),3)
