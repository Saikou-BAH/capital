"""
Couche d'accès aux données — routage vers le backend actif.

Le backend est déterminé par la variable d'environnement BACKEND :
  - "csv"    (défaut) → stockage local dans data/*.csv
  - "sheets"          → Google Sheets (nécessite credentials + SPREADSHEET_ID)

Pour changer de backend, il suffit de modifier BACKEND dans .env.
Toutes les pages de l'app importent uniquement depuis ce module.
"""

import os
from dotenv import load_dotenv
from utils.runtime import is_read_only_mode

load_dotenv()

_BACKEND = os.getenv("BACKEND", "csv").strip().lower()

if _BACKEND == "sheets":
    from utils.backends.sheets_backend import (
        get_investisseurs, add_investisseur, update_investisseur,
        get_comptes, add_compte, update_compte,
        get_mouvements, add_mouvement, delete_mouvement,
        get_objectifs, add_objectif, update_objectif,
        get_taux, add_taux,
        is_demo_mode, export_csv,
    )
else:
    # Mode par défaut : CSV local
    from utils.backends.csv_backend import (
        get_investisseurs, add_investisseur, update_investisseur,
        get_comptes, add_compte, update_compte,
        get_mouvements, add_mouvement, delete_mouvement,
        get_objectifs, add_objectif, update_objectif,
        get_taux, add_taux,
        is_demo_mode, export_csv,
    )


def get_backend_name() -> str:
    """Retourne le nom du backend actif pour affichage dans l'UI."""
    return "Google Sheets" if _BACKEND == "sheets" else "CSV local"


def _blocked_write(*args, **kwargs) -> bool:
    print("[data_loader] Écriture bloquée : application en mode lecture seule.")
    return False


if is_read_only_mode():
    add_investisseur = _blocked_write
    update_investisseur = _blocked_write
    add_compte = _blocked_write
    update_compte = _blocked_write
    add_mouvement = _blocked_write
    delete_mouvement = _blocked_write
    add_objectif = _blocked_write
    update_objectif = _blocked_write
    add_taux = _blocked_write
