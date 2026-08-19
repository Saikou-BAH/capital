import unittest

from utils.simulation_parts import calculer_parametres_parts


class SimulationPartsTest(unittest.TestCase):
    def test_objectif_septembre_250m_avec_reserve_15_et_don_5(self):
        params = calculer_parametres_parts(250_000_000, 15, 5)

        self.assertEqual(params.part_fondateur_gardee_pct, 10)
        self.assertEqual(params.part_cash_pct, 85)
        self.assertEqual(round(params.valorisation_totale_implicite), 294_117_647)
        self.assertEqual(round(params.valeur_1_pourcent_gnf), 2_941_176)

    def test_objectif_decembre_500m_avec_reserve_15_et_don_5(self):
        params = calculer_parametres_parts(500_000_000, 15, 5)

        self.assertEqual(params.part_fondateur_gardee_pct, 10)
        self.assertEqual(params.part_cash_pct, 85)
        self.assertEqual(round(params.valorisation_totale_implicite), 588_235_294)
        self.assertEqual(round(params.valeur_1_pourcent_gnf), 5_882_353)


if __name__ == "__main__":
    unittest.main()
