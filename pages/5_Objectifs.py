"""Page Objectifs."""

import streamlit as st
import pandas as pd
from datetime import date, timedelta

from utils.data_loader import get_objectifs, get_mouvements, get_comptes, add_objectif, update_objectif
from utils.config import (
    OBJECTIF_SEPTEMBRE_ID, OBJECTIF_SEPTEMBRE_NOM, OBJECTIF_SEPTEMBRE_MONTANT, OBJECTIF_SEPTEMBRE_DATE,
    OBJECTIF_DECEMBRE_ID, OBJECTIF_DECEMBRE_NOM, OBJECTIF_DECEMBRE_MONTANT, OBJECTIF_DECEMBRE_DATE,
)
from utils.calculs import calculer_capital_total, progression_objectifs
from utils.formatting import (
    inject_css, kpi_card, section_header, page_header, empty_state,
    fmt_gnf, fmt_pct, progress_bar, divider, spacer,
)
from utils.charts import chart_objectifs_gauge
from utils.runtime import is_read_only_mode, read_only_notice

st.set_page_config(page_title="Objectifs", page_icon="🎯", layout="wide")
inject_css()

st.markdown(page_header("Objectifs", "🎯", "Suivez la progression vers les cibles de capital."), unsafe_allow_html=True)

@st.cache_data(ttl=60)
def load():
    return get_objectifs(), get_mouvements(), get_comptes()

df_obj, df_mvt, df_cpt = load()
objectifs_principaux = pd.DataFrame([
    {
        "id": OBJECTIF_SEPTEMBRE_ID,
        "nom_objectif": OBJECTIF_SEPTEMBRE_NOM,
        "montant_cible_gnf": OBJECTIF_SEPTEMBRE_MONTANT,
        "date_cible": OBJECTIF_SEPTEMBRE_DATE,
        "description": "50% du capital cible — 250 millions GNF",
        "actif": True,
    },
    {
        "id": OBJECTIF_DECEMBRE_ID,
        "nom_objectif": OBJECTIF_DECEMBRE_NOM,
        "montant_cible_gnf": OBJECTIF_DECEMBRE_MONTANT,
        "date_cible": OBJECTIF_DECEMBRE_DATE,
        "description": "100% du capital cible — 500 millions GNF",
        "actif": True,
    },
])
if df_obj is None or df_obj.empty:
    df_obj = objectifs_principaux
else:
    ids = set(df_obj["id"].astype(str)) if "id" in df_obj.columns else set()
    missing = objectifs_principaux[~objectifs_principaux["id"].astype(str).isin(ids)]
    df_obj = pd.concat([df_obj, missing], ignore_index=True)
capital = calculer_capital_total(df_mvt, df_cpt)
df_prog = progression_objectifs(df_obj, capital)
READ_ONLY = is_read_only_mode()

# ── KPIs ──────────────────────────────────────────────────────────────────────
nb_obj = len(df_obj) if df_obj is not None else 0
nb_att = len(df_prog[df_prog["atteint"]]) if df_prog is not None and not df_prog.empty and "atteint" in df_prog else 0
nb_act = len(df_obj[df_obj["actif"].astype(str).str.lower() == "true"]) if not df_obj.empty else 0

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(kpi_card("Capital actuel", fmt_gnf(capital), icon="💼", color="blue"), unsafe_allow_html=True)
with c2:
    st.markdown(kpi_card("Objectifs actifs", str(nb_act), icon="🎯", color="amber"), unsafe_allow_html=True)
with c3:
    st.markdown(kpi_card("Objectifs atteints", str(nb_att), icon="✅", color="green"), unsafe_allow_html=True)

st.markdown(divider(), unsafe_allow_html=True)

# ── Cartes objectifs ──────────────────────────────────────────────────────────
st.markdown(section_header("Suivi des objectifs", "📊", "#2563EB"), unsafe_allow_html=True)

if df_prog is not None and not df_prog.empty:
    actifs = df_prog[df_prog["actif"].astype(str).str.lower() == "true"]
    if not actifs.empty:
        for _, row in actifs.iterrows():
            pct     = float(row["progress_pct"])
            cible   = float(row["montant_cible_gnf"])
            reste   = float(row["reste_gnf"])
            atteint = bool(row["atteint"])
            date_c  = str(row.get("date_cible", ""))

            try:
                dc    = pd.Timestamp(date_c).date()
                jours = (dc - date.today()).days
                jours_txt = (
                    "✅ Atteint avant l'échéance !" if atteint else
                    f"⚠️ Dépassé de {-jours} jours" if jours < 0 else
                    f"{jours} jours restants"
                )
            except Exception:
                jours_txt = date_c

            color   = "#059669" if atteint else ("#2563EB" if pct >= 50 else "#D97706")
            bar_col = "green"  if atteint else ("blue"    if pct >= 50 else "amber")

            col_info, col_gauge = st.columns([3, 1])
            with col_info:
                st.markdown(
                    f"""<div class="obj-card">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:.6rem">
                        <div>
                            <div class="obj-card-title">{row['nom_objectif']}</div>
                            <div class="obj-card-desc">{str(row.get('description',''))[:120]}</div>
                        </div>
                        <div style="text-align:right;flex-shrink:0;margin-left:1rem">
                            <div class="obj-pct" style="color:{color}">{fmt_pct(pct)}</div>
                            <div style="font-size:.72rem;color:#94A3B8;margin-top:.15rem;font-weight:500">{jours_txt}</div>
                        </div>
                    </div>
                    {progress_bar(pct, bar_col, "10px")}
                    <div style="display:flex;gap:2.5rem;margin-top:.8rem">
                        <div>
                            <div style="font-size:.63rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:#94A3B8;margin-bottom:.1rem">Capital actuel</div>
                            <div style="font-size:.88rem;font-weight:700;color:#0F172A">{fmt_gnf(capital)}</div>
                        </div>
                        <div>
                            <div style="font-size:.63rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:#94A3B8;margin-bottom:.1rem">Cible</div>
                            <div style="font-size:.88rem;font-weight:700;color:#0F172A">{fmt_gnf(cible)}</div>
                        </div>
                        <div>
                            <div style="font-size:.63rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:#94A3B8;margin-bottom:.1rem">Reste</div>
                            <div style="font-size:.88rem;font-weight:700;color:{'#059669' if atteint else '#DC2626'}">{fmt_gnf(reste) if not atteint else '—'}</div>
                        </div>
                        <div>
                            <div style="font-size:.63rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:#94A3B8;margin-bottom:.1rem">Échéance</div>
                            <div style="font-size:.88rem;font-weight:700;color:#0F172A">{date_c}</div>
                        </div>
                    </div>
                    </div>""",
                    unsafe_allow_html=True,
                )
            with col_gauge:
                st.markdown(spacer("0.5rem"), unsafe_allow_html=True)
                st.markdown('<div class="card" style="padding:.25rem">', unsafe_allow_html=True)
                st.plotly_chart(chart_objectifs_gauge(row["nom_objectif"], pct, color), use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

            st.markdown(spacer("0.25rem"), unsafe_allow_html=True)
    else:
        st.success("🎉 Tous les objectifs actifs sont atteints !")
else:
    st.markdown(
        empty_state("🎯", "Aucun objectif défini", "Créez votre premier objectif ci-dessous pour suivre la progression."),
        unsafe_allow_html=True,
    )

st.markdown(divider(), unsafe_allow_html=True)

# ── Formulaire ajout ──────────────────────────────────────────────────────────
if READ_ONLY:
    read_only_notice("La gestion des objectifs")

with st.expander("➕  Créer un objectif", expanded=False):
    with st.form("form_add_obj", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nom       = st.text_input("Nom *", placeholder="Ex : Objectif Septembre 2026")
            cible_gnf = st.number_input("Montant cible (GNF) *", min_value=0.0,
                                        step=1_000_000.0, format="%.0f")
        with col2:
            date_cib  = st.date_input("Date cible *", value=date.today() + timedelta(days=365))
            actif     = st.checkbox("Objectif actif", value=True)
        description = st.text_area("Description", height=80)

        if st.form_submit_button("Créer l'objectif", type="primary", disabled=READ_ONLY):
            if not nom.strip():
                st.error("Le nom est obligatoire.")
            elif cible_gnf <= 0:
                st.error("Le montant doit être supérieur à 0.")
            elif add_objectif(nom.strip(), cible_gnf, str(date_cib), description.strip(), actif):
                st.success(f"✅ Objectif **{nom}** créé.")
                st.cache_data.clear()
                st.rerun()

# ── Formulaire modification ───────────────────────────────────────────────────
if df_obj is not None and not df_obj.empty:
    with st.expander("✏️  Modifier un objectif", expanded=False):
        obj_map = {row["id"]: row["nom_objectif"] for _, row in df_obj.iterrows()}
        choix   = st.selectbox("Objectif", list(obj_map.keys()),
                               format_func=lambda x: obj_map.get(x, x))
        if choix:
            sel = df_obj[df_obj["id"] == choix].iloc[0]
            with st.form("form_edit_obj"):
                col1, col2 = st.columns(2)
                with col1:
                    n_nom = st.text_input("Nom", value=str(sel["nom_objectif"]))
                    n_cib = st.number_input("Montant cible (GNF)", value=float(sel["montant_cible_gnf"]),
                                            step=1_000_000.0, format="%.0f")
                with col2:
                    try:    dc_val = pd.Timestamp(sel["date_cible"]).date()
                    except: dc_val = date.today()
                    n_date = st.date_input("Date cible", value=dc_val)
                    n_act  = st.checkbox("Actif", value=str(sel["actif"]).lower() == "true")
                n_desc = st.text_area("Description", value=str(sel.get("description", "")), height=80)

                if st.form_submit_button("Mettre à jour", type="primary", disabled=READ_ONLY):
                    if update_objectif(choix, {
                        "nom_objectif": n_nom, "montant_cible_gnf": n_cib,
                        "date_cible": str(n_date), "actif": str(n_act), "description": n_desc,
                    }):
                        st.success("✅ Mis à jour.")
                        st.cache_data.clear()
                        st.rerun()
