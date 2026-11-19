import unittest
from .piloto import Persistencia, equipos_piloto, estados


class PilotoTests(unittest.TestCase):
    def test_area_sin_reglas_o_epp_no_soportado_se_rechaza(self):
        for nombres in ([], ["Guantes"]):
            with self.assertRaises(ValueError):
                equipos_piloto(nombres)
        self.assertEqual(equipos_piloto([" Cásco ", "Safety Vest"]), ["CASCO", "CHALECO"])

    def test_ausencia_no_es_infraccion_y_conflicto_se_abstiene(self):
        personas = {1: [0, 0, 100, 200]}
        negativo = ("NO-Hardhat", .9, [20, 0, 70, 35])
        positivo = ("Hardhat", .9, [20, 0, 70, 35])
        self.assertEqual(estados(personas, [], ["CASCO"])[1, "CASCO"], "NO_EVALUABLE")
        self.assertEqual(estados(personas, [negativo], ["CASCO"])[1, "CASCO"], "INCUMPLIMIENTO")
        self.assertEqual(estados(personas, [negativo, positivo], ["CASCO"])[1, "CASCO"], "NO_EVALUABLE")

    def test_asociacion_ambigua_no_se_asigna(self):
        resultado = estados({1: [0, 0, 100, 200], 2: [0, 0, 100, 200]},
                            [("NO-Hardhat", .9, [20, 0, 70, 35])], ["CASCO"])
        self.assertEqual(set(resultado.values()), {"NO_EVALUABLE"})

    def test_persistencia_deduplicacion_y_reaparicion(self):
        p = Persistencia(segundos=1)
        negativo = {(1, "CASCO"): "INCUMPLIMIENTO"}
        for t in [0, .5, 1, 1.5, 2]:
            p.observar(t, negativo)
        self.assertEqual(len(p.eventos), 1)
        self.assertEqual(p.eventos[0]["fin"], 2)
        p.observar(2.5, {})
        for t in [3, 3.5, 4]:
            p.observar(t, negativo)
        self.assertEqual(len(p.eventos), 2)

    def test_occlusion_y_salto_temporal_reinician(self):
        for observacion in ({}, {(1, "CASCO"): "NO_EVALUABLE"}):
            p = Persistencia(segundos=1)
            p.observar(0, {(1, "CASCO"): "INCUMPLIMIENTO"})
            p.observar(.5, observacion)
            p.observar(1, {(1, "CASCO"): "INCUMPLIMIENTO"})
            self.assertFalse(p.eventos)
        p.observar(2, {(1, "CASCO"): "INCUMPLIMIENTO"})
        self.assertFalse(p.eventos)

    def test_tiempos_invalidos(self):
        p = Persistencia()
        p.observar(0, {})
        for t in [0, -1, float("nan"), float("inf")]:
            with self.assertRaises(ValueError):
                p.observar(t, {})
