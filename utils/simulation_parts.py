"""Calculs purs pour la page de simulation des parts."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ParametresPartsSimulation:
    objectif_cash_gnf: float
    part_reservee_totale_pct: float
    part_donnee_bah_alseny_pct: float
    part_fondateur_gardee_pct: float
    part_cash_pct: float
    valorisation_totale_implicite: float
    valeur_1_pourcent_gnf: float


def calculer_parametres_parts(
    objectif_cash_gnf: float,
    part_reservee_totale_pct: float,
    part_donnee_bah_alseny_pct: float,
) -> ParametresPartsSimulation:
    """Calcule la valorisation et les parts issues de la reserve fondateur."""
    objectif_cash_gnf = float(objectif_cash_gnf)
    part_reservee_totale_pct = float(part_reservee_totale_pct)
    part_donnee_bah_alseny_pct = float(part_donnee_bah_alseny_pct)

    if part_reservee_totale_pct < 0 or part_reservee_totale_pct >= 100:
        raise ValueError("La part reservee doit etre comprise entre 0 et moins de 100 %.")
    if part_donnee_bah_alseny_pct < 0:
        raise ValueError("La part donnee ne peut pas etre negative.")
    if part_donnee_bah_alseny_pct > part_reservee_totale_pct:
        raise ValueError("La part donnee ne peut pas depasser la part reservee.")

    part_fondateur_gardee_pct = part_reservee_totale_pct - part_donnee_bah_alseny_pct
    part_cash_pct = 100.0 - part_reservee_totale_pct
    valorisation_totale_implicite = objectif_cash_gnf / (part_cash_pct / 100.0)
    valeur_1_pourcent_gnf = valorisation_totale_implicite / 100.0

    return ParametresPartsSimulation(
        objectif_cash_gnf=objectif_cash_gnf,
        part_reservee_totale_pct=part_reservee_totale_pct,
        part_donnee_bah_alseny_pct=part_donnee_bah_alseny_pct,
        part_fondateur_gardee_pct=part_fondateur_gardee_pct,
        part_cash_pct=part_cash_pct,
        valorisation_totale_implicite=valorisation_totale_implicite,
        valeur_1_pourcent_gnf=valeur_1_pourcent_gnf,
    )
