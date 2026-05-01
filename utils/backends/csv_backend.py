"""
Backend CSV — stockage local dans data/*.csv

Mode principal pour le développement local. Pas de connexion externe requise.
Les fichiers CSV sont créés vides (en-têtes uniquement) au premier lancement.
"""

import os
import uuid
from datetime import datetime, date
from pathlib import Path

import pandas as pd

from utils.config import (
    COLS_COMPTES, COLS_INVESTISSEURS, COLS_MOUVEMENTS,
    COLS_OBJECTIFS, COLS_TAUX,
    SHEET_COMPTES, SHEET_INVESTISSEURS, SHEET_MOUVEMENTS,
    SHEET_OBJECTIFS, SHEET_TAUX,
)

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


# Aucune donnée préremplie — l'application démarre vide.
# Les CSV sont créés avec uniquement les colonnes en-têtes.


# ── Helpers CSV ───────────────────────────────────────────────────────────────

def _csv_path(sheet_name: str) -> Path:
    return DATA_DIR / f"{sheet_name}.csv"


def _ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _init_csv(sheet_name: str, cols: list[str]):
    """Crée le CSV vide (en-têtes uniquement) s'il n'existe pas encore."""
    path = _csv_path(sheet_name)
    if not path.exists():
        _ensure_data_dir()
        pd.DataFrame(columns=cols).to_csv(path, index=False, sep=";", encoding="utf-8-sig")


def _read_csv(sheet_name: str, cols: list[str]) -> pd.DataFrame:
    """Lit un CSV et renvoie un DataFrame avec les colonnes attendues."""
    _init_csv(sheet_name, cols)
    path = _csv_path(sheet_name)
    try:
        df = pd.read_csv(path, sep=";", encoding="utf-8-sig", dtype=str)
    except Exception:
        return pd.DataFrame(columns=cols)
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    return df[cols].fillna("")


def _append_csv(sheet_name: str, cols: list[str], row: dict) -> bool:
    """Ajoute une ligne à un CSV."""
    _init_csv(sheet_name, cols)
    path = _csv_path(sheet_name)
    new_row = pd.DataFrame([{c: str(row.get(c, "")) for c in cols}])
    try:
        df = _read_csv(sheet_name, cols)
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(path, index=False, sep=";", encoding="utf-8-sig")
        return True
    except Exception as e:
        print(f"[CSV backend] Erreur écriture {sheet_name}: {e}")
        return False


def _update_csv(sheet_name: str, cols: list[str], row_id: str, updates: dict) -> bool:
    """Met à jour la ligne dont la colonne 'id' vaut row_id."""
    path = _csv_path(sheet_name)
    try:
        df = _read_csv(sheet_name, cols)
        mask = df["id"] == row_id
        if mask.sum() == 0:
            return False
        for col, val in updates.items():
            if col in df.columns:
                df.loc[mask, col] = str(val)
        df.to_csv(path, index=False, sep=";", encoding="utf-8-sig")
        return True
    except Exception as e:
        print(f"[CSV backend] Erreur mise à jour {sheet_name}: {e}")
        return False


def _delete_csv(sheet_name: str, cols: list[str], row_id: str) -> bool:
    """Supprime la ligne dont la colonne 'id' vaut row_id."""
    path = _csv_path(sheet_name)
    try:
        df = _read_csv(sheet_name, cols)
        if row_id not in df["id"].values:
            return False
        df = df[df["id"] != row_id]
        df.to_csv(path, index=False, sep=";", encoding="utf-8-sig")
        return True
    except Exception as e:
        print(f"[CSV backend] Erreur suppression {sheet_name}: {e}")
        return False


def _new_id(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:8]}"


# ── is_demo_mode ──────────────────────────────────────────────────────────────

def is_demo_mode() -> bool:
    """CSV est un vrai backend local — pas du mode démo."""
    return False


# ── API publique — Investisseurs ───────────────────────────────────────────────

def get_investisseurs() -> pd.DataFrame:
    return _read_csv(SHEET_INVESTISSEURS, COLS_INVESTISSEURS)


def add_investisseur(nom: str, statut: str, notes: str = "", date_creation: str | None = None) -> bool:
    row = {
        "id": _new_id("inv-"),
        "nom": nom,
        "statut": statut,
        "notes": notes,
        "date_creation": str(date_creation or date.today()),
    }
    return _append_csv(SHEET_INVESTISSEURS, COLS_INVESTISSEURS, row)


def update_investisseur(inv_id: str, updates: dict) -> bool:
    return _update_csv(SHEET_INVESTISSEURS, COLS_INVESTISSEURS, inv_id, updates)


# ── API publique — Comptes ─────────────────────────────────────────────────────

def get_comptes() -> pd.DataFrame:
    return _read_csv(SHEET_COMPTES, COLS_COMPTES)


def add_compte(nom: str, investisseur_id: str, pays: str, devise: str,
               type_compte: str, actif: bool = True, description: str = "",
               date_creation: str | None = None) -> bool:
    row = {
        "id": _new_id("cpt-"),
        "nom": nom,
        "investisseur_id": investisseur_id,
        "pays": pays,
        "devise": devise,
        "type_compte": type_compte,
        "actif": str(actif),
        "description": description,
        "date_creation": str(date_creation or date.today()),
    }
    return _append_csv(SHEET_COMPTES, COLS_COMPTES, row)


def update_compte(cpt_id: str, updates: dict) -> bool:
    return _update_csv(SHEET_COMPTES, COLS_COMPTES, cpt_id, updates)


# ── API publique — Mouvements ─────────────────────────────────────────────────

def get_mouvements() -> pd.DataFrame:
    return _read_csv(SHEET_MOUVEMENTS, COLS_MOUVEMENTS)


def add_mouvement(
    date_mvt: str,
    type_mouvement: str,
    investisseur_id: str,
    montant_origine: float,
    devise_origine: str,
    taux_eur_gnf: float,
    montant_converti_gnf: float,
    compte_source_id: str = "",
    compte_destination_id: str = "",
    commentaire: str = "",
    compte_dans_capital: bool = True,
) -> bool:
    # Pour les mouvements en GNF, le taux est 1 (pas de conversion)
    taux_final = taux_eur_gnf if devise_origine == "EUR" else 1
    row = {
        "id": _new_id("mvt-"),
        "date": date_mvt,
        "type_mouvement": type_mouvement,
        "investisseur_id": investisseur_id,
        "compte_source_id": compte_source_id,
        "compte_destination_id": compte_destination_id,
        "montant_origine": montant_origine,
        "devise_origine": devise_origine,
        "taux_eur_gnf": taux_final,
        "montant_converti_gnf": montant_converti_gnf,
        "commentaire": commentaire,
        "compte_dans_capital": str(compte_dans_capital),
        "date_creation": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    return _append_csv(SHEET_MOUVEMENTS, COLS_MOUVEMENTS, row)


def delete_mouvement(mvt_id: str) -> bool:
    return _delete_csv(SHEET_MOUVEMENTS, COLS_MOUVEMENTS, mvt_id)


# ── API publique — Objectifs ──────────────────────────────────────────────────

def get_objectifs() -> pd.DataFrame:
    return _read_csv(SHEET_OBJECTIFS, COLS_OBJECTIFS)


def add_objectif(nom: str, montant_cible_gnf: float, date_cible: str,
                 description: str = "", actif: bool = True) -> bool:
    row = {
        "id": _new_id("obj-"),
        "nom_objectif": nom,
        "montant_cible_gnf": montant_cible_gnf,
        "date_cible": date_cible,
        "description": description,
        "actif": str(actif),
    }
    return _append_csv(SHEET_OBJECTIFS, COLS_OBJECTIFS, row)


def update_objectif(obj_id: str, updates: dict) -> bool:
    return _update_csv(SHEET_OBJECTIFS, COLS_OBJECTIFS, obj_id, updates)


# ── API publique — Taux de conversion ────────────────────────────────────────

def get_taux() -> pd.DataFrame:
    return _read_csv(SHEET_TAUX, COLS_TAUX)


def add_taux(date_taux: str, eur_to_gnf: float, commentaire: str = "") -> bool:
    """
    Enregistre un nouveau taux EUR→GNF.
    Colonnes : id, date_taux, eur_to_gnf, commentaire, created_at
    """
    row = {
        "id": _new_id("tx-"),
        "date_taux": date_taux,
        "eur_to_gnf": eur_to_gnf,
        "commentaire": commentaire,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    return _append_csv(SHEET_TAUX, COLS_TAUX, row)


# ── Export CSV ────────────────────────────────────────────────────────────────

def export_csv(df: pd.DataFrame) -> bytes:
    """Exporte un DataFrame en bytes CSV (UTF-8 BOM, séparateur point-virgule)."""
    return df.to_csv(index=False, sep=";", decimal=",", encoding="utf-8-sig").encode("utf-8-sig")
