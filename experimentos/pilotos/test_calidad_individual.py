"""Fixtures técnicos explícitos; no son detecciones ni etiquetas de evaluación."""
from copy import deepcopy
import unittest
import numpy as np
from .calidad_individual import preparar_fotograma, recortar_region, CLASES_INSPECCION


class CalidadIndividualTests(unittest.TestCase):
    def setUp(self):
        self.sha = "a"*64
        self.dato = {"frame_index": 0, "pts_seconds": 0.0, "objects": [
            {"label": "bottle", "class_id": 39, "bbox_xyxy": [1, 1, 5, 7], "score": .8,
             "track_id": 2, "observed_this_frame": True, "frame_index": 0,
             "video_sha256": self.sha, "run_id": "FIXTURE", "cap_neck_region": {"bbox_xyxy": [1, 1, 5, 3], "quality": {"technical_pass": True}}}]}

    def preparar(self, registro=None):
        return preparar_fotograma(registro if registro is not None else self.dato, fuente_sha256=self.sha, ejecucion_id="FIXTURE")

    def test_preserva_deteccion_y_original(self):
        original = deepcopy(self.dato)
        nuevo = self.preparar()
        objeto = nuevo["envases_observados"][0]
        self.assertEqual(objeto["bbox_xyxy"], self.dato["objects"][0]["bbox_xyxy"])
        self.assertEqual(objeto["score"], .8)
        self.assertEqual(objeto["track_id"], 2)
        objeto["roi_cuello_candidata"]["quality"]["technical_pass"] = False
        self.assertEqual(self.dato, original)

    def test_roi_no_es_tapa_y_falta_deteccion_no_es_ausencia(self):
        nuevo = self.preparar();objeto = nuevo["envases_observados"][0]
        self.assertIsNone(nuevo["tapas_observadas"])
        self.assertIsNone(objeto["tapa_asociada"])
        self.assertFalse(objeto["roi_es_tapa_detectada"])
        self.assertEqual(objeto["inspeccion"]["estado"], "NO EVALUABLE")
        self.assertEqual(set(objeto["inspeccion"]["clases"]), set(CLASES_INSPECCION))
        self.assertTrue(all(c["prediccion"] is None and c["score"] is None for c in objeto["inspeccion"]["clases"].values()))

    def test_calidad_tecnica_no_certifica_visibilidad(self):
        self.assertEqual(self.preparar()["envases_observados"][0]["visibilidad"]["estado"], "NO EVALUABLE")

    def test_sin_observaciones_no_conformidad(self):
        self.dato["objects"] = []
        nuevo = self.preparar()
        self.assertEqual(nuevo["envases_observados"], [])
        self.assertIsNone(nuevo["tapas_observadas"])

    def test_rechaza_datos_invalidos(self):
        for campo, valor in [("score", float("nan")), ("score", 2), ("bbox_xyxy", [1,2,1,8]),
                             ("observed_this_frame", False), ("video_sha256", "b"*64),
                             ("run_id", "OTRA"), ("frame_index", 1), ("class_id", 1), ("track_id", -1)]:
            with self.subTest(campo=campo, valor=valor):
                registro = deepcopy(self.dato);registro["objects"][0][campo] = valor
                with self.assertRaises(ValueError): self.preparar(registro)

    def test_no_repite_id_y_permite_observacion_sin_id(self):
        self.dato["objects"].append(deepcopy(self.dato["objects"][0]))
        with self.assertRaises(ValueError): self.preparar()
        for o in self.dato["objects"]: o["track_id"] = None
        self.assertEqual(len(self.preparar()["envases_observados"]), 2)

    def test_recorte_no_altera_imagen(self):
        imagen = np.arange(100).reshape(10,10);original = imagen.copy()
        region = recortar_region(imagen, [1,2,5,7]);self.assertEqual(region.shape,(5,4))
        region[:] = 0;np.testing.assert_array_equal(imagen,original)
        with self.assertRaises(ValueError): recortar_region(imagen,[0,0,11,8])
