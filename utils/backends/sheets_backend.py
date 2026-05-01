"""
Backend Google Sheets — stockage cloud via gspread.

Mode production pour Streamlit Community Cloud ou tout environnement avec
accès à un service account Google.
Si les credentials sont absents, retombe sur un stockage vide en mémoire
(st.session_state) — aucune donnée fictive.
"""

import os
import uuid
from datetime import datetime, date

import gspread
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

from utils.config import (
    COLS_COMPTES, COLS_INVESTISSEURS, COLS_MOUVEMENTS,
    COLS_OBJECTIFS, COLS_TAUX,
    SHEET_COMPTES, SHEET_INVESTISSEURS, SHEET_MOUVEMENTS,
    SHEET_OBJECTIFS, SHEET_TAUX,
)

load_dotenv()

_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Aucune donnée préremplie — l'application démarre vide dans tous les modes.


# ── Connexion ─────────────────────────────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def _get_client():
    try:
        if "gcp_service_account" in st.secrets:
            creds = Credentials.from_service_account_info(
                dict(st.secrets["gcp_service_account"]), scopes=_SCOPES
            )
        else:
            path = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
            if not os.path.exists(path):
                return None
            creds = Credentials.from_service_account_file(path, scopes=_SCOPES)
        return gspread.authorize(creds)
    except Exception:
        return None


def _get_spreadsheet():
    client = _get_client()
    if not client:
        return None
    sid = os.getenv("SPREADSHEET_ID") or st.secrets.get("spreadsheet_id", "")
    if not sid:
        return None
    try:
        return client.open_by_key(sid)
    except Exception:
        return None


def is_demo_mode() -> bool:
    return _get_spreadsheet() is None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _init_session_demo():
    """Initialise un stockage vide en mémoire (sans données fictives)."""
    if "_sheets_demo" not in st.session_state:
        from utils.config import SHEET_INVESTISSEURS, SHEET_COMPTES, SHEET_MOUVEMENTS, SHEET_OBJECTIFS, SHEET_TAUX
        st.session_state["_sheets_demo"] = {
            SHEET_INVESTISSEURS: [],
            SHEET_COMPTES: [],
            SHEET_MOUVEMENTS: [],
            SHEET_OBJECTIFS: [],
            SHEET_TAUX: [],
        }


def _ensure_ws(ss, name: str, cols: list[str]):
    try:
        return ss.worksheet(name)
    except gspread.WorksheetNotFound:
        ws = ss.add_worksheet(title=name, rows=2000, cols=len(cols))
        ws.append_row(cols)
        return ws


def _read_sheet(name: str, cols: list[str]) -> pd.DataFrame:
    ss = _get_spreadsheet()
    if ss is None:
        _init_session_demo()
        rows = st.session_state["_sheets_demo"].get(name, [])
        return pd.DataFrame(rows, columns=cols) if rows else pd.DataFrame(columns=cols)
    ws = _ensure_ws(ss, name, cols)
    rows = ws.get_all_records(expected_headers=cols)
    if not rows:
        return pd.DataFrame(columns=cols)
    df = pd.DataFrame(rows)
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    return df[cols]


def _add_row(name: str, cols: list[str], row: dict) -> bool:
    ss = _get_spreadsheet()
    if ss is None:
        _init_session_demo()
        st.session_state["_sheets_demo"][name].append(row)
        return True
    try:
        ws = _ensure_ws(ss, name, cols)
        ws.append_row([str(row.get(c, "")) for c in cols])
        return True
    except Exception as e:
        st.error(f"Erreur Google Sheets : {e}")
        return False


def _update_row(name: str, cols: list[str], row_id: str, updates: dict) -> bool:
    ss = _get_spreadsheet()
    if ss is None:
        _init_session_demo()
        for item in st.session_state["_sheets_demo"].get(name, []):
            if item.get("id") == row_id:
                item.update(updates)
        return True
    try:
        ws = _ensure_ws(ss, name, cols)
        records = ws.get_all_records(expected_headers=cols)
        for i, rec in enumerate(records, start=2):
            if str(rec.get("id")) == row_id:
                for col, val in updates.items():
                    if col in cols:
                        ws.update_cell(i, cols.index(col) + 1, str(val))
        return True
    except Exception as e:
        st.error(f"Erreur Google Sheets : {e}")
        return False


def _delete_row(name: str, cols: list[str], row_id: str) -> bool:
    ss = _get_spreadsheet()
    if ss is None:
        _init_session_demo()
        rows = st.session_state["_sheets_demo"].get(name, [])
        st.session_state["_sheets_demo"][name] = [row for row in rows if row.get("id") != row_id]
        return True
    try:
        ws = _ensure_ws(ss, name, cols)
        records = ws.get_all_records(expected_headers=cols)
        for i, rec in enumerate(records, start=2):
            if str(rec.get("id")) == row_id:
                ws.delete_row(i)
                return True
        return False
    except Exception as e:
        st.error(f"Erreur Google Sheets : {e}")
        return False


def _new_id(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:8]}"


# ── API publique ──────────────────────────────────────────────────────────────

def get_investisseurs() -> pd.DataFrame:
    return _read_sheet(SHEET_INVESTISSEURS, COLS_INVESTISSEURS)

def add_investisseur(nom: str, statut: str, notes: str = "", date_creation: str | None = None) -> bool:
    return _add_row(SHEET_INVESTISSEURS, COLS_INVESTISSEURS, {
        "id": _new_id("inv-"), "nom": nom, "statut": statut,
        "notes": notes, "date_creation": str(date_creation or date.today()),
    })

def update_investisseur(inv_id: str, updates: dict) -> bool:
    return _update_row(SHEET_INVESTISSEURS, COLS_INVESTISSEURS, inv_id, updates)


def get_comptes() -> pd.DataFrame:
    return _read_sheet(SHEET_COMPTES, COLS_COMPTES)

def add_compte(nom: str, investisseur_id: str, pays: str, devise: str,
               type_compte: str, actif: bool = True, description: str = "",
               date_creation: str | None = None) -> bool:
    return _add_row(SHEET_COMPTES, COLS_COMPTES, {
        "id": _new_id("cpt-"), "nom": nom, "investisseur_id": investisseur_id,
        "pays": pays, "devise": devise, "type_compte": type_compte,
        "actif": str(actif), "description": description,
        "date_creation": str(date_creation or date.today()),
    })

def update_compte(cpt_id: str, updates: dict) -> bool:
    return _update_row(SHEET_COMPTES, COLS_COMPTES, cpt_id, updates)


def get_mouvements() -> pd.DataFrame:
    return _read_sheet(SHEET_MOUVEMENTS, COLS_MOUVEMENTS)

def add_mouvement(date_mvt, type_mouvement, investisseur_id, montant_origine,
                  devise_origine, taux_eur_gnf, montant_converti_gnf,
                  compte_source_id="", compte_destination_id="",
                  commentaire="", compte_dans_capital=True) -> bool:
    taux_final = taux_eur_gnf if devise_origine == "EUR" else 1
    return _add_row(SHEET_MOUVEMENTS, COLS_MOUVEMENTS, {
        "id": _new_id("mvt-"), "date": str(date_mvt),
        "type_mouvement": type_mouvement, "investisseur_id": investisseur_id,
        "compte_source_id": compte_source_id, "compte_destination_id": compte_destination_id,
        "montant_origine": montant_origine, "devise_origine": devise_origine,
        "taux_eur_gnf": taux_final, "montant_converti_gnf": montant_converti_gnf,
        "commentaire": commentaire, "compte_dans_capital": str(compte_dans_capital),
        "date_creation": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })


def delete_mouvement(mvt_id: str) -> bool:
    return _delete_row(SHEET_MOUVEMENTS, COLS_MOUVEMENTS, mvt_id)


def get_objectifs() -> pd.DataFrame:
    return _read_sheet(SHEET_OBJECTIFS, COLS_OBJECTIFS)

def add_objectif(nom, montant_cible_gnf, date_cible, description="", actif=True) -> bool:
    return _add_row(SHEET_OBJECTIFS, COLS_OBJECTIFS, {
        "id": _new_id("obj-"), "nom_objectif": nom,
        "montant_cible_gnf": montant_cible_gnf, "date_cible": date_cible,
        "description": description, "actif": str(actif),
    })

def update_objectif(obj_id: str, updates: dict) -> bool:
    return _update_row(SHEET_OBJECTIFS, COLS_OBJECTIFS, obj_id, updates)


def get_taux() -> pd.DataFrame:
    return _read_sheet(SHEET_TAUX, COLS_TAUX)

def add_taux(date_taux: str, eur_to_gnf: float, commentaire: str = "") -> bool:
    return _add_row(SHEET_TAUX, COLS_TAUX, {
        "id": _new_id("tx-"), "date_taux": date_taux, "eur_to_gnf": eur_to_gnf,
        "commentaire": commentaire, "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })


def export_csv(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False, sep=";", decimal=",", encoding="utf-8-sig").encode("utf-8-sig")
