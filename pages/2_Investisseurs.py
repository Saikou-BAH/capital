"""Page Investisseurs."""

from datetime import date
from html import escape

import streamlit as st
import pandas as pd

from utils.config import STATUTS_INVESTISSEUR, OBJECTIF_SEPTEMBRE_MONTANT, OBJECTIF_DECEMBRE_MONTANT
from utils.data_loader import get_investisseurs, add_investisseur, update_investisseur, get_mouvements
from utils.calculs import (
    parts_par_investisseur, apports_par_devise_investisseur,
    evolution_apports_par_investisseur,
)
from utils.formatting import (
    inject_css, kpi_card, section_header, page_header, empty_state, fmt_gnf, fmt_pct,
    fmt_eur, fmt_taux, progress_labeled, badge_mouvement, divider, spacer, stat_row,
)
from utils.charts import (
    chart_bar_investisseurs, chart_apports_eur_par_investisseur,
    chart_evolution_apports_investisseur,
)
from utils.runtime import is_read_only_mode, read_only_notice

st.set_page_config(page_title="Investisseurs", page_icon="👥", layout="wide")
inject_css()

st.markdown(page_header("Investisseurs", "👥", "Gérez les membres du projet et suivez leurs apports."), unsafe_allow_html=True)

@st.cache_data(ttl=60)
def load():
    return get_investisseurs(), get_mouvements()

df_inv, df_mvt = load()
df_parts = parts_par_investisseur(df_mvt, df_inv)
df_apports_devise = apports_par_devise_investisseur(df_mvt, df_inv)
df_evo_apports = evolution_apports_par_investisseur(df_mvt, df_inv)
READ_ONLY = is_read_only_mode()

# ── KPIs ──────────────────────────────────────────────────────────────────────
nb_total  = len(df_inv) if not df_inv.empty else 0
nb_actifs = len(df_inv[df_inv["statut"] == "actif"]) if not df_inv.empty else 0
total_cap = df_parts["net_gnf"].sum() if not df_parts.empty else 0

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(kpi_card("Total investisseurs", str(nb_total), icon="👤", color="blue"), unsafe_allow_html=True)
with c2:
    st.markdown(kpi_card("Investisseurs actifs", str(nb_actifs), icon="✅", color="green"), unsafe_allow_html=True)
with c3:
    st.markdown(kpi_card("Total apports nets", fmt_gnf(total_cap), icon="💰", color="violet"), unsafe_allow_html=True)

st.markdown(divider(), unsafe_allow_html=True)

# ── Liste + graphique ─────────────────────────────────────────────────────────
col_list, col_chart = st.columns([3, 2])

with col_list:
    st.markdown(section_header("Liste des investisseurs", "👥", "#7C3AED"), unsafe_allow_html=True)

    if df_inv.empty:
        st.markdown(
            empty_state("👤", "Aucun investisseur", "Utilisez le formulaire ci-dessous pour ajouter le premier investisseur."),
            unsafe_allow_html=True,
        )
    else:
        if not df_parts.empty:
            df_d = df_inv.merge(
                df_parts[["investisseur_id", "net_gnf", "part_pct", "apports_gnf", "retraits_gnf"]],
                left_on="id", right_on="investisseur_id", how="left",
            )
            if not df_apports_devise.empty:
                df_d = df_d.merge(
                    df_apports_devise[["investisseur_id", "apports_eur", "apports_gnf_nat"]],
                    on="investisseur_id", how="left",
            )
            df_d["net_gnf"]  = df_d["net_gnf"].fillna(0)
            df_d["part_pct"] = df_d["part_pct"].fillna(0)
            if "apports_eur" not in df_d.columns:
                df_d["apports_eur"] = 0.0
            if "apports_gnf_nat" not in df_d.columns:
                df_d["apports_gnf_nat"] = 0.0
            df_d["apports_eur"] = df_d["apports_eur"].fillna(0)
            df_d["apports_gnf_nat"] = df_d["apports_gnf_nat"].fillna(0)
        else:
            df_d = df_inv.copy()
            df_d["net_gnf"] = df_d["part_pct"] = 0.0
            df_d["apports_eur"] = df_d["apports_gnf_nat"] = 0.0

        STATUS_DOT = {"actif": "🟢", "inactif": "🔴", "potentiel": "🟡"}
        STATUS_BG  = {"actif": "#ECFDF5", "inactif": "#FEF2F2", "potentiel": "#FFFBEB"}
        STATUS_CLR = {"actif": "#059669", "inactif": "#DC2626", "potentiel": "#D97706"}

        for _, row in df_d.iterrows():
            dot  = STATUS_DOT.get(str(row["statut"]), "⚪")
            pct  = float(row.get("part_pct", 0))
            net  = float(row.get("net_gnf", 0))
            pct_sep = net / OBJECTIF_SEPTEMBRE_MONTANT * 100 if OBJECTIF_SEPTEMBRE_MONTANT else 0.0
            pct_dec = net / OBJECTIF_DECEMBRE_MONTANT * 100 if OBJECTIF_DECEMBRE_MONTANT else 0.0
            apports_eur = float(row.get("apports_eur", 0))
            apports_gnf_nat = float(row.get("apports_gnf_nat", 0))
            sbg  = STATUS_BG.get(str(row["statut"]), "#F8FAFC")
            sclr = STATUS_CLR.get(str(row["statut"]), "#64748B")
            nom_txt = escape(str(row["nom"]))
            statut_txt = escape(str(row["statut"]))
            notes_txt = escape(str(row.get("notes", ""))[:70])
            notes_html = (
                f'<div style="font-size:.72rem;color:#94A3B8;margin-top:.4rem">{notes_txt}</div>'
                if notes_txt else ""
            )

            st.markdown(
                (
                    '<div class="card" style="margin-bottom:.6rem;padding:1rem 1.25rem">'
                    '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:.55rem">'
                    '<div style="display:flex;align-items:center;gap:.55rem">'
                    f'<div style="width:36px;height:36px;border-radius:10px;background:{sbg};display:flex;'
                    f'align-items:center;justify-content:center;font-size:1.05rem">{dot}</div>'
                    '<div>'
                    f'<div style="font-size:.92rem;font-weight:700;color:#0F172A">{nom_txt}</div>'
                    f'<div style="font-size:.68rem;font-weight:600;text-transform:uppercase;'
                    f'letter-spacing:.07em;color:{sclr};margin-top:.05rem">{statut_txt}</div>'
                    '</div>'
                    '</div>'
                    '<div style="text-align:right">'
                    f'<div style="font-size:.95rem;font-weight:800;color:#0F172A">{fmt_gnf(net)}</div>'
                    f'<div style="font-size:.7rem;color:#94A3B8">{fmt_pct(pct)} du total</div>'
                    '</div>'
                    '</div>'
                    f'{progress_labeled(pct, color="auto")}'
                    '<div style="display:grid;grid-template-columns:1fr 1fr;gap:.45rem;margin-top:.55rem">'
                    f'<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:6px;padding:.45rem .55rem">'
                    f'<div style="font-size:.62rem;font-weight:800;color:#94A3B8;text-transform:uppercase;letter-spacing:.08em">Objectif sept.</div>'
                    f'<div style="font-size:.82rem;font-weight:800;color:#0F172A;margin-top:.1rem">{fmt_pct(pct_sep)}</div>'
                    f'</div>'
                    f'<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:6px;padding:.45rem .55rem">'
                    f'<div style="font-size:.62rem;font-weight:800;color:#94A3B8;text-transform:uppercase;letter-spacing:.08em">Objectif déc.</div>'
                    f'<div style="font-size:.82rem;font-weight:800;color:#0F172A;margin-top:.1rem">{fmt_pct(pct_dec)}</div>'
                    f'</div>'
                    '</div>'
                    '<div style="display:flex;gap:.5rem;flex-wrap:wrap;margin-top:.55rem">'
                    f'<span style="font-size:.72rem;font-weight:700;color:#2563EB;background:#EFF6FF;'
                    f'padding:.22rem .45rem;border-radius:5px">{fmt_eur(apports_eur)} apportés</span>'
                    f'<span style="font-size:.72rem;font-weight:700;color:#059669;background:#ECFDF5;'
                    f'padding:.22rem .45rem;border-radius:5px">{fmt_gnf(apports_gnf_nat)} apportés</span>'
                    '</div>'
                    f'{notes_html}'
                    '</div>'
                ),
                unsafe_allow_html=True,
            )

with col_chart:
    st.markdown(section_header("Apports nets", "📊", "#059669"), unsafe_allow_html=True)
    st.markdown('<div class="card" style="padding:.75rem 1rem .5rem 1rem">', unsafe_allow_html=True)
    if not df_parts.empty:
        st.plotly_chart(chart_bar_investisseurs(df_parts), use_container_width=True)
    else:
        st.markdown(empty_state("📊", "Aucune donnée", "Les apports apparaîtront ici une fois enregistrés."), unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown(divider(), unsafe_allow_html=True)

# ── Apports par devise ────────────────────────────────────────────────────────
st.markdown(section_header("Apports par devise", "💱", "#2563EB"), unsafe_allow_html=True)

col_eur, col_evo = st.columns([2, 3])
with col_eur:
    st.markdown('<div class="card" style="padding:.75rem 1rem .5rem 1rem">', unsafe_allow_html=True)
    st.plotly_chart(chart_apports_eur_par_investisseur(df_apports_devise), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
with col_evo:
    if df_inv.empty:
        st.markdown(
            empty_state("📈", "Aucun investisseur", "Ajoutez un investisseur pour suivre ses apports."),
            unsafe_allow_html=True,
        )
    else:
        for _, inv_row in df_inv.iterrows():
            nom_inv = str(inv_row["nom"])
            st.markdown('<div class="card" style="padding:.75rem 1rem .5rem 1rem;margin-bottom:.75rem">', unsafe_allow_html=True)
            st.plotly_chart(chart_evolution_apports_investisseur(df_evo_apports, nom_inv), use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

st.markdown(divider(), unsafe_allow_html=True)

# ── Formulaire ajout ──────────────────────────────────────────────────────────
if READ_ONLY:
    read_only_notice("La gestion des investisseurs")

with st.expander("➕  Ajouter un investisseur", expanded=False):
    with st.form("form_add_inv", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nom    = st.text_input("Nom *", placeholder="Ex : Mamadou Diallo")
            statut = st.selectbox("Statut *", STATUTS_INVESTISSEUR)
        with col2:
            notes  = st.text_area("Notes", placeholder="Informations complémentaires…", height=80)
            date_creation = st.date_input("Date de création *", value=date.today())

        if st.form_submit_button("Enregistrer l'investisseur", type="primary", disabled=READ_ONLY):
            if not nom.strip():
                st.error("Le nom est obligatoire.")
            elif add_investisseur(nom.strip(), statut, notes.strip(), str(date_creation)):
                st.success(f"✅ **{nom}** ajouté avec succès.")
                st.cache_data.clear()
                st.rerun()

# ── Formulaire modification ───────────────────────────────────────────────────
if not df_inv.empty:
    with st.expander("✏️  Modifier un investisseur", expanded=False):
        noms_map = {row["id"]: row["nom"] for _, row in df_inv.iterrows()}
        cid = st.selectbox("Investisseur", list(noms_map.keys()),
                           format_func=lambda x: noms_map.get(x, x), key="sel_inv")
        if cid:
            sel = df_inv[df_inv["id"] == cid].iloc[0]
            with st.form("form_edit_inv"):
                col1, col2 = st.columns(2)
                with col1:
                    n_nom = st.text_input("Nom", value=str(sel["nom"]))
                    n_st  = st.selectbox(
                        "Statut", STATUTS_INVESTISSEUR,
                        index=STATUTS_INVESTISSEUR.index(sel["statut"])
                        if sel["statut"] in STATUTS_INVESTISSEUR else 0,
                    )
                with col2:
                    n_notes = st.text_area("Notes", value=str(sel.get("notes", "")), height=80)
                    try:
                        n_date_val = pd.Timestamp(sel.get("date_creation", "")).date()
                    except Exception:
                        n_date_val = date.today()
                    n_date_creation = st.date_input("Date de création", value=n_date_val)

                if st.form_submit_button("Mettre à jour", type="primary", disabled=READ_ONLY):
                    if update_investisseur(cid, {"nom": n_nom, "statut": n_st, "notes": n_notes, "date_creation": str(n_date_creation)}):
                        st.success("✅ Mis à jour.")
                        st.cache_data.clear()
                        st.rerun()

    with st.expander("📋 Historique des mouvements de l'investisseur", expanded=False):
        inv_choice = st.selectbox(
            "Investisseur", list(noms_map.keys()),
            format_func=lambda x: noms_map.get(x, x), key="hist_inv_sel"
        )
        if inv_choice:
            df_inv_mvt = df_mvt.copy()
            df_inv_mvt["date"] = pd.to_datetime(df_inv_mvt["date"], errors="coerce")
            df_inv_mvt["montant_converti_gnf"] = pd.to_numeric(df_inv_mvt["montant_converti_gnf"], errors="coerce").fillna(0)
            df_inv_mvt["montant_origine"] = pd.to_numeric(df_inv_mvt["montant_origine"], errors="coerce").fillna(0)
            df_inv_mvt = df_inv_mvt[df_inv_mvt["investisseur_id"] == inv_choice].sort_values("date", ascending=False)

            if df_inv_mvt.empty:
                st.info("Aucun mouvement pour cet investisseur.")
            else:
                cols = st.columns([1.4, 1.6, 2.2, 2.5, 2, 2, 2.2])
                for col, lbl in zip(cols, ["Date", "Type", "Montant GNF", "Montant origine", "Taux", "Source", "Destination"]):
                    with col:
                        st.markdown(f'<div class="th">{lbl}</div>', unsafe_allow_html=True)
                st.markdown('<hr style="border:none;border-top:1.5px solid #E2E8F0;margin:.3rem 0">', unsafe_allow_html=True)
                for _, row in df_inv_mvt.iterrows():
                    c1, c2, c3, c4, c5, c6, c7 = st.columns([1.4, 1.6, 2.2, 2.5, 2, 2, 2.2])
                    with c1:
                        st.markdown(f'<div class="row-date">{str(row["date"])[:10] if pd.notna(row["date"]) else "—"}</div>', unsafe_allow_html=True)
                    with c2:
                        st.markdown(badge_mouvement(str(row["type_mouvement"])), unsafe_allow_html=True)
                    with c3:
                        st.markdown(f'<div class="row-amount">{fmt_gnf(row["montant_converti_gnf"])}</div>', unsafe_allow_html=True)
                    with c4:
                        if str(row.get("devise_origine", "")).upper() == "EUR":
                            st.markdown(f'<div class="row-comment">{fmt_eur(row["montant_origine"])}</div>', unsafe_allow_html=True)
                        else:
                            st.markdown(f'<div class="row-comment">{row.get("montant_origine", "")} {row.get("devise_origine", "")}</div>', unsafe_allow_html=True)
                    with c5:
                        st.markdown(f'<div class="row-comment">{fmt_taux(row["taux_eur_gnf"]) if str(row.get("devise_origine","")).upper()=="EUR" else "—"}</div>', unsafe_allow_html=True)
                    with c6:
                        st.markdown(f'<div class="row-comment">{row.get("compte_source_id", "—")}</div>', unsafe_allow_html=True)
                    with c7:
                        st.markdown(f'<div class="row-comment">{row.get("compte_destination_id", "—")}</div>', unsafe_allow_html=True)
                    st.markdown('<hr style="border:none;border-top:1px solid #F8FAFC;margin:.2rem 0">', unsafe_allow_html=True)
