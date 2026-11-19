"""Pruebas de inspección geométrica; sin anotaciones ni predicciones reales."""
import unittest
from .auditar_suficiencia_tapa_v003 import iou


class IoUInspeccionTests(unittest.TestCase):
    def test_identidad_disjuntas_y_area_nula(self):
        self.assertEqual(iou([0,0,10,10],[0,0,10,10]),1)
        self.assertEqual(iou([0,0,10,10],[20,20,30,30]),0)
        self.assertEqual(iou([0,0,0,0],[0,0,0,0]),0)

    def test_simetria_y_superposicion_parcial(self):
        a=[0,0,10,10];b=[5,0,15,10]
        self.assertAlmostEqual(iou(a,b),1/3)
        self.assertEqual(iou(a,b),iou(b,a))

    def test_caja_contenida_no_coincide_por_tener_mismo_centro(self):
        self.assertAlmostEqual(iou([0,0,10,10],[4,4,6,6]),.04)


if __name__=='__main__':unittest.main()
