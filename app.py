"""Dashboard principal — Capital Legend Farm."""

import streamlit as st
import pandas as pd
from datetime import date

from utils.config import (
    CAPITAL_CIBLE_GNF,
    OBJECTIF_SEPTEMBRE_NOM, OBJECTIF_SEPTEMBRE_MONTANT, OBJECTIF_SEPTEMBRE_DATE,
    OBJECTIF_DECEMBRE_NOM, OBJECTIF_DECEMBRE_MONTANT, OBJECTIF_DECEMBRE_DATE,
)
from utils.data_loader import (
    get_investisseurs, get_comptes, get_mouvements,
    get_objectifs, get_taux, is_demo_mode,
)
from utils.calculs import (
    calculer_capital_total, calculer_capital_breakdown, parts_par_investisseur,
    repartition_par_pays, repartition_par_devise,
    evolution_capital, progression_objectifs, get_dernier_taux,
)
from utils.formatting import (
    inject_css, kpi_card, hero_banner, section_header, page_header,
    fmt_gnf, fmt_pct, fmt_taux, fmt_eur,
    badge_mouvement, progress_bar, progress_labeled,
    divider, spacer, empty_state, stat_row,
)
from utils.charts import (
    chart_evolution_capital, chart_parts_investisseurs,
    chart_repartition_pays, chart_repartition_devise,
    chart_mouvements_par_mois,
)
from utils.runtime import is_read_only_mode

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

# ── Données ───────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60, show_spinner=False)
def _load():
    return (
        get_investisseurs(), get_comptes(), get_mouvements(),
        get_objectifs(), get_taux(),
    )

df_inv, df_cpt, df_mvt, df_obj, df_taux = _load()

# ── Calculs ───────────────────────────────────────────────────────────────────
capital_total     = calculer_capital_total(df_mvt, df_cpt)
pct_global        = capital_total / CAPITAL_CIBLE_GNF * 100
dernier_taux      = get_dernier_taux(df_taux)
df_parts          = parts_par_investisseur(df_mvt, df_inv)
df_pays           = repartition_par_pays(df_mvt, df_cpt)
df_devise         = repartition_par_devise(df_mvt, df_cpt)
df_evolution      = evolution_capital(df_mvt, df_cpt)
capital_breakdown = calculer_capital_breakdown(df_mvt, df_cpt)
total_eur         = capital_breakdown["total_eur"]
total_gnf         = capital_breakdown["total_gnf"]
total_eur_gnf     = capital_breakdown["valorisation_eur_gnf"]
df_obj_prog       = progression_objectifs(df_obj, capital_total)
nb_inv            = len(df_inv) if df_inv is not None else 0
nb_mvt            = len(df_mvt) if df_mvt is not None else 0

reste_sep  = max(0.0, OBJECTIF_SEPTEMBRE_MONTANT - capital_total)
reste_dec  = max(0.0, OBJECTIF_DECEMBRE_MONTANT  - capital_total)
pct_sep    = min(100.0, capital_total / OBJECTIF_SEPTEMBRE_MONTANT * 100)
pct_dec    = min(100.0, capital_total / OBJECTIF_DECEMBRE_MONTANT  * 100)
atteint_sep = capital_total >= OBJECTIF_SEPTEMBRE_MONTANT
atteint_dec = capital_total >= OBJECTIF_DECEMBRE_MONTANT

# ══════════════════════════════════════════════════════════════════════════════
# HERO + OBJECTIF RAPIDE
# ══════════════════════════════════════════════════════════════════════════════
col_hero, col_side = st.columns([3, 1])

with col_hero:
    st.markdown(
        hero_banner(capital_total, pct_global, dernier_taux, nb_inv, nb_mvt),
        unsafe_allow_html=True,
    )

with col_side:
    st.markdown(spacer("0.4rem"), unsafe_allow_html=True)

    # Prochain objectif non atteint
    if df_obj_prog is not None and not df_obj_prog.empty:
        actifs = df_obj_prog[df_obj_prog["actif"].astype(str).str.lower() == "true"]
        non_att = actifs[~actifs["atteint"]]
        prochain = non_att.sort_values("montant_cible_gnf").iloc[0] if not non_att.empty else None
        if prochain is not None:
            pct_p  = float(prochain["progress_pct"])
            reste_p = float(prochain["reste_gnf"])
            c_p = "green" if pct_p >= 75 else ("blue" if pct_p >= 40 else "amber")
            st.markdown(
                kpi_card("Prochain objectif", fmt_pct(pct_p),
                         sub=f"Reste : {fmt_gnf(reste_p)}", color=c_p, icon="🎯"),
                unsafe_allow_html=True,
            )
            st.markdown(progress_bar(pct_p, c_p, "5px"), unsafe_allow_html=True)
            st.markdown(spacer("0.5rem"), unsafe_allow_html=True)

    today_str = date.today().strftime("%d %b %Y")
    st.markdown(
        kpi_card("Aujourd'hui", today_str,
                 sub=f"Taux : {fmt_taux(dernier_taux)}", color="slate", icon="🗓️"),
        unsafe_allow_html=True,
    )

# ══════════════════════════════════════════════════════════════════════════════
# KPI ROW
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(spacer("0.5rem"), unsafe_allow_html=True)
k1, k2, k3, k4 = st.columns(4)

with k1:
    st.markdown(kpi_card(
        "Capital valorisé total", fmt_gnf(capital_total),
        sub="Reporting GNF (valorisation EUR incluse)", color="blue", icon="💼",
    ), unsafe_allow_html=True)
with k2:
    st.markdown(kpi_card(
        "Détenu en EUR", fmt_eur(total_eur),
        sub="Montant natif non encore transféré", color="green", icon="🇪🇺",
    ), unsafe_allow_html=True)
with k3:
    st.markdown(kpi_card(
        "Détenu en GNF", fmt_gnf(total_gnf),
        sub="Montant natif GNF en Guinée", color="violet", icon="🇬🇳",
    ), unsafe_allow_html=True)
with k4:
    st.markdown(kpi_card(
        "Valorisation EUR restants", fmt_gnf(total_eur_gnf),
        sub="Équivalent GNF des EUR non transférés", color="amber", icon="💱",
    ), unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# OBJECTIFS SEPTEMBRE & DÉCEMBRE
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(divider(), unsafe_allow_html=True)
st.markdown(section_header("Objectifs principaux", "🎯", "#059669"), unsafe_allow_html=True)

col_sep, col_dec = st.columns(2)

def _obj_card(nom, desc, pct, capital, cible, reste, echeance, atteint):
    color  = "#059669" if atteint else ("#2563EB" if pct >= 50 else "#D97706")
    bar_c  = "green" if atteint else ("blue" if pct >= 50 else "amber")
    status = "✅ Objectif atteint !" if atteint else f"Reste : {fmt_gnf(reste)} · Échéance : {echeance}"
    return f"""
<div class="obj-card">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:.5rem">
    <div>
      <div class="obj-card-title">{nom}</div>
      <div class="obj-card-desc">{desc}</div>
    </div>
    <div style="text-align:right;flex-shrink:0;margin-left:1rem">
      <div class="obj-pct" style="color:{color}">{fmt_pct(pct)}</div>
    </div>
  </div>
  {progress_bar(pct, bar_c, "8px")}
  <div style="display:flex;justify-content:space-between;margin-top:.65rem">
    <div>
      <div style="font-size:.63rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:#94A3B8;margin-bottom:.1rem">Capital actuel</div>
      <div style="font-size:.85rem;font-weight:700;color:#0F172A">{fmt_gnf(capital)}</div>
    </div>
    <div>
      <div style="font-size:.63rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:#94A3B8;margin-bottom:.1rem">Cible</div>
      <div style="font-size:.85rem;font-weight:700;color:#0F172A">{fmt_gnf(cible)}</div>
    </div>
    <div>
      <div style="font-size:.63rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:#94A3B8;margin-bottom:.1rem">Statut</div>
      <div style="font-size:.78rem;font-weight:600;color:{'#059669' if atteint else '#64748B'}">{status}</div>
    </div>
  </div>
</div>"""

with col_sep:
    st.markdown(_obj_card(
        OBJECTIF_SEPTEMBRE_NOM,
        "50% du capital cible — 250 millions GNF",
        pct_sep, capital_total, OBJECTIF_SEPTEMBRE_MONTANT, reste_sep,
        OBJECTIF_SEPTEMBRE_DATE, atteint_sep,
    ), unsafe_allow_html=True)

with col_dec:
    st.markdown(_obj_card(
        OBJECTIF_DECEMBRE_NOM,
        "100% du capital cible — 500 millions GNF",
        pct_dec, capital_total, OBJECTIF_DECEMBRE_MONTANT, reste_dec,
        OBJECTIF_DECEMBRE_DATE, atteint_dec,
    ), unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# GRAPHIQUES LIGNE 1 : Évolution + Parts
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(divider(), unsafe_allow_html=True)
st.markdown(section_header("Évolution & répartition", "📈", "#2563EB"), unsafe_allow_html=True)

col_evo, col_pts = st.columns([3, 2])

with col_evo:
    st.markdown('<div class="card" style="padding:.75rem 1rem .5rem 1rem">', unsafe_allow_html=True)
    st.plotly_chart(chart_evolution_capital(df_evolution), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col_pts:
    st.markdown('<div class="card" style="padding:.75rem 1rem .5rem 1rem">', unsafe_allow_html=True)
    if df_parts is not None and not df_parts.empty:
        st.plotly_chart(chart_parts_investisseurs(df_parts), use_container_width=True)
    else:
        st.markdown(empty_state("👥", "Aucun investisseur", "Ajoutez des investisseurs et des apports pour voir la répartition."), unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# GRAPHIQUES LIGNE 2 : Mouvements / Pays / Devise
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(spacer("0.75rem"), unsafe_allow_html=True)
c_mvt, c_pays, c_dev = st.columns(3)

with c_mvt:
    st.markdown('<div class="card" style="padding:.75rem 1rem .5rem 1rem">', unsafe_allow_html=True)
    st.plotly_chart(chart_mouvements_par_mois(df_mvt), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with c_pays:
    st.markdown('<div class="card" style="padding:.75rem 1rem .5rem 1rem">', unsafe_allow_html=True)
    st.plotly_chart(chart_repartition_pays(df_pays), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with c_dev:
    st.markdown('<div class="card" style="padding:.75rem 1rem .5rem 1rem">', unsafe_allow_html=True)
    st.plotly_chart(chart_repartition_devise(df_devise), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PARTS PAR INVESTISSEUR
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(divider(), unsafe_allow_html=True)
st.markdown(section_header("Parts par investisseur", "👥", "#7C3AED"), unsafe_allow_html=True)

if df_parts is not None and not df_parts.empty:
    st.markdown('<div class="card" style="padding:1.25rem 1.5rem">', unsafe_allow_html=True)
    for i, (_, row) in enumerate(df_parts.iterrows()):
        pct_inv = float(row["part_pct"])
        pct_obj_sep = float(row["net_gnf"]) / OBJECTIF_SEPTEMBRE_MONTANT * 100 if OBJECTIF_SEPTEMBRE_MONTANT else 0.0
        pct_obj_dec = float(row["net_gnf"]) / OBJECTIF_DECEMBRE_MONTANT * 100 if OBJECTIF_DECEMBRE_MONTANT else 0.0
        cn, cb, co, cv = st.columns([2.3, 4.2, 2.6, 2.4])
        with cn:
            st.markdown(
                f'<div style="font-size:.87rem;font-weight:700;color:#1E293B;padding-top:.25rem">{row["nom"]}</div>',
                unsafe_allow_html=True,
            )
        with cb:
            st.markdown(progress_labeled(pct_inv, color="auto"), unsafe_allow_html=True)
        with co:
            st.markdown(
                f'<div style="display:flex;gap:.35rem;justify-content:center">'
                f'<span style="font-size:.68rem;font-weight:800;color:#2563EB;background:#EFF6FF;'
                f'padding:.2rem .4rem;border-radius:5px">Sept. {fmt_pct(pct_obj_sep)}</span>'
                f'<span style="font-size:.68rem;font-weight:800;color:#7C3AED;background:#F5F3FF;'
                f'padding:.2rem .4rem;border-radius:5px">Déc. {fmt_pct(pct_obj_dec)}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with cv:
            st.markdown(
                f'<div style="text-align:right;padding-top:.05rem">'
                f'<span style="font-size:.87rem;font-weight:800;color:#0F172A">{fmt_gnf(row["net_gnf"])}</span>'
                f'<br><span style="font-size:.7rem;color:#94A3B8">{fmt_pct(pct_inv)}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        if i < len(df_parts) - 1:
            st.markdown('<hr style="border:none;border-top:1px solid #F1F5F9;margin:.35rem 0">', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
else:
    st.markdown(
        empty_state("💰", "Aucun apport enregistré",
                    "Créez des investisseurs et enregistrez des apports pour voir leur répartition."),
        unsafe_allow_html=True,
    )

# ══════════════════════════════════════════════════════════════════════════════
# ACTIVITÉ RÉCENTE
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(divider(), unsafe_allow_html=True)

col_hd, col_lk = st.columns([5, 1])
with col_hd:
    st.markdown(section_header("Activité récente", "🕐", "#D97706"), unsafe_allow_html=True)
with col_lk:
    st.markdown(spacer("1rem"), unsafe_allow_html=True)
    st.page_link("pages/7_Historique.py", label="Voir tout →", icon="📜")

if df_mvt is not None and not df_mvt.empty:
    df_rec = df_mvt.copy()
    df_rec["date"] = pd.to_datetime(df_rec["date"], errors="coerce")
    df_rec["montant_converti_gnf"] = pd.to_numeric(df_rec["montant_converti_gnf"], errors="coerce").fillna(0)
    df_rec = df_rec.sort_values("date", ascending=False).head(8)

    if df_inv is not None and not df_inv.empty:
        noms = df_inv.set_index("id")["nom"].to_dict()
        df_rec["investisseur"] = df_rec["investisseur_id"].map(noms).fillna("—")
    else:
        df_rec["investisseur"] = "—"

    st.markdown('<div class="card" style="padding:1rem 1.25rem">', unsafe_allow_html=True)

    # En-têtes
    h1, h2, h3, h4, h5 = st.columns([1.5, 2, 2.5, 3, 4])
    for col, lbl in zip([h1, h2, h3, h4, h5], ["Date", "Type", "Investisseur", "Montant (GNF)", "Commentaire"]):
        with col:
            st.markdown(f'<div class="th">{lbl}</div>', unsafe_allow_html=True)
    st.markdown('<hr style="border:none;border-top:1.5px solid #F1F5F9;margin:.3rem 0 .5rem 0">', unsafe_allow_html=True)

    for i, (_, row) in enumerate(df_rec.iterrows()):
        in_cap = str(row.get("compte_dans_capital", "")).lower() in ["true", "1", "oui"]
        c1, c2, c3, c4, c5 = st.columns([1.5, 2, 2.5, 3, 4])
        with c1:
            st.markdown(f'<div class="row-date">{str(row["date"])[:10] if pd.notna(row["date"]) else "—"}</div>', unsafe_allow_html=True)
        with c2:
            st.markdown(badge_mouvement(str(row["type_mouvement"])), unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div style="font-size:.84rem;font-weight:600;color:#334155">{row.get("investisseur","—")}</div>', unsafe_allow_html=True)
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
            st.markdown(f'<div class="row-comment" style="padding-top:.2rem">{str(row.get("commentaire",""))[:65]}</div>', unsafe_allow_html=True)

        if i < len(df_rec) - 1:
            st.markdown('<hr style="border:none;border-top:1px solid #F8FAFC;margin:.25rem 0">', unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

else:
    st.markdown(
        empty_state("💸", "Aucun mouvement enregistré",
                    "Commencez par ajouter un investisseur, créer un compte, puis enregistrer un apport."),
        unsafe_allow_html=True,
    )

st.markdown(spacer("2rem"), unsafe_allow_html=True)
