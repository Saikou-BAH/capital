"""Page Historique — vue chronologique complète avec filtres avancés et export CSV."""

import streamlit as st
import pandas as pd
from datetime import date

from utils.config import TYPES_MOUVEMENT, DEVISES, PAYS_DISPONIBLES
from utils.data_loader import get_mouvements, get_investisseurs, get_comptes, delete_mouvement, export_csv
from utils.calculs import evolution_capital
from utils.formatting import (
    inject_css, kpi_card, section_header, page_header, empty_state,
    fmt_gnf, fmt_eur, fmt_taux, badge_mouvement, divider, spacer,
)
from utils.charts import chart_evolution_capital
from utils.runtime import is_read_only_mode

st.set_page_config(page_title="Historique", page_icon="📜", layout="wide")
inject_css()

st.markdown(page_header("Historique", "📜", "Vue chronologique complète — filtres avancés et export."), unsafe_allow_html=True)

@st.cache_data(ttl=60)
def load():
    return get_mouvements(), get_investisseurs(), get_comptes()

df_mvt, df_inv, df_cpt = load()
READ_ONLY = is_read_only_mode()

noms_inv = df_inv.set_index("id")["nom"].to_dict() if not df_inv.empty else {}
noms_cpt = df_cpt.set_index("id")["nom"].to_dict() if not df_cpt.empty else {}
pays_cpt = df_cpt.set_index("id")["pays"].to_dict() if not df_cpt.empty else {}

# ── Préparation ───────────────────────────────────────────────────────────────
if df_mvt is not None and not df_mvt.empty:
    df = df_mvt.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["montant_converti_gnf"] = pd.to_numeric(df["montant_converti_gnf"], errors="coerce").fillna(0)
    df["montant_origine"]      = pd.to_numeric(df["montant_origine"], errors="coerce").fillna(0)
    df["taux_eur_gnf"]         = pd.to_numeric(df["taux_eur_gnf"], errors="coerce").fillna(0)
    df["investisseur"] = df["investisseur_id"].map(noms_inv).fillna("—")
    df["src_nom"]      = df["compte_source_id"].map(noms_cpt).fillna("—")
    df["dst_nom"]      = df["compte_destination_id"].map(noms_cpt).fillna("—")
    df["pays_dst"]     = df["compte_destination_id"].map(pays_cpt).fillna("—")
    df["pays_src"]     = df["compte_source_id"].map(pays_cpt).fillna("—")
    devise_cpt         = df_cpt.set_index("id")["devise"].to_dict() if not df_cpt.empty else {}
    df["devise_dst"]   = df["compte_destination_id"].map(devise_cpt).fillna("—")
else:
    df = pd.DataFrame()

# ── KPIs ──────────────────────────────────────────────────────────────────────
nb_total    = len(df) if not df.empty else 0
tot_apports = df[df["type_mouvement"]=="apport"]["montant_converti_gnf"].sum() if not df.empty else 0
nb_trans    = len(df[df["type_mouvement"]=="transfert"]) if not df.empty else 0
date_prem   = str(df["date"].min())[:10] if not df.empty and not df["date"].isna().all() else "—"

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(kpi_card("Total mouvements", str(nb_total), icon="📋", color="blue"), unsafe_allow_html=True)
with c2:
    st.markdown(kpi_card("Total apports (GNF)", fmt_gnf(tot_apports), icon="💰", color="green"), unsafe_allow_html=True)
with c3:
    st.markdown(kpi_card("Transferts internes", str(nb_trans), icon="↔️", color="violet"), unsafe_allow_html=True)
with c4:
    st.markdown(kpi_card("Depuis le", date_prem, icon="📅", color="amber"), unsafe_allow_html=True)

st.markdown(divider(), unsafe_allow_html=True)

# ── Courbe ────────────────────────────────────────────────────────────────────
st.markdown(section_header("Évolution du capital", "📈", "#059669"), unsafe_allow_html=True)
st.markdown('<div class="card" style="padding:.75rem 1rem .5rem 1rem">', unsafe_allow_html=True)
st.plotly_chart(chart_evolution_capital(evolution_capital(df_mvt, df_cpt)), use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

st.markdown(divider(), unsafe_allow_html=True)

# ── Filtres ───────────────────────────────────────────────────────────────────
st.markdown(section_header("Filtres avancés", "🔍", "#475569"), unsafe_allow_html=True)

r1 = st.columns(5)
with r1[0]: f_type  = st.multiselect("Type", TYPES_MOUVEMENT)
with r1[1]: f_inv   = st.selectbox("Investisseur", ["Tous"] + sorted(noms_inv.values()))
with r1[2]: f_dev   = st.multiselect("Devise", DEVISES)
with r1[3]: f_dmin  = st.date_input("Du", value=None, key="h_dmin")
with r1[4]: f_dmax  = st.date_input("Au", value=None, key="h_dmax")

r2 = st.columns(5)
with r2[0]: f_pays    = st.selectbox("Pays destination", ["Tous"] + PAYS_DISPONIBLES)
with r2[1]: f_capital = st.selectbox("Dans le capital ?", ["Tous", "Oui", "Non"])
with r2[2]: f_mmin    = st.number_input("Montant min (GNF)", min_value=0.0, value=0.0, step=1_000_000.0, format="%.0f")
with r2[3]: f_mmax    = st.number_input("Montant max (GNF)", min_value=0.0, value=0.0, step=1_000_000.0, format="%.0f")
with r2[4]: f_search  = st.text_input("Recherche commentaire", placeholder="Mot-clé…")

# Application filtres
df_show = df.copy() if not df.empty else pd.DataFrame()
if not df_show.empty:
    if f_type:
        df_show = df_show[df_show["type_mouvement"].isin(f_type)]
    if f_inv != "Tous":
        df_show = df_show[df_show["investisseur"] == f_inv]
    if f_dev:
        df_show = df_show[df_show["devise_origine"].isin(f_dev)]
    if f_dmin:
        df_show = df_show[df_show["date"] >= pd.Timestamp(f_dmin)]
    if f_dmax:
        df_show = df_show[df_show["date"] <= pd.Timestamp(f_dmax)]
    if f_pays != "Tous":
        df_show = df_show[df_show["pays_dst"] == f_pays]
    if f_capital == "Oui":
        df_show = df_show[df_show["compte_dans_capital"].astype(str).str.lower().isin(["true","1","oui"])]
    elif f_capital == "Non":
        df_show = df_show[~df_show["compte_dans_capital"].astype(str).str.lower().isin(["true","1","oui"])]
    if f_mmin > 0:
        df_show = df_show[df_show["montant_converti_gnf"] >= f_mmin]
    if f_mmax > 0:
        df_show = df_show[df_show["montant_converti_gnf"] <= f_mmax]
    if f_search.strip():
        df_show = df_show[df_show["commentaire"].astype(str).str.contains(f_search.strip(), case=False, na=False)]
    df_show = df_show.sort_values("date", ascending=False)

st.markdown(divider(), unsafe_allow_html=True)

# ── Résultats + export ────────────────────────────────────────────────────────
nb = len(df_show) if not df_show.empty else 0
col_count, col_export = st.columns([4, 1])
with col_count:
    st.markdown(
        f'<div style="font-size:.78rem;font-weight:600;color:#94A3B8;margin-bottom:.5rem">'
        f'{nb} mouvement(s) affiché(s)</div>',
        unsafe_allow_html=True,
    )
with col_export:
    if not df_show.empty:
        cols_ex = ["date","type_mouvement","investisseur","montant_origine","devise_origine",
                   "taux_eur_gnf","montant_converti_gnf","src_nom","dst_nom","pays_dst",
                   "compte_dans_capital","commentaire"]
        df_csv = df_show[[c for c in cols_ex if c in df_show.columns]].copy()
        df_csv["date"] = df_csv["date"].astype(str).str[:10]
        st.download_button("⬇️ Export CSV", export_csv(df_csv),
                           f"historique_{date.today()}.csv", "text/csv")

if df_show.empty:
    st.markdown(
        empty_state("🔍", "Aucun résultat", "Aucun mouvement ne correspond aux filtres sélectionnés."),
        unsafe_allow_html=True,
    )
else:
    # En-têtes
    hh = st.columns([1.4, 1.8, 2.2, 3, 2, 2, 1.4, 2.5])
    for col, lbl in zip(hh, ["Date", "Type", "Investisseur", "Montant (GNF)", "Source", "Destination", "Action", "Commentaire"]):
        with col:
            st.markdown(f'<div class="th">{lbl}</div>', unsafe_allow_html=True)
    st.markdown('<hr style="border:none;border-top:1.5px solid #E2E8F0;margin:.3rem 0 .5rem 0">', unsafe_allow_html=True)

    for _, row in df_show.iterrows():
        in_cap = str(row.get("compte_dans_capital","")).lower() in ["true","1","oui"]
        c1,c2,c3,c4,c5,c6,c7,c8 = st.columns([1.4,1.8,2.2,3,2,2,1.4,2.5])
        with c1:
            st.markdown(f'<div class="row-date">{str(row["date"])[:10] if pd.notna(row["date"]) else "—"}</div>', unsafe_allow_html=True)
        with c2:
            st.markdown(badge_mouvement(str(row["type_mouvement"])), unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div style="font-size:.84rem;color:#334155;font-weight:500">{row.get("investisseur","—")}</div>', unsafe_allow_html=True)
        with c4:
            cap_dot = '<span style="color:#059669;font-size:.55rem">●</span>' if in_cap else '<span style="color:#CBD5E1;font-size:.55rem">●</span>'
            extra = ""
            if str(row.get("devise_origine", "")).upper() != "GNF":
                extra = f' · {fmt_eur(row["montant_origine"])} @ {fmt_taux(row["taux_eur_gnf"])}'
            st.markdown(
                f'<div class="row-amount">{fmt_gnf(row["montant_converti_gnf"])}</div>'
                f'<div class="row-comment">{cap_dot} {"Capital" if in_cap else "Hors capital"}{extra}</div>',
                unsafe_allow_html=True,
            )
        with c5:
            st.markdown(
                f'<div class="row-comment">{row.get("src_nom","—")}'
                f'<br><span style="color:#CBD5E1">{row.get("pays_src","")}</span></div>',
                unsafe_allow_html=True,
            )
        with c6:
            st.markdown(
                f'<div class="row-comment">{row.get("dst_nom","—")}'
                f'<br><span style="color:#CBD5E1">{row.get("pays_dst","")}</span></div>',
                unsafe_allow_html=True,
            )
        with c7:
            type_mvt_v   = str(row.get("type_mouvement","")).lower()
            devise_orig_v = str(row.get("devise_origine","")).upper()
            pays_dst_v   = str(row.get("pays_dst",""))
            devise_dst_v = str(row.get("devise_dst","")).upper()
            can_delete = (
                type_mvt_v == "apport" and devise_orig_v == "EUR"
            ) or (
                type_mvt_v == "transfert" and pays_dst_v.lower() == "guinée" and devise_dst_v == "GNF"
            )
            if can_delete and not READ_ONLY:
                if st.button("🗑️", key=f"del_{row['id']}", help="Supprimer"):
                    if delete_mouvement(row["id"]):
                        st.success("Supprimé.")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("Impossible de supprimer.")
            else:
                st.markdown('<div style="color:#CBD5E1;font-size:.75rem;padding-top:.2rem">—</div>', unsafe_allow_html=True)
        with c8:
            st.markdown(f'<div class="row-comment">{str(row.get("commentaire",""))[:65]}</div>', unsafe_allow_html=True)

        st.markdown('<hr style="border:none;border-top:1px solid #F8FAFC;margin:.25rem 0">', unsafe_allow_html=True)
