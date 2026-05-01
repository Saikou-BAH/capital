"""Page Comptes — création, modification, soldes."""

from datetime import date

import streamlit as st
import pandas as pd

from utils.config import TYPES_COMPTE, PAYS_DISPONIBLES, DEVISES
from utils.data_loader import get_comptes, get_investisseurs, get_mouvements, add_compte, update_compte
from utils.calculs import (
    soldes_par_compte, calculer_capital_breakdown, valeurs_par_compte,
    repartition_par_devise,
)
from utils.formatting import (
    inject_css, kpi_card, section_header, page_header, empty_state,
    fmt_gnf, fmt_eur, fmt_taux, badge_mouvement, divider, spacer,
)
from utils.charts import chart_valeurs_par_compte, chart_repartition_devise
from utils.runtime import is_read_only_mode, read_only_notice

st.set_page_config(page_title="Comptes", page_icon="🏦", layout="wide")
inject_css()

st.markdown(page_header("Comptes", "🏦", "Gérez les comptes bancaires et de trésorerie du projet."), unsafe_allow_html=True)

@st.cache_data(ttl=60)
def load():
    return get_comptes(), get_investisseurs(), get_mouvements()

df_cpt, df_inv, df_mvt = load()
df_soldes = soldes_par_compte(df_mvt, df_cpt)
df_valeurs = valeurs_par_compte(df_mvt, df_cpt)
df_devise = repartition_par_devise(df_mvt, df_cpt)
capital_breakdown = calculer_capital_breakdown(df_mvt, df_cpt)
total_valorise_gnf = capital_breakdown["capital_total"]
READ_ONLY = is_read_only_mode()

noms_inv = {}
if df_inv is not None and not df_inv.empty:
    noms_inv = df_inv.set_index("id")["nom"].to_dict()

# ── KPIs ──────────────────────────────────────────────────────────────────────
nb_comptes = len(df_cpt)
nb_actifs  = len(df_cpt[df_cpt["actif"].astype(str).str.lower() == "true"]) if not df_cpt.empty else 0

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(kpi_card("Total comptes", str(nb_comptes), icon="🏦", color="blue"), unsafe_allow_html=True)
with c2:
    st.markdown(kpi_card("Comptes actifs", str(nb_actifs), icon="✅", color="green"), unsafe_allow_html=True)
with c3:
    st.markdown(kpi_card("Capital valorisé total", fmt_gnf(total_valorise_gnf), icon="💼", color="violet"), unsafe_allow_html=True)

st.markdown(divider(), unsafe_allow_html=True)

# ── Graphiques comptes ───────────────────────────────────────────────────────
st.markdown(section_header("Vue graphique des comptes", "📊", "#059669"), unsafe_allow_html=True)

g1, g2 = st.columns([3, 2])
with g1:
    st.markdown('<div class="card" style="padding:.75rem 1rem .5rem 1rem">', unsafe_allow_html=True)
    st.plotly_chart(chart_valeurs_par_compte(df_valeurs), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
with g2:
    st.markdown('<div class="card" style="padding:.75rem 1rem .5rem 1rem">', unsafe_allow_html=True)
    st.plotly_chart(chart_repartition_devise(df_devise), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown(divider(), unsafe_allow_html=True)

# ── Filtres ───────────────────────────────────────────────────────────────────
f1, f2, f3, f4 = st.columns(4)
with f1:
    filtre_pays   = st.multiselect("Pays", PAYS_DISPONIBLES)
with f2:
    filtre_devise = st.multiselect("Devise", DEVISES)
with f3:
    filtre_type   = st.multiselect("Type", TYPES_COMPTE)
with f4:
    filtre_actif  = st.selectbox("Statut", ["Tous", "Actif", "Inactif"])

st.markdown(spacer("0.5rem"), unsafe_allow_html=True)

# ── Liste comptes ─────────────────────────────────────────────────────────────
if df_soldes is not None and not df_soldes.empty and "solde_gnf" in df_soldes.columns:
    df_display = df_cpt.merge(df_soldes[["id", "solde_gnf"]], on="id", how="left")
    df_display["solde_gnf"] = df_display["solde_gnf"].fillna(0)
else:
    df_display = df_cpt.copy()
    df_display["solde_gnf"] = 0

if filtre_pays:
    df_display = df_display[df_display["pays"].isin(filtre_pays)]
if filtre_devise:
    df_display = df_display[df_display["devise"].isin(filtre_devise)]
if filtre_type:
    df_display = df_display[df_display["type_compte"].isin(filtre_type)]
if filtre_actif == "Actif":
    df_display = df_display[df_display["actif"].astype(str).str.lower() == "true"]
elif filtre_actif == "Inactif":
    df_display = df_display[df_display["actif"].astype(str).str.lower() != "true"]

st.markdown(section_header("Liste des comptes", "🏦", "#2563EB"), unsafe_allow_html=True)

if df_display.empty:
    st.markdown(
        empty_state("🏦", "Aucun compte trouvé", "Aucun compte ne correspond à ces filtres, ou aucun compte n'a encore été créé."),
        unsafe_allow_html=True,
    )
else:
    ICONES_TYPE = {"banque": "🏦", "espèces": "💵", "mobile money": "📱", "YMO": "📲", "autre": "📂"}
    ICONES_PAYS = {"France": "🇫🇷", "Guinée": "🇬🇳", "Belgique": "🇧🇪", "Sénégal": "🇸🇳"}
    DEVISE_CLR  = {"EUR": "#2563EB", "GNF": "#059669"}

    # En-têtes
    h1, h2, h3, h4, h5, h6 = st.columns([3, 2.5, 1.2, 1.8, 2, 2.5])
    for col, lbl in zip([h1, h2, h3, h4, h5, h6], ["Compte", "Solde estimé", "Devise", "Statut", "Propriétaire", "Description"]):
        with col:
            st.markdown(f'<div class="th">{lbl}</div>', unsafe_allow_html=True)
    st.markdown('<hr style="border:none;border-top:1.5px solid #E2E8F0;margin:.3rem 0 .5rem 0">', unsafe_allow_html=True)

    for _, row in df_display.iterrows():
        is_actif = str(row["actif"]).lower() == "true"
        icone    = ICONES_TYPE.get(row["type_compte"], "📂")
        drapeau  = ICONES_PAYS.get(row["pays"], "🌍")
        proprio  = noms_inv.get(row.get("investisseur_id", ""), "—")
        solde    = row["solde_gnf"]
        dev      = str(row["devise"]).upper()
        dev_clr  = DEVISE_CLR.get(dev, "#64748B")
        solde_fmt = fmt_eur(solde) if dev == "EUR" else fmt_gnf(solde)
        solde_clr = "#059669" if solde > 0 else ("#DC2626" if solde < 0 else "#94A3B8")

        c1, c2, c3, c4, c5, c6 = st.columns([3, 2.5, 1.2, 1.8, 2, 2.5])
        with c1:
            actif_badge = (
                '<span style="background:#ECFDF5;color:#059669;font-size:.6rem;font-weight:700;'
                'padding:.1rem .35rem;border-radius:4px;letter-spacing:.04em">ACTIF</span>'
                if is_actif else
                '<span style="background:#FEF2F2;color:#DC2626;font-size:.6rem;font-weight:700;'
                'padding:.1rem .35rem;border-radius:4px;letter-spacing:.04em">INACTIF</span>'
            )
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:.5rem;padding:.15rem 0">'
                f'  <div style="font-size:1.1rem">{icone}</div>'
                f'  <div>'
                f'    <div style="font-size:.87rem;font-weight:700;color:#0F172A">{row["nom"]}</div>'
                f'    <div style="font-size:.7rem;color:#94A3B8;margin-top:.05rem">{drapeau} {row["pays"]} · {row["type_compte"]}</div>'
                f'  </div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(
                f'<div style="font-size:.9rem;font-weight:800;color:{solde_clr};padding-top:.2rem">{solde_fmt}</div>',
                unsafe_allow_html=True,
            )
        with c3:
            st.markdown(
                f'<div style="font-size:.78rem;font-weight:700;color:{dev_clr};padding-top:.2rem;'
                f'background:{"#EFF6FF" if dev=="EUR" else "#ECFDF5"};border-radius:5px;'
                f'display:inline-block;padding:.15rem .4rem">{dev}</div>',
                unsafe_allow_html=True,
            )
        with c4:
            badge_html = (
                '<span style="background:#ECFDF5;color:#059669;font-size:.65rem;font-weight:700;'
                'padding:.15rem .4rem;border-radius:5px">Actif</span>'
                if is_actif else
                '<span style="background:#FEF2F2;color:#DC2626;font-size:.65rem;font-weight:700;'
                'padding:.15rem .4rem;border-radius:5px">Inactif</span>'
            )
            st.markdown(f'<div style="padding-top:.2rem">{badge_html}</div>', unsafe_allow_html=True)
        with c5:
            st.markdown(f'<div class="row-comment" style="padding-top:.2rem">{proprio}</div>', unsafe_allow_html=True)
        with c6:
            st.markdown(f'<div class="row-comment" style="padding-top:.2rem">{str(row.get("description",""))[:55]}</div>', unsafe_allow_html=True)

        st.markdown('<hr style="border:none;border-top:1px solid #F8FAFC;margin:.3rem 0">', unsafe_allow_html=True)

st.markdown(divider(), unsafe_allow_html=True)

# ── Formulaire ajout ──────────────────────────────────────────────────────────
inv_options = {row["id"]: row["nom"] for _, row in df_inv.iterrows()} if not df_inv.empty else {}

if READ_ONLY:
    read_only_notice("La gestion des comptes")

with st.expander("➕ Ajouter un compte", expanded=False):
    with st.form("form_add_cpt", clear_on_submit=True):
        st.markdown("#### Nouveau compte")
        col1, col2 = st.columns(2)
        with col1:
            nom      = st.text_input("Nom du compte *", placeholder="Ex : BICIGUI Conakry")
            pays     = st.selectbox("Pays *", PAYS_DISPONIBLES)
            devise   = st.selectbox("Devise *", DEVISES)
        with col2:
            type_cpt = st.selectbox("Type *", TYPES_COMPTE)
            inv_id   = st.selectbox(
                "Propriétaire",
                options=[""] + list(inv_options.keys()),
                format_func=lambda x: inv_options.get(x, "— Aucun —") if x else "— Aucun —",
            )
            actif    = st.checkbox("Compte actif", value=True)
            date_creation = st.date_input("Date de création *", value=date.today())
        description = st.text_area("Description", height=80)

        if st.form_submit_button("Créer le compte", type="primary", disabled=READ_ONLY):
            if not nom.strip():
                st.error("Le nom est obligatoire.")
            else:
                if add_compte(nom.strip(), inv_id, pays, devise, type_cpt, actif, description.strip(), str(date_creation)):
                    st.success(f"✅ Compte **{nom}** créé.")
                    st.cache_data.clear()
                    st.rerun()

# ── Formulaire modification ───────────────────────────────────────────────────
if not df_cpt.empty:
    with st.expander("✏️ Modifier un compte", expanded=False):
        cpt_map = {row["id"]: row["nom"] for _, row in df_cpt.iterrows()}
        choix   = st.selectbox("Compte", list(cpt_map.keys()),
                               format_func=lambda x: cpt_map.get(x, x), key="sel_cpt_edit")
        if choix:
            sel = df_cpt[df_cpt["id"] == choix].iloc[0]
            with st.form("form_edit_cpt"):
                col1, col2 = st.columns(2)
                with col1:
                    n_nom  = st.text_input("Nom", value=str(sel["nom"]))
                    n_pays = st.selectbox("Pays", PAYS_DISPONIBLES,
                                          index=PAYS_DISPONIBLES.index(sel["pays"]) if sel["pays"] in PAYS_DISPONIBLES else 0)
                    n_dev  = st.selectbox("Devise", DEVISES,
                                          index=DEVISES.index(sel["devise"]) if sel["devise"] in DEVISES else 0)
                with col2:
                    n_type = st.selectbox("Type", TYPES_COMPTE,
                                          index=TYPES_COMPTE.index(sel["type_compte"]) if sel["type_compte"] in TYPES_COMPTE else 0)
                    n_inv  = st.selectbox(
                        "Propriétaire",
                        options=[""] + list(inv_options.keys()),
                        format_func=lambda x: inv_options.get(x, "— Aucun —") if x else "— Aucun —",
                        index=([""] + list(inv_options.keys())).index(sel.get("investisseur_id", ""))
                        if sel.get("investisseur_id", "") in inv_options else 0,
                    )
                    n_actif = st.checkbox("Actif", value=str(sel["actif"]).lower() == "true")
                    n_desc  = st.text_area("Description", value=str(sel.get("description", "")), height=80)

                if st.form_submit_button("Mettre à jour", type="primary", disabled=READ_ONLY):
                    if update_compte(choix, {"nom": n_nom, "pays": n_pays, "devise": n_dev,
                                             "type_compte": n_type, "investisseur_id": n_inv,
                                             "actif": str(n_actif), "description": n_desc}):
                        st.success("✅ Compte mis à jour.")
                        st.cache_data.clear()
                        st.rerun()

    with st.expander("📋 Historique du compte", expanded=False):
        cpt_choice = st.selectbox(
            "Compte", list(cpt_map.keys()),
            format_func=lambda x: cpt_map.get(x, x), key="hist_cpt_sel"
        )
        if cpt_choice:
            df_cpt_mvt = df_mvt.copy()
            df_cpt_mvt["date"] = pd.to_datetime(df_cpt_mvt["date"], errors="coerce")
            df_cpt_mvt["montant_converti_gnf"] = pd.to_numeric(df_cpt_mvt["montant_converti_gnf"], errors="coerce").fillna(0)
            df_cpt_mvt["montant_origine"] = pd.to_numeric(df_cpt_mvt["montant_origine"], errors="coerce").fillna(0)
            df_cpt_mvt = df_cpt_mvt[
                (df_cpt_mvt["compte_source_id"] == cpt_choice)
                | (df_cpt_mvt["compte_destination_id"] == cpt_choice)
            ].sort_values("date", ascending=False)

            if df_cpt_mvt.empty:
                st.info("Aucun mouvement pour ce compte.")
            else:
                cols = st.columns([1.4, 1.6, 2.2, 2.5, 2, 2, 2.2])
                for col, lbl in zip(cols, ["Date", "Type", "Montant GNF", "Montant origine", "Taux", "Source", "Destination"]):
                    with col:
                        st.markdown(f'<div class="th">{lbl}</div>', unsafe_allow_html=True)
                st.markdown('<hr style="border:none;border-top:1.5px solid #E2E8F0;margin:.3rem 0">', unsafe_allow_html=True)
                for _, row in df_cpt_mvt.iterrows():
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
                            st.markdown(f'<div class="row-comment">{row.get("montant_origine","")} {row.get("devise_origine","")}</div>', unsafe_allow_html=True)
                    with c5:
                        st.markdown(f'<div class="row-comment">{fmt_taux(row["taux_eur_gnf"]) if str(row.get("devise_origine","")).upper()=="EUR" else "—"}</div>', unsafe_allow_html=True)
                    with c6:
                        st.markdown(f'<div class="row-comment">{row.get("compte_source_id","—")}</div>', unsafe_allow_html=True)
                    with c7:
                        st.markdown(f'<div class="row-comment">{row.get("compte_destination_id","—")}</div>', unsafe_allow_html=True)
                    st.markdown('<hr style="border:none;border-top:1px solid #F8FAFC;margin:.2rem 0">', unsafe_allow_html=True)
