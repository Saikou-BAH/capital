import unittest

import pandas as pd

from utils.calculs import (
    calculer_capital_breakdown,
    evolution_capital,
    repartition_par_devise,
    repartition_par_pays,
)


class CalculsCapitalTest(unittest.TestCase):
    def setUp(self):
        self.df_comptes = pd.DataFrame(
            [
                {
                    "id": "cpt-cec777b6",
                    "nom": "BNP",
                    "pays": "France",
                    "devise": "EUR",
                },
                {
                    "id": "cpt-0d06dbcd",
                    "nom": "YMO",
                    "pays": "Guinée",
                    "devise": "GNF",
                }
            ]
        )
        self.df_mouvements = pd.DataFrame(
            [
                {
                    "id": "mvt-8c5b86cc",
                    "date": "2026-05-01",
                    "type_mouvement": "apport",
                    "investisseur_id": "inv-6f12fde9",
                    "compte_source_id": "",
                    "compte_destination_id": "cpt-cec777b6",
                    "montant_origine": 1000.0,
                    "devise_origine": "EUR",
                    "taux_eur_gnf": 10500.0,
                    "montant_converti_gnf": 10500000.0,
                    "compte_dans_capital": True,
                }
            ]
        )

    def test_apport_eur_reste_valorise_en_gnf(self):
        breakdown = calculer_capital_breakdown(self.df_mouvements, self.df_comptes)

        self.assertEqual(breakdown["total_eur"], 1000.0)
        self.assertEqual(breakdown["total_gnf"], 0.0)
        self.assertEqual(breakdown["valorisation_eur_gnf"], 10500000.0)
        self.assertEqual(breakdown["capital_total"], 10500000.0)

    def test_graph_data_include_apport_eur(self):
        evolution = evolution_capital(self.df_mouvements, self.df_comptes)
        pays = repartition_par_pays(self.df_mouvements, self.df_comptes)
        devise = repartition_par_devise(self.df_mouvements, self.df_comptes)

        self.assertEqual(evolution.iloc[-1]["capital_cumule"], 10500000.0)
        self.assertEqual(pays.iloc[0]["pays"], "France")
        self.assertEqual(pays.iloc[0]["montant_gnf"], 10500000.0)
        self.assertEqual(devise.iloc[0]["devise"], "EUR")
        self.assertEqual(devise.iloc[0]["montant_gnf"], 10500000.0)

    def test_repartition_after_full_eur_to_gnf_transfer(self):
        df_mouvements = pd.concat(
            [
                self.df_mouvements,
                pd.DataFrame(
                    [
                        {
                            "id": "mvt-845f6cfc",
                            "date": "2026-05-01",
                            "type_mouvement": "transfert",
                            "investisseur_id": "inv-6f12fde9",
                            "compte_source_id": "cpt-cec777b6",
                            "compte_destination_id": "cpt-0d06dbcd",
                            "montant_origine": 1000.0,
                            "devise_origine": "EUR",
                            "taux_eur_gnf": 10500.0,
                            "montant_converti_gnf": 10500000.0,
                            "compte_dans_capital": False,
                        }
                    ]
                ),
            ],
            ignore_index=True,
        )

        pays = repartition_par_pays(df_mouvements, self.df_comptes)
        devise = repartition_par_devise(df_mouvements, self.df_comptes)

        self.assertEqual(len(pays), 1)
        self.assertEqual(pays.iloc[0]["pays"], "Guinée")
        self.assertEqual(pays.iloc[0]["montant_gnf"], 10500000.0)
        self.assertEqual(len(devise), 1)
        self.assertEqual(devise.iloc[0]["devise"], "GNF")
        self.assertEqual(devise.iloc[0]["montant_gnf"], 10500000.0)

    def test_depense_reduit_le_capital_net(self):
        df_mouvements = pd.concat(
            [
                self.df_mouvements,
                pd.DataFrame(
                    [
                        {
                            "id": "mvt-transfer",
                            "date": "2026-05-02",
                            "type_mouvement": "transfert",
                            "investisseur_id": "inv-6f12fde9",
                            "compte_source_id": "cpt-cec777b6",
                            "compte_destination_id": "cpt-0d06dbcd",
                            "montant_origine": 1000.0,
                            "devise_origine": "EUR",
                            "taux_eur_gnf": 10500.0,
                            "montant_converti_gnf": 10500000.0,
                            "compte_dans_capital": False,
                        },
                        {
                            "id": "mvt-depense",
                            "date": "2026-05-03",
                            "type_mouvement": "depense",
                            "investisseur_id": "inv-6f12fde9",
                            "compte_source_id": "cpt-0d06dbcd",
                            "compte_destination_id": "",
                            "montant_origine": 500000.0,
                            "devise_origine": "GNF",
                            "taux_eur_gnf": 1.0,
                            "montant_converti_gnf": 500000.0,
                            "compte_dans_capital": True,
                        },
                    ]
                ),
            ],
            ignore_index=True,
        )

        breakdown = calculer_capital_breakdown(df_mouvements, self.df_comptes)
        evolution = evolution_capital(df_mouvements, self.df_comptes)

        self.assertEqual(breakdown["capital_total"], 10000000.0)
        self.assertEqual(evolution.iloc[-1]["capital_cumule"], 10000000.0)


if __name__ == "__main__":
    unittest.main()
