import unittest
from .evaluacion import comparar


class ComparacionTests(unittest.TestCase):
    def setUp(self):
        self.ref = {"records": [{"sample_id": "fixture", "source": {"image_sha256": "hash_fixture"},
            "annotation": {"status": "reviewed", "exhaustive": True, "boxes": [
                {"class_name": "ENVASE", "bbox_xyxy": [0, 0, 10, 10], "not_evaluable": False},
                {"class_name": "TAPA", "bbox_xyxy": [0, 0, 4, 4], "not_evaluable": False}]}}]}
        self.pred = {"samples": [{"sample_id": "fixture", "image_sha256": "hash_fixture", "detections": [
            {"class_name": "ENVASE", "bbox_xyxy": [0, 0, 10, 10], "score": .9}]}], "clases_ejecutadas": ["ENVASE"]}

    def test_acierto_no_inventa_metricas_tapa(self):
        r = comparar(self.ref, self.pred)
        self.assertEqual(r["por_clase"]["ENVASE"]["precision"], 1)
        self.assertIsNone(r["por_clase"]["TAPA"]["recall"])
        self.assertIsNone(r["defectos"]["metricas"])

    def test_duplicado_y_omision(self):
        self.pred["samples"][0]["detections"] *= 2
        self.assertEqual(comparar(self.ref, self.pred)["por_clase"]["ENVASE"]["fp"], 1)
        self.pred["samples"][0]["detections"] = []
        r = comparar(self.ref, self.pred)["por_clase"]["ENVASE"]
        self.assertEqual(r["fn"], 1)
        self.assertIsNone(r["precision"])
        self.assertEqual(r["recall"], 0)

    def test_muestra_no_ejecutada_no_es_omision(self):
        r = comparar(self.ref, {"samples": []})
        self.assertEqual(r["no_ejecutadas"], ["fixture"])
        self.assertIsNone(r["por_clase"]["ENVASE"]["recall"])

    def test_hash_y_revision_obligatorios(self):
        self.pred["samples"][0]["image_sha256"] = "otro"
        with self.assertRaises(ValueError):
            comparar(self.ref, self.pred)
        self.pred["samples"][0]["image_sha256"] = "hash_fixture"
        self.ref["records"][0]["annotation"]["exhaustive"] = False
        with self.assertRaises(ValueError):
            comparar(self.ref, self.pred)

    def test_region_no_evaluable_no_se_convierte_en_negativo(self):
        self.ref["records"][0]["annotation"]["boxes"][0]["not_evaluable"] = True
        r = comparar(self.ref, self.pred)["por_clase"]["ENVASE"]
        self.assertEqual(r["ignoradas"], 1)
        self.assertEqual(r["fp"], 0)
        self.assertEqual(r["fn"], 0)

    def test_prediccion_pequena_en_region_desconocida_no_es_fp(self):
        self.ref["records"][0]["annotation"]["boxes"][0]["not_evaluable"] = None
        self.pred["samples"][0]["detections"][0]["bbox_xyxy"] = [1, 1, 2, 2]
        r = comparar(self.ref, self.pred)
        self.assertEqual(r["por_clase"]["ENVASE"]["ignoradas"], 1)
        self.assertEqual(r["por_clase"]["ENVASE"]["fp"], 0)
        self.assertEqual(r["detalle"][0]["referencias"][0]["estado"], "NO_EVALUABLE")
