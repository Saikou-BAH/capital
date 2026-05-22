"""Entrée de l'application — configuration globale et navigation."""

import streamlit as st
from utils.formatting import inject_css
from utils.runtime import is_read_only_mode
from utils.data_loader import is_demo_mode

st.set_page_config(
    page_title="Capital Legend Farm",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

if is_read_only_mode():
    st.info(
        "Version lecture seule : les données affichées proviennent des CSV du dépôt. "
        "Les modifications se font en local puis via GitHub.",
        icon="🔒",
    )

if is_demo_mode():
    st.warning(
        "**Mode démonstration** — Connexion Google Sheets impossible. "
        "Les modifications ne sont pas persistées.",
        icon="⚠️",
    )

# ── Navigation ─────────────────────────────────────────────────────────────────
_dashboard     = st.Page("pages/1_Dashboard.py",                   title="Tableau de bord",         icon="📊", default=True)
_investisseurs = st.Page("pages/2_Investisseurs.py",               title="Investisseurs",            icon="👥")
_comptes       = st.Page("pages/3_Comptes.py",                     title="Comptes",                  icon="🏦")
_mouvements    = st.Page("pages/4_Mouvements.py",                  title="Mouvements",               icon="💸")
_objectifs     = st.Page("pages/5_Objectifs.py",                   title="Objectifs",                icon="🎯")
_depenses      = st.Page("pages/8_Depenses_Avant_Exploitation.py", title="Dépenses construction",    icon="🏗️")
_taux          = st.Page("pages/6_Taux_de_conversion.py",          title="Taux de conversion",        icon="💱")
_historique    = st.Page("pages/7_Historique.py",                  title="Historique",                icon="📜")

pg = st.navigation({
    "Pilotage":           [_dashboard],
    "Capital":            [_investisseurs, _comptes, _mouvements, _objectifs],
    "Avant exploitation": [_depenses],
    "Outils":             [_taux, _historique],
})
pg.run()
