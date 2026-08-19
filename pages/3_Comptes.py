"""Page Comptes — création, modification, soldes."""

from datetime import date

import streamlit as st
import pandas as pd

from utils.config import TYPES_COMPTE, PAYS_DISPONIBLES, DEVISES
from utils.data_loader import get_comptes, get_investisseurs, get_mouvements, add_compte, update_compte
from utils.calculs import (
    soldes_par_compte, calculer_capital_breakdown, valeurs_par_compte,
    repartition_par_devise, repartition_investisseurs_par_compte,
)
from utils.formatting import (
    inject_css, kpi_card, section_header, page_header, empty_state,
    fmt_gnf, fmt_eur, fmt_taux, badge_mouvement, divider, spacer,
)
from utils.charts import chart_valeurs_par_compte, chart_repartition_devise, chart_evolution_soldes_comptes
from utils.runtime import is_read_only_mode, read_only_notice

inject_css()

st.markdown(page_header("Comptes", "🏦", "Gérez les comptes bancaires et de trésorerie du projet."), unsafe_allow_html=True)

@st.cache_data(ttl=60)
def load():
    return get_comptes(), get_investisseurs(), get_mouvements()

df_cpt, df_inv, df_mvt = load()
df_soldes = soldes_par_compte(df_mvt, df_cpt)
df_valeurs = valeurs_par_compte(df_mvt, df_cpt)
df_devise = repartition_par_devise(df_mvt, df_cpt)
df_repart_inv = repartition_investisseurs_par_compte(df_mvt, df_cpt, df_inv)
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

st.markdown(spacer("0.5rem"), unsafe_allow_html=True)
st.markdown('<div class="card" style="padding:.75rem 1rem .5rem 1rem">', unsafe_allow_html=True)
st.plotly_chart(chart_evolution_soldes_comptes(df_mvt, df_cpt), use_container_width=True)
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

if df_display.empty:
    st.markdown(
        empty_state("🏦", "Aucun compte trouvé", "Aucun compte ne correspond à ces filtres, ou aucun compte n'a encore été créé."),
        unsafe_allow_html=True,
    )
else:
    ICONES_TYPE = {"banque": "🏦", "espèces": "💵", "mobile money": "📱", "YMO": "📲", "autre": "📂"}
    ICONES_PAYS = {"France": "🇫🇷", "Guinée": "🇬🇳", "Belgique": "🇧🇪", "Sénégal": "🇸🇳"}

    def _render_compte_row(row):
        is_actif  = str(row["actif"]).lower() == "true"
        icone     = ICONES_TYPE.get(row["type_compte"], "📂")
        drapeau   = ICONES_PAYS.get(row["pays"], "🌍")
        proprio   = noms_inv.get(row.get("investisseur_id", ""), "—")
        solde     = row["solde_gnf"]
        dev       = str(row["devise"]).upper()
        solde_fmt = fmt_eur(solde) if dev == "EUR" else fmt_gnf(solde)
        solde_clr = "#059669" if solde > 0 else ("#DC2626" if solde < 0 else "#94A3B8")
        frais_pct_val = float(row.get("frais_pct", 0) or 0)

        c1, c2, c3, c4, c5 = st.columns([3.5, 2.5, 1.8, 2, 2.5])
        with c1:
            frais_badge = (
                f'<span style="background:#F5F3FF;color:#7C3AED;font-size:.6rem;font-weight:700;'
                f'padding:.1rem .35rem;border-radius:4px;margin-left:.35rem">🏧 {frais_pct_val*100:.0f}% frais</span>'
                if frais_pct_val > 0 else ""
            )
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:.5rem;padding:.15rem 0">'
                f'  <div style="font-size:1.1rem">{icone}</div>'
                f'  <div>'
                f'    <div style="font-size:.87rem;font-weight:700;color:#0F172A">{row["nom"]}{frais_badge}</div>'
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
            badge_html = (
                '<span style="background:#ECFDF5;color:#059669;font-size:.65rem;font-weight:700;'
                'padding:.15rem .4rem;border-radius:5px">Actif</span>'
                if is_actif else
                '<span style="background:#FEF2F2;color:#DC2626;font-size:.65rem;font-weight:700;'
                'padding:.15rem .4rem;border-radius:5px">Inactif</span>'
            )
            st.markdown(f'<div style="padding-top:.2rem">{badge_html}</div>', unsafe_allow_html=True)
        with c4:
            st.markdown(f'<div class="row-comment" style="padding-top:.2rem">{proprio}</div>', unsafe_allow_html=True)
        with c5:
            st.markdown(f'<div class="row-comment" style="padding-top:.2rem">{str(row.get("description",""))[:55]}</div>', unsafe_allow_html=True)

        df_rep_cpt = df_repart_inv[df_repart_inv["compte_id"] == row["id"]] if not df_repart_inv.empty else pd.DataFrame()
        if not df_rep_cpt.empty:
            fmt_montant = fmt_eur if dev == "EUR" else fmt_gnf
            badges = "".join(
                f'<span style="background:#F1F5F9;color:#334155;font-size:.68rem;font-weight:600;'
                f'padding:.15rem .5rem;border-radius:999px;white-space:nowrap">'
                f'👤 {r["investisseur_nom"]} — {fmt_montant(r["montant"])} ({r["pct"]:.0f}%)</span>'
                for _, r in df_rep_cpt.iterrows()
            )
            st.markdown(
                f'<div style="display:flex;gap:.4rem;flex-wrap:wrap;padding:.25rem 0 0 0">{badges}</div>',
                unsafe_allow_html=True,
            )
        st.markdown('<hr style="border:none;border-top:1px solid #F8FAFC;margin:.3rem 0">', unsafe_allow_html=True)

    def _render_section(df_sec, title, color):
        if df_sec.empty:
            return
        st.markdown(section_header(title, "", color), unsafe_allow_html=True)
        h1, h2, h3, h4, h5 = st.columns([3.5, 2.5, 1.8, 2, 2.5])
        for col, lbl in zip([h1, h2, h3, h4, h5], ["Compte", "Solde estimé", "Statut", "Propriétaire", "Description"]):
            with col:
                st.markdown(f'<div class="th">{lbl}</div>', unsafe_allow_html=True)
        st.markdown('<hr style="border:none;border-top:1.5px solid #E2E8F0;margin:.3rem 0 .5rem 0">', unsafe_allow_html=True)
        for _, row in df_sec.iterrows():
            _render_compte_row(row)

    # Groupement par devise
    df_eur = df_display[df_display["devise"].astype(str).str.upper() == "EUR"]
    df_gnf = df_display[df_display["devise"].astype(str).str.upper() == "GNF"]
    df_gnf_frais   = df_gnf[df_gnf["frais_pct"].apply(lambda x: float(x or 0)) > 0]
    df_gnf_normal  = df_gnf[df_gnf["frais_pct"].apply(lambda x: float(x or 0)) == 0]
    df_other = df_display[~df_display["devise"].astype(str).str.upper().isin(["EUR", "GNF"])]

    if not df_eur.empty:
        _render_section(df_eur, f"Comptes en EUR  ({len(df_eur)})", "#2563EB")
        st.markdown(spacer("0.5rem"), unsafe_allow_html=True)

    if not df_gnf_normal.empty:
        _render_section(df_gnf_normal, f"Comptes en GNF  ({len(df_gnf_normal)})", "#059669")
        st.markdown(spacer("0.5rem"), unsafe_allow_html=True)

    if not df_gnf_frais.empty:
        _render_section(df_gnf_frais, f"Comptes GNF avec frais  ({len(df_gnf_frais)})", "#7C3AED")
        st.markdown(spacer("0.5rem"), unsafe_allow_html=True)

    if not df_other.empty:
        _render_section(df_other, f"Autres comptes  ({len(df_other)})", "#475569")

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
        frais_pct_input = st.number_input(
            "Frais de retrait (%)",
            min_value=0.0, max_value=100.0, value=0.0, step=0.1, format="%.2f",
            help="Ex : 1 = 1%. Un mouvement de frais est créé automatiquement à chaque transfert entrant.",
        )

        if st.form_submit_button("Créer le compte", type="primary", disabled=READ_ONLY):
            if not nom.strip():
                st.error("Le nom est obligatoire.")
            else:
                if add_compte(nom.strip(), inv_id, pays, devise, type_cpt, actif, description.strip(), str(date_creation), frais_pct=frais_pct_input / 100):
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
            _rows_cpt = df_cpt[df_cpt["id"] == choix]
            if _rows_cpt.empty:
                st.warning("Compte introuvable — rechargez la page.")
            else:
                sel = _rows_cpt.iloc[0]
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
                    n_frais_pct = st.number_input(
                        "Frais de retrait (%)",
                        min_value=0.0, max_value=100.0,
                        value=float(sel.get("frais_pct", 0) or 0) * 100,
                        step=0.1, format="%.2f",
                        help="Ex : 1 = 1%. Un mouvement de frais est créé automatiquement à chaque transfert entrant.",
                    )

                    if st.form_submit_button("Mettre à jour", type="primary", disabled=READ_ONLY):
                        if update_compte(choix, {"nom": n_nom, "pays": n_pays, "devise": n_dev,
                                                 "type_compte": n_type, "investisseur_id": n_inv,
                                                 "actif": str(n_actif), "description": n_desc,
                                                 "frais_pct": str(n_frais_pct / 100)}):
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
                        src_nom = cpt_map.get(row.get("compte_source_id", ""), row.get("compte_source_id", "—") or "—")
                        st.markdown(f'<div class="row-comment">{src_nom}</div>', unsafe_allow_html=True)
                    with c7:
                        dst_nom = cpt_map.get(row.get("compte_destination_id", ""), row.get("compte_destination_id", "—") or "—")
                        st.markdown(f'<div class="row-comment">{dst_nom}</div>', unsafe_allow_html=True)
                    st.markdown('<hr style="border:none;border-top:1px solid #F8FAFC;margin:.2rem 0">', unsafe_allow_html=True)
