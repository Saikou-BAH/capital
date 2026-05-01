"""Page Taux de conversion EUR → GNF — historique et simulateur."""

import streamlit as st
import pandas as pd
from datetime import date

from utils.data_loader import get_taux, add_taux, export_csv
from utils.calculs import get_dernier_taux
from utils.formatting import (
    inject_css, kpi_card, section_header, page_header, empty_state,
    fmt_taux, fmt_eur, fmt_gnf, divider, spacer,
)
from utils.charts import chart_historique_taux
from utils.runtime import is_read_only_mode, read_only_notice

st.set_page_config(page_title="Taux de conversion", page_icon="💱", layout="wide")
inject_css()

st.markdown(page_header("Taux de conversion", "💱", "Historique des taux EUR → GNF et simulateur de conversion."), unsafe_allow_html=True)

@st.cache_data(ttl=60)
def load():
    return get_taux()

df_taux = load()
READ_ONLY = is_read_only_mode()

if df_taux is not None and not df_taux.empty:
    df_sort = df_taux.copy()
    df_sort["date_taux"]  = pd.to_datetime(df_sort["date_taux"], errors="coerce")
    df_sort["eur_to_gnf"] = pd.to_numeric(df_sort["eur_to_gnf"], errors="coerce")
    df_sort = df_sort.dropna(subset=["date_taux", "eur_to_gnf"]).sort_values("date_taux", ascending=False)
else:
    df_sort = pd.DataFrame()

dernier_taux = get_dernier_taux(df_taux)

variation = None
if len(df_sort) >= 2:
    variation = float(df_sort.iloc[0]["eur_to_gnf"]) - float(df_sort.iloc[1]["eur_to_gnf"])

# ── KPIs ──────────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(kpi_card("Dernier taux", fmt_taux(dernier_taux), icon="💱", color="blue"), unsafe_allow_html=True)
with c2:
    date_str = str(df_sort.iloc[0]["date_taux"])[:10] if not df_sort.empty else "—"
    st.markdown(kpi_card("Date du dernier taux", date_str, icon="📅", color="green"), unsafe_allow_html=True)
with c3:
    st.markdown(kpi_card("Taux enregistrés", str(len(df_sort)), icon="📋", color="violet"), unsafe_allow_html=True)
with c4:
    if variation is not None:
        sign  = "+" if variation >= 0 else ""
        color = "green" if variation >= 0 else "red"
        st.markdown(kpi_card("Variation vs précédent", f"{sign}{int(variation)} GNF/€", icon="📈", color=color), unsafe_allow_html=True)
    else:
        st.markdown(kpi_card("Variation vs précédent", "—", icon="📈", color="slate"), unsafe_allow_html=True)

st.markdown(divider(), unsafe_allow_html=True)

# ── Simulateur + graphique ────────────────────────────────────────────────────
col_sim, col_chart = st.columns([1, 2])

with col_sim:
    st.markdown(section_header("Simulateur de conversion", "🧮", "#7C3AED"), unsafe_allow_html=True)

    st.markdown('<div class="card" style="padding:1.25rem 1.4rem">', unsafe_allow_html=True)
    montant_eur = st.number_input("Montant en EUR", min_value=0.0, value=0.0, step=100.0)
    taux_sim    = st.number_input("Taux EUR → GNF", min_value=0.0,
                                  value=float(dernier_taux) if dernier_taux > 0 else 0.0, step=50.0)
    montant_gnf_sim = montant_eur * taux_sim
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(spacer("0.5rem"), unsafe_allow_html=True)
    st.markdown(
        kpi_card("Résultat en GNF", fmt_gnf(montant_gnf_sim),
                 sub=f"{fmt_eur(montant_eur)} × {fmt_taux(taux_sim)}", color="blue"),
        unsafe_allow_html=True,
    )

    st.markdown(spacer("0.35rem"), unsafe_allow_html=True)
    st.markdown('<div class="card" style="padding:1.25rem 1.4rem">', unsafe_allow_html=True)
    montant_gnf_in  = st.number_input("Montant en GNF", min_value=0.0, value=1_000_000.0, step=100_000.0)
    montant_eur_sim = montant_gnf_in / taux_sim if taux_sim > 0 else 0
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown(spacer("0.35rem"), unsafe_allow_html=True)
    st.markdown(
        kpi_card("Équivalent EUR", fmt_eur(montant_eur_sim),
                 sub=f"÷ {fmt_taux(taux_sim)}", color="violet"),
        unsafe_allow_html=True,
    )

with col_chart:
    st.markdown(section_header("Historique du taux", "📈", "#2563EB"), unsafe_allow_html=True)
    st.markdown('<div class="card" style="padding:.75rem 1rem .5rem 1rem">', unsafe_allow_html=True)
    st.plotly_chart(chart_historique_taux(df_taux), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown(divider(), unsafe_allow_html=True)

# ── Formulaire ajout taux ─────────────────────────────────────────────────────
if READ_ONLY:
    read_only_notice("L'enregistrement des taux")

with st.expander("➕ Enregistrer un nouveau taux", expanded=False):
    with st.form("form_add_taux", clear_on_submit=True):
        st.markdown("#### Nouveau taux EUR → GNF")

        col1, col2 = st.columns(2)
        with col1:
            date_taux_val = st.date_input("Date du taux *", value=date.today())
            taux_val      = st.number_input(
                "Taux EUR → GNF *",
                min_value=0.0, value=float(dernier_taux) if dernier_taux > 0 else 0.0,
                step=50.0,
                help="Combien de GNF pour 1 EUR à cette date ?",
            )
        with col2:
            commentaire = st.text_area(
                "Commentaire",
                placeholder="Ex : Taux BOA Guinée du jour, taux Western Union…",
                height=100,
            )
            st.markdown(
                kpi_card("Prévisualisation", fmt_taux(taux_val),
                         sub=f"Valide au {date_taux_val}", color="blue"),
                unsafe_allow_html=True,
            )

        if st.form_submit_button("Enregistrer le taux", type="primary", disabled=READ_ONLY):
            if taux_val <= 0:
                st.error("Le taux doit être supérieur à 0.")
            else:
                ok = add_taux(str(date_taux_val), taux_val, commentaire.strip())
                if ok:
                    st.success(f"✅ Taux **{fmt_taux(taux_val)}** enregistré pour le {date_taux_val}.")
                    st.cache_data.clear()
                    st.rerun()

st.markdown(divider(), unsafe_allow_html=True)

# ── Historique ────────────────────────────────────────────────────────────────
col_title, col_export = st.columns([4, 1])
with col_title:
    st.markdown(section_header("Historique des taux", "📋", "#475569"), unsafe_allow_html=True)
with col_export:
    if not df_sort.empty:
        csv_bytes = export_csv(df_sort.assign(date_taux=df_sort["date_taux"].astype(str).str[:10]))
        st.download_button("⬇️ CSV", csv_bytes, f"taux_conversion_{date.today()}.csv", "text/csv")

if df_sort.empty:
    st.markdown(
        empty_state("💱", "Aucun taux enregistré", "Utilisez le formulaire ci-dessus pour ajouter le premier taux de change."),
        unsafe_allow_html=True,
    )
else:
    # En-têtes
    h1, h2, h3, h4, h5 = st.columns([2, 2.5, 2.5, 3, 2.5])
    for col, lbl in zip([h1, h2, h3, h4, h5], ["Date", "Taux EUR/GNF", "Équiv. 1 000 EUR", "Commentaire", "Enregistré le"]):
        with col:
            st.markdown(f'<div class="th">{lbl}</div>', unsafe_allow_html=True)
    st.markdown('<hr style="border:none;border-top:1.5px solid #E2E8F0;margin:.3rem 0 .5rem 0">', unsafe_allow_html=True)

    for i, (_, row) in enumerate(df_sort.iterrows()):
        taux_row = float(row["eur_to_gnf"])
        c1, c2, c3, c4, c5 = st.columns([2, 2.5, 2.5, 3, 2.5])
        with c1:
            st.markdown(f'<div class="row-date">{str(row["date_taux"])[:10]}</div>', unsafe_allow_html=True)
        with c2:
            label = ' <span style="font-size:.62rem;background:#EFF6FF;color:#2563EB;padding:.1rem .35rem;border-radius:4px;font-weight:700">DERNIER</span>' if i == 0 else ""
            st.markdown(f'<div style="font-size:.88rem;font-weight:800;color:#0F172A">{fmt_taux(taux_row)}{label}</div>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div class="row-comment">{fmt_gnf(1000 * taux_row)}</div>', unsafe_allow_html=True)
        with c4:
            st.markdown(f'<div class="row-comment">{str(row.get("commentaire",""))}</div>', unsafe_allow_html=True)
        with c5:
            st.markdown(f'<div class="row-comment">{str(row.get("created_at",""))[:16]}</div>', unsafe_allow_html=True)
        st.markdown('<hr style="border:none;border-top:1px solid #F8FAFC;margin:.3rem 0">', unsafe_allow_html=True)
