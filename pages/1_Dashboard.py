"""Tableau de bord — Capital Legend Farm."""

import streamlit as st
import pandas as pd
from datetime import date

from utils.config import (
    CAPITAL_CIBLE_GNF,
    OBJECTIF_SEPTEMBRE_ID, OBJECTIF_SEPTEMBRE_NOM, OBJECTIF_SEPTEMBRE_MONTANT, OBJECTIF_SEPTEMBRE_DATE,
    OBJECTIF_DECEMBRE_ID, OBJECTIF_DECEMBRE_NOM, OBJECTIF_DECEMBRE_MONTANT, OBJECTIF_DECEMBRE_DATE,
)
from utils.data_loader import (
    get_investisseurs, get_comptes, get_mouvements,
    get_objectifs, get_taux, get_depenses, is_demo_mode,
)
from utils.calculs import (
    calculer_capital_total, calculer_capital_breakdown, calculer_bilan_capital,
    parts_par_investisseur, valeurs_par_compte,
    repartition_par_pays, repartition_par_devise,
    evolution_capital, evolution_apports_par_investisseur,
    progression_objectifs, get_dernier_taux,
)
from utils.formatting import (
    inject_css, kpi_card, hero_banner, section_header, page_header,
    summary_bar, fmt_gnf, fmt_pct, fmt_taux, fmt_eur,
    badge_mouvement, progress_bar, progress_labeled,
    divider, spacer, empty_state, stat_row,
)
from utils.charts import (
    chart_evolution_capital, chart_parts_investisseurs,
    chart_evolution_apports_investisseurs,
    chart_frais_par_investisseur,
    chart_repartition_pays, chart_repartition_devise,
    chart_mouvements_par_mois,
)
from utils.runtime import is_read_only_mode

inject_css()

# ── Données ───────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60, show_spinner=False)
def _load():
    return (
        get_investisseurs(), get_comptes(), get_mouvements(),
        get_objectifs(), get_taux(), get_depenses(),
    )

df_inv, df_cpt, df_mvt, df_obj, df_taux, df_dep = _load()

# ── Calculs ───────────────────────────────────────────────────────────────────
capital_total     = calculer_capital_total(df_mvt, df_cpt)
pct_global        = capital_total / CAPITAL_CIBLE_GNF * 100
dernier_taux      = get_dernier_taux(df_taux)
df_parts          = parts_par_investisseur(df_mvt, df_inv)
df_pays           = repartition_par_pays(df_mvt, df_cpt)
df_devise         = repartition_par_devise(df_mvt, df_cpt)
df_evolution      = evolution_capital(df_mvt, df_cpt)
df_evolution_inv  = evolution_apports_par_investisseur(df_mvt, df_inv)
capital_breakdown = calculer_capital_breakdown(df_mvt, df_cpt)
total_eur         = capital_breakdown["total_eur"]
total_gnf         = capital_breakdown["total_gnf"]
total_eur_gnf     = capital_breakdown["valorisation_eur_gnf"]
nb_inv            = len(df_inv) if df_inv is not None else 0
nb_mvt            = len(df_mvt) if df_mvt is not None else 0

# Frais et reste à compléter
_df_frais = df_mvt[df_mvt["type_mouvement"] == "frais_retrait"] if df_mvt is not None and not df_mvt.empty else None
total_frais = float(pd.to_numeric(_df_frais["montant_converti_gnf"], errors="coerce").sum()) if _df_frais is not None and not _df_frais.empty else 0.0
reste_a_completer = max(0.0, CAPITAL_CIBLE_GNF - capital_total)

# Bilan capital consolidé
bilan = calculer_bilan_capital(df_mvt, df_cpt, df_dep)

# Soldes par compte pour le bloc "Où est l'argent ?"
df_valeurs_cpt = valeurs_par_compte(df_mvt, df_cpt)

# Alerte frais : rythme mensuel et projection
_date_debut = None
if df_mvt is not None and not df_mvt.empty:
    _dates = pd.to_datetime(df_mvt["date"], errors="coerce").dropna()
    if not _dates.empty:
        _date_debut = _dates.min()
_mois_ecoules = max(
    ((pd.Timestamp.now() - _date_debut).days / 30.0) if _date_debut is not None else 1.0,
    0.5,
)
_rythme_frais_mensuel = total_frais / _mois_ecoules
_mois_vers_dec = max((pd.Timestamp("2026-12-31") - pd.Timestamp.now()).days / 30.0, 0.0)
_projection_frais_dec = total_frais + _rythme_frais_mensuel * _mois_vers_dec
_part_frais_pct = (total_frais / bilan["capital_brut_apporte"] * 100) if bilan["capital_brut_apporte"] > 0 else 0.0

# Merge objectifs hardcodés + objectifs personnalisés du CSV
_obj_principaux = pd.DataFrame([
    {"id": OBJECTIF_SEPTEMBRE_ID, "nom_objectif": OBJECTIF_SEPTEMBRE_NOM,
     "montant_cible_gnf": OBJECTIF_SEPTEMBRE_MONTANT, "date_cible": OBJECTIF_SEPTEMBRE_DATE,
     "description": "50% du capital cible — 250 millions GNF", "actif": True},
    {"id": OBJECTIF_DECEMBRE_ID, "nom_objectif": OBJECTIF_DECEMBRE_NOM,
     "montant_cible_gnf": OBJECTIF_DECEMBRE_MONTANT, "date_cible": OBJECTIF_DECEMBRE_DATE,
     "description": "100% du capital cible — 500 millions GNF", "actif": True},
])
if df_obj is None or df_obj.empty:
    _df_obj_all = _obj_principaux
else:
    _ids_existants = set(df_obj["id"].astype(str)) if "id" in df_obj.columns else set()
    _manquants = _obj_principaux[~_obj_principaux["id"].astype(str).isin(_ids_existants)]
    _df_obj_all = pd.concat([df_obj, _manquants], ignore_index=True)

df_obj_prog = progression_objectifs(_df_obj_all, capital_total)

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
k1, k2, k3, k4, k5 = st.columns(5)

with k1:
    st.markdown(kpi_card(
        "Capital valorisé", fmt_gnf(capital_total),
        sub="Total GNF valorisé (EUR + GNF)", color="blue", icon="💼",
    ), unsafe_allow_html=True)
with k2:
    st.markdown(kpi_card(
        "Disponible en GNF", fmt_gnf(total_gnf),
        sub="En comptes GNF — Guinée", color="green", icon="🇬🇳",
    ), unsafe_allow_html=True)
with k3:
    st.markdown(kpi_card(
        "Disponible en EUR", fmt_eur(total_eur),
        sub=f"≈ {fmt_gnf(total_eur_gnf)} valorisé", color="violet", icon="🇪🇺",
    ), unsafe_allow_html=True)
with k4:
    st.markdown(kpi_card(
        "Frais payés", fmt_gnf(total_frais),
        sub="Frais de retrait cumulés", color="amber", icon="🏧",
    ), unsafe_allow_html=True)
with k5:
    st.markdown(kpi_card(
        "Reste à compléter", fmt_gnf(reste_a_completer),
        sub=f"Objectif : {fmt_gnf(CAPITAL_CIBLE_GNF)}", color="red", icon="🎯",
    ), unsafe_allow_html=True)

# ── Résumé financier ──────────────────────────────────────────────────────────
st.markdown(spacer("0.5rem"), unsafe_allow_html=True)
st.markdown(
    summary_bar([
        ("Capital cible",        fmt_gnf(CAPITAL_CIBLE_GNF),  "navy"),
        ("Capital actuel",       fmt_gnf(capital_total),       "blue"),
        ("Reste à compléter",    fmt_gnf(reste_a_completer),   "red"),
        ("Progression",          fmt_pct(pct_global),          "green"),
        ("Dernier taux EUR/GNF", fmt_taux(dernier_taux),       "amber"),
        ("Frais de retrait",     fmt_gnf(total_frais),         "violet"),
    ]),
    unsafe_allow_html=True,
)

# ══════════════════════════════════════════════════════════════════════════════
# BILAN CAPITAL
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(divider(), unsafe_allow_html=True)
st.markdown(section_header("Bilan capital", "📊", "#0F172A"), unsafe_allow_html=True)

_b1, _b2, _b3, _b4, _b5 = st.columns(5)
with _b1:
    st.markdown(kpi_card(
        "Capital brut apporté", fmt_gnf(bilan["capital_brut_apporte"]),
        sub="Somme de tous les apports", color="navy", icon="💰",
    ), unsafe_allow_html=True)
with _b2:
    st.markdown(kpi_card(
        "Frais perdus", fmt_gnf(bilan["total_frais"]),
        sub=f"{fmt_pct(_part_frais_pct)} du capital brut", color="amber", icon="🏧",
    ), unsafe_allow_html=True)
with _b3:
    st.markdown(kpi_card(
        "Dépenses construction", fmt_gnf(bilan["depenses_construction_payees"]),
        sub=f"Budget total : {fmt_gnf(bilan['depenses_construction_total'])}", color="orange", icon="🏗️",
    ), unsafe_allow_html=True)
with _b4:
    st.markdown(kpi_card(
        "Capital en comptes", fmt_gnf(bilan["capital_total_valorise"]),
        sub="EUR valorisé + GNF disponible", color="blue", icon="🏦",
    ), unsafe_allow_html=True)
with _b5:
    st.markdown(kpi_card(
        "Liquidités après travaux", fmt_gnf(bilan["capital_liquide_apres_depenses"]),
        sub="Capital comptes − dépenses payées", color="green", icon="✅",
    ), unsafe_allow_html=True)

st.markdown(spacer("0.25rem"), unsafe_allow_html=True)
st.markdown(
    f'<div style="background:#FFF7ED;border:1px solid #FED7AA;border-radius:10px;padding:.65rem 1rem;'
    f'font-size:.78rem;color:#9A3412;font-weight:500">'
    f'ℹ️ <strong>Lecture du bilan</strong> — Le <em>capital brut apporté</em> est la somme brute de tous '
    f'les apports valorisés en GNF. Le <em>capital en comptes</em> utilise la simulation FIFO '
    f'(taux réels de transfert) et peut différer du brut si des écarts de taux ont eu lieu. '
    f'Les <em>dépenses construction</em> sont une vue de pilotage : elles ne sont pas encore '
    f'déduites de la logique officielle du capital tant qu\'elles ne sont pas reliées aux mouvements.'
    f'</div>',
    unsafe_allow_html=True,
)

# ══════════════════════════════════════════════════════════════════════════════
# ALERTE FRAIS
# ══════════════════════════════════════════════════════════════════════════════
if total_frais > 0:
    st.markdown(divider(), unsafe_allow_html=True)
    st.markdown(section_header("Alerte frais", "🏧", "#D97706"), unsafe_allow_html=True)
    _frais_alert_color = "#FEF2F2" if _part_frais_pct > 2 else "#ECFDF5"
    _frais_alert_border = "#FECACA" if _part_frais_pct > 2 else "#A7F3D0"
    _frais_alert_txt = "#991B1B" if _part_frais_pct > 2 else "#065F46"
    _frais_icon = "⚠️" if _part_frais_pct > 2 else "✅"
    _frais_msg = (
        f"Les frais représentent <strong>{fmt_pct(_part_frais_pct)}</strong> du capital brut. "
        f"Au rythme actuel (<strong>{fmt_gnf(_rythme_frais_mensuel)}/mois</strong>), "
        f"la projection à fin décembre 2026 est de <strong>{fmt_gnf(_projection_frais_dec)}</strong> de frais cumulés."
    )
    st.markdown(
        f'<div style="background:{_frais_alert_color};border:1px solid {_frais_alert_border};'
        f'border-radius:10px;padding:.75rem 1.1rem;font-size:.82rem;color:{_frais_alert_txt};font-weight:500">'
        f'{_frais_icon} {_frais_msg}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(spacer("0.25rem"), unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# OBJECTIFS SEPTEMBRE & DÉCEMBRE
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(divider(), unsafe_allow_html=True)
st.markdown(section_header("Objectifs", "🎯", "#059669"), unsafe_allow_html=True)

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

if df_obj_prog is not None and not df_obj_prog.empty:
    _actifs_dash = df_obj_prog[df_obj_prog["actif"].astype(str).str.lower() == "true"]
    _obj_rows = list(_actifs_dash.iterrows())
    for i in range(0, max(len(_obj_rows), 1), 2):
        _pair = _obj_rows[i:i + 2]
        _cols = st.columns(len(_pair)) if len(_pair) > 1 else st.columns([1, 1])
        for j, (_, _row) in enumerate(_pair):
            with _cols[j]:
                st.markdown(_obj_card(
                    str(_row["nom_objectif"]),
                    str(_row.get("description", "")),
                    float(_row["progress_pct"]),
                    capital_total,
                    float(_row["montant_cible_gnf"]),
                    float(_row["reste_gnf"]),
                    str(_row.get("date_cible", "")),
                    bool(_row["atteint"]),
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
# GRAPHIQUE : Évolution des parts par investisseur
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(spacer("0.5rem"), unsafe_allow_html=True)
st.markdown('<div class="card" style="padding:.75rem 1rem .5rem 1rem">', unsafe_allow_html=True)
if df_evolution_inv is not None and not df_evolution_inv.empty:
    st.plotly_chart(chart_evolution_apports_investisseurs(df_evolution_inv), use_container_width=True)
else:
    st.markdown(empty_state("📈", "Aucune donnée", "Enregistrez des apports pour voir l'évolution par investisseur."), unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# GRAPHIQUES LIGNE 2 : Mouvements pleine largeur
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(spacer("0.75rem"), unsafe_allow_html=True)
st.markdown('<div class="card" style="padding:.75rem 1rem .5rem 1rem">', unsafe_allow_html=True)
st.plotly_chart(chart_mouvements_par_mois(df_mvt), use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

# Camemberts Pays / Devise côte à côte
st.markdown(spacer("0.5rem"), unsafe_allow_html=True)
c_pays, c_dev = st.columns(2)

with c_pays:
    st.markdown('<div class="card" style="padding:.75rem 1rem .5rem 1rem">', unsafe_allow_html=True)
    st.plotly_chart(chart_repartition_pays(df_pays), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with c_dev:
    st.markdown('<div class="card" style="padding:.75rem 1rem .5rem 1rem">', unsafe_allow_html=True)
    st.plotly_chart(chart_repartition_devise(df_devise), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# OÙ EST L'ARGENT ?
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(divider(), unsafe_allow_html=True)
st.markdown(section_header("Où est l'argent ?", "🗺️", "#0D9488"), unsafe_allow_html=True)

_col_cpt, _col_geo = st.columns([3, 2])

with _col_cpt:
    st.markdown('<div class="card" style="padding:1.1rem 1.4rem">', unsafe_allow_html=True)
    st.markdown(
        '<div style="font-size:.68rem;font-weight:700;text-transform:uppercase;letter-spacing:.09em;'
        'color:#94A3B8;margin-bottom:.65rem">Solde par compte</div>',
        unsafe_allow_html=True,
    )
    if df_valeurs_cpt is not None and not df_valeurs_cpt.empty:
        _noms_inv_map = df_inv.set_index("id")["nom"].to_dict() if df_inv is not None and not df_inv.empty else {}
        for _, _cpt_row in df_valeurs_cpt.sort_values("valeur_gnf", ascending=False).iterrows():
            _valeur = float(_cpt_row["valeur_gnf"])
            if _valeur <= 0:
                continue
            _devise = str(_cpt_row.get("devise", "GNF")).upper()
            _pays = str(_cpt_row.get("pays", "—"))
            _type_c = str(_cpt_row.get("type_compte", ""))
            _flag = "🇫🇷" if _pays == "France" else ("🇬🇳" if _pays == "Guinée" else "🌍")
            _val_txt = fmt_gnf(_valeur)
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;align-items:center;'
                f'padding:.45rem 0;border-bottom:1px solid #F1F5F9">'
                f'<div>'
                f'  <span style="font-size:.84rem;font-weight:600;color:#1E293B">{_cpt_row["nom"]}</span>'
                f'  <span style="font-size:.7rem;color:#94A3B8;margin-left:.5rem">{_flag} {_pays} · {_devise}</span>'
                f'</div>'
                f'<span style="font-size:.88rem;font-weight:800;color:#0F172A">{_val_txt}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        _total_val = float(df_valeurs_cpt["valeur_gnf"].sum())
        st.markdown(
            f'<div style="display:flex;justify-content:space-between;padding:.55rem 0 0 0;margin-top:.2rem">'
            f'<span style="font-size:.78rem;font-weight:700;color:#475569">Total valorisé</span>'
            f'<span style="font-size:.9rem;font-weight:800;color:#2563EB">{fmt_gnf(_total_val)}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(empty_state("🏦", "Aucun compte", "Créez des comptes et enregistrez des mouvements."), unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with _col_geo:
    # Répartition Guinée / France
    _en_guinee = float(df_pays[df_pays["pays"] == "Guinée"]["montant_gnf"].sum()) if df_pays is not None and not df_pays.empty and "Guinée" in df_pays["pays"].values else 0.0
    _en_france = float(df_pays[df_pays["pays"] == "France"]["montant_gnf"].sum()) if df_pays is not None and not df_pays.empty and "France" in df_pays["pays"].values else 0.0
    _total_geo = _en_guinee + _en_france or 1.0
    st.markdown('<div class="card" style="padding:1.1rem 1.4rem">', unsafe_allow_html=True)
    st.markdown(
        '<div style="font-size:.68rem;font-weight:700;text-transform:uppercase;letter-spacing:.09em;'
        'color:#94A3B8;margin-bottom:.65rem">Répartition géographique</div>',
        unsafe_allow_html=True,
    )
    for _nom, _val, _color, _flag in [
        ("En Guinée (GNF)", _en_guinee, "#10b981", "🇬🇳"),
        ("En France (EUR valorisé)", _en_france, "#3b82f6", "🇫🇷"),
    ]:
        _pct_g = _val / _total_geo * 100
        st.markdown(
            f'<div style="margin-bottom:.8rem">'
            f'<div style="display:flex;justify-content:space-between;margin-bottom:.25rem">'
            f'  <span style="font-size:.8rem;font-weight:600;color:#475569">{_flag} {_nom}</span>'
            f'  <span style="font-size:.82rem;font-weight:800;color:#0F172A">{fmt_gnf(_val)}</span>'
            f'</div>'
            f'<div style="height:6px;background:#F1F5F9;border-radius:3px">'
            f'  <div style="width:{min(_pct_g,100):.1f}%;height:100%;background:{_color};border-radius:3px"></div>'
            f'</div>'
            f'<div style="font-size:.68rem;color:#94A3B8;margin-top:.15rem">{_pct_g:.1f} % du total</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    st.markdown(
        f'<div style="border-top:1px solid #F1F5F9;padding-top:.65rem;margin-top:.3rem">'
        f'<div style="font-size:.68rem;font-weight:700;text-transform:uppercase;letter-spacing:.09em;'
        f'color:#94A3B8;margin-bottom:.4rem">Par devise</div>',
        unsafe_allow_html=True,
    )
    _en_eur_val = bilan["capital_total_valorise"] - total_gnf if total_gnf < bilan["capital_total_valorise"] else 0.0
    for _dv, _val_d, _color_d in [
        ("GNF (liquide Guinée)", total_gnf, "#10b981"),
        ("EUR (valorisé en GNF)", total_eur_gnf, "#3b82f6"),
    ]:
        _pct_d = _val_d / max(bilan["capital_total_valorise"], 1) * 100
        st.markdown(
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'padding:.35rem 0;border-bottom:1px solid #F8FAFC">'
            f'<span style="font-size:.78rem;color:#64748B;font-weight:500">{_dv}</span>'
            f'<div style="text-align:right">'
            f'<div style="font-size:.82rem;font-weight:700;color:#0F172A">{fmt_gnf(_val_d)}</div>'
            f'<div style="font-size:.67rem;color:#94A3B8">{_pct_d:.1f} %</div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )
    st.markdown("</div></div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TRAVAUX / CONSTRUCTION
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(divider(), unsafe_allow_html=True)
_col_trav_hd, _col_trav_lk = st.columns([5, 1])
with _col_trav_hd:
    st.markdown(section_header("Travaux / Construction", "🏗️", "#EA580C"), unsafe_allow_html=True)
with _col_trav_lk:
    st.markdown(spacer("1rem"), unsafe_allow_html=True)
    st.page_link("pages/8_Depenses_Avant_Exploitation.py", label="Voir le détail →", icon="🏗️")

_t1, _t2, _t3, _t4 = st.columns(4)
with _t1:
    st.markdown(kpi_card(
        "Budget total prévu", fmt_gnf(bilan["depenses_construction_total"]),
        sub="Toutes catégories confondues", color="slate", icon="📋",
    ), unsafe_allow_html=True)
with _t2:
    st.markdown(kpi_card(
        "Déjà payé", fmt_gnf(bilan["depenses_construction_payees"]),
        sub="Dépenses avec statut Payé", color="green", icon="✅",
    ), unsafe_allow_html=True)
with _t3:
    st.markdown(kpi_card(
        "En attente", fmt_gnf(bilan["depenses_construction_attente"]),
        sub="À payer ou partiellement payé", color="amber", icon="⏳",
    ), unsafe_allow_html=True)
with _t4:
    _pct_trav = (bilan["depenses_construction_payees"] / bilan["depenses_construction_total"] * 100) if bilan["depenses_construction_total"] > 0 else 0.0
    st.markdown(kpi_card(
        "Avancement paiements", fmt_pct(_pct_trav),
        sub="Part des dépenses déjà réglées", color="blue", icon="📈",
    ), unsafe_allow_html=True)

if bilan["depenses_construction_total"] == 0:
    st.markdown(
        f'<div style="background:#F1F5F9;border-radius:10px;padding:.65rem 1rem;'
        f'font-size:.8rem;color:#64748B;text-align:center">'
        f'Aucune dépense de construction enregistrée — '
        f'<a href="/8_Depenses_Avant_Exploitation" style="color:#2563EB;font-weight:600">Ajouter des dépenses →</a>'
        f'</div>',
        unsafe_allow_html=True,
    )

# ══════════════════════════════════════════════════════════════════════════════
# FRAIS DE RETRAIT PAR INVESTISSEUR
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(spacer("0.5rem"), unsafe_allow_html=True)
st.markdown('<div class="card" style="padding:.75rem 1rem .5rem 1rem">', unsafe_allow_html=True)
st.plotly_chart(chart_frais_par_investisseur(df_mvt, df_inv), use_container_width=True)
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
