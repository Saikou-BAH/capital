"""Page Objectifs."""

import streamlit as st
import pandas as pd
from datetime import date, timedelta

from utils.data_loader import (
    get_objectifs, get_mouvements, get_comptes, add_objectif, update_objectif,
    get_plan_apports, add_plan_apport, update_plan_apport, delete_plan_apport,
)
from utils.config import (
    OBJECTIF_SEPTEMBRE_ID, OBJECTIF_SEPTEMBRE_NOM, OBJECTIF_SEPTEMBRE_MONTANT, OBJECTIF_SEPTEMBRE_DATE,
    OBJECTIF_DECEMBRE_ID, OBJECTIF_DECEMBRE_NOM, OBJECTIF_DECEMBRE_MONTANT, OBJECTIF_DECEMBRE_DATE,
    PALIERS_CAPITAL,
)
from utils.calculs import (
    calculer_capital_total, progression_objectifs,
    calculer_palier, apport_moyen_mensuel, date_atteinte_palier,
    calculer_projection_plan, TOLERANCE_AVANCE_JOURS,
    realise_par_mois, statut_apport_mensuel, synthese_plan_vs_reel,
    trajectoire_ideale_palier, prochain_apport_prevu, montant_ajustement_necessaire,
    appliquer_scenario_plan,
)
from utils.formatting import (
    inject_css, kpi_card, section_header, page_header, empty_state,
    fmt_gnf, fmt_gnf_court, fmt_pct, fmt_date_fr, fmt_jours_restants, progress_bar, divider, spacer,
)
from utils.charts import chart_objectifs_gauge
from utils.runtime import is_read_only_mode, read_only_notice

inject_css()

st.markdown(page_header("Objectifs", "🎯", "Suivez la progression vers les cibles de capital."), unsafe_allow_html=True)
st.page_link("pages/1_Dashboard.py", label="← Retour au tableau de bord", icon="📊")

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
        "cloture": False,
        "capital_gele_gnf": 0,
        "date_cloture": "",
    },
    {
        "id": OBJECTIF_DECEMBRE_ID,
        "nom_objectif": OBJECTIF_DECEMBRE_NOM,
        "montant_cible_gnf": OBJECTIF_DECEMBRE_MONTANT,
        "date_cible": OBJECTIF_DECEMBRE_DATE,
        "description": "100% du capital cible — 500 millions GNF",
        "actif": True,
        "cloture": False,
        "capital_gele_gnf": 0,
        "date_cloture": "",
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
_est_cloture_kpi = (
    df_obj["cloture"].astype(str).str.lower() == "true"
    if "cloture" in df_obj.columns else pd.Series(False, index=df_obj.index)
)
nb_act = len(df_obj[(df_obj["actif"].astype(str).str.lower() == "true") & (~_est_cloture_kpi)]) if not df_obj.empty else 0

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(kpi_card("Capital actuel", fmt_gnf(capital), icon="💼", color="blue"), unsafe_allow_html=True)
with c2:
    st.markdown(kpi_card("Objectifs actifs", str(nb_act), icon="🎯", color="amber"), unsafe_allow_html=True)
with c3:
    st.markdown(kpi_card("Objectifs atteints", str(nb_att), icon="✅", color="green"), unsafe_allow_html=True)

st.markdown(divider(), unsafe_allow_html=True)

# ── Cartes objectifs — 5 paliers de capital ────────────────────────────────────
st.markdown(section_header("Suivi des objectifs", "📊", "#B65C2E"), unsafe_allow_html=True)

@st.cache_data(ttl=60)
def load_plan():
    return get_plan_apports()

df_plan = load_plan()
AUJOURDHUI = date.today()

_apport_moy = apport_moyen_mensuel(df_mvt)  # rythme réel — inchangé

# Apports prévus pour le mois courant (utilisé pour "Capital prévu fin de mois"),
# lus depuis le plan d'apports GNF — jamais de conversion, jamais de devise.
_mois_actuel_periode = pd.Timestamp(AUJOURDHUI).to_period("M")
if df_plan is not None and not df_plan.empty:
    _dfp = df_plan.copy()
    _dfp["mois_periode"] = pd.to_datetime(_dfp["mois"], errors="coerce").dt.to_period("M")
    _dfp["montant_prevu_gnf"] = pd.to_numeric(_dfp["montant_prevu_gnf"], errors="coerce").fillna(0.0)
    _apports_prevus_mois_actuel = float(_dfp.loc[_dfp["mois_periode"] == _mois_actuel_periode, "montant_prevu_gnf"].sum())
else:
    _apports_prevus_mois_actuel = 0.0

# Calcule tous les indicateurs de chaque palier — logique centralisée dans
# utils.calculs.calculer_palier (rythme réel, INCHANGÉE) et calculer_projection_plan
# (plan personnel, 100% GNF, strictement séparée du réel).
_paliers_calc = []
for _i_p, _p in enumerate(PALIERS_CAPITAL):
    _c = calculer_palier(capital, _p["montant_cible_gnf"], _p["date_cible"], _apport_moy, _apports_prevus_mois_actuel)
    _proj_plan = calculer_projection_plan(capital, _p["montant_cible_gnf"], _p["date_cible"], df_plan, AUJOURDHUI, df_mvt)
    _c.update(_proj_plan)
    _c["id"] = _p["id"]
    _c["nom"] = _p["nom"]
    _c["icone"] = _p.get("icone", "🎯")
    # La date réelle d'atteinte vient TOUJOURS de l'historique réel des mouvements,
    # jamais du plan — un palier "prévu atteint" n'est pas un palier réellement atteint.
    _c["date_atteinte"] = date_atteinte_palier(df_mvt, df_cpt, _p["montant_cible_gnf"]) if _c["atteint"] else None
    # Trajectoire idéale : None pour le 1er palier (aucun point de départ défini,
    # jamais inventé) ; dérivée du palier précédent pour les suivants.
    _c["trajectoire"] = trajectoire_ideale_palier(capital, PALIERS_CAPITAL, _i_p, AUJOURDHUI)
    # Montant à ajouter au plan pour tenir la cible — 0 si le plan couvre déjà.
    _c["ajustement_necessaire"] = montant_ajustement_necessaire(_c["ecart_capital_planning"])
    _paliers_calc.append(_c)

# Le premier palier non atteint (staircase 200M → 250M → 300M → 400M → 500M)
# devient automatiquement l'objectif actif, mis en avant visuellement.
_idx_actif = next((i for i, c in enumerate(_paliers_calc) if not c["atteint"]), None)

# Prochain apport planifié (mois >= aujourd'hui), pour le résumé en tête de page.
_prochain_apport = prochain_apport_prevu(df_plan, AUJOURDHUI)

# Synthèse prévu vs réel — mêmes chiffres que la section "Plan d'apports" plus bas,
# calculés une seule fois ici pour alimenter le résumé compact.
_synth_resume = synthese_plan_vs_reel(df_plan, df_mvt, AUJOURDHUI)

_statut_color_map = {
    "green": ("#166534", "#dcfce7"),
    "blue":  ("#9C4B22", "#FBF0E7"),
    "amber": ("#92400e", "#fef3c7"),
    "red":   ("#991b1b", "#fee2e2"),
}
_lbl_style = "font-size:.63rem;font-weight:600;text-transform:none;letter-spacing:0;color:#7F7568;margin-bottom:.1rem"
_val_style = "font-size:.85rem;font-weight:700;color:#241F19"

# ── Résumé compact en tête de section (6 petites cartes KPI, mêmes composants
# que le reste de l'appli — desktop : 2 rangées de 3 ; mobile : Streamlit
# empile automatiquement les colonnes en une par ligne) ─────────────────────
_pal_actif = _paliers_calc[_idx_actif] if _idx_actif is not None else None

rc1, rc2, rc3 = st.columns(3)
with rc1:
    if _pal_actif is not None:
        st.markdown(kpi_card(
            "Palier actif", fmt_gnf_court(_pal_actif["montant_cible"]),
            sub=_pal_actif["nom"], color="blue", icon="🎯",
        ), unsafe_allow_html=True)
    else:
        st.markdown(kpi_card("Palier actif", "Tous atteints", sub="✅", color="green", icon="🎯"), unsafe_allow_html=True)
with rc2:
    if _pal_actif is not None:
        st.markdown(kpi_card(
            "Temps restant", fmt_jours_restants(_pal_actif["jours_restants"], False, None),
            sub=fmt_date_fr(_pal_actif["date_cible"]), color="amber", icon="⏳",
        ), unsafe_allow_html=True)
    else:
        st.markdown(kpi_card("Temps restant", "—", color="slate", icon="⏳"), unsafe_allow_html=True)
with rc3:
    if _prochain_apport is not None:
        st.markdown(kpi_card(
            "Prochain apport", fmt_gnf_court(_prochain_apport["montant_gnf"]),
            sub=fmt_date_fr(_prochain_apport["date"]), color="violet", icon="➡️",
        ), unsafe_allow_html=True)
    else:
        st.markdown(kpi_card("Prochain apport", "Aucun planifié", color="slate", icon="➡️"), unsafe_allow_html=True)

rc4, rc5, rc6 = st.columns(3)
with rc4:
    if _synth_resume["prevu_echu_gnf"] > 0:
        st.markdown(kpi_card(
            "Prévu vs réel", fmt_gnf_court(_synth_resume["ecart_gnf"]),
            sub=_synth_resume["statut"], color=_synth_resume["couleur_statut"], icon="📉",
        ), unsafe_allow_html=True)
    else:
        # Couvre à la fois "planning pas encore commencé" et "aucun plan enregistré"
        # — jamais un faux écart ni un faux %, le statut précis vient du calcul.
        st.markdown(kpi_card(
            "Prévu vs réel", "—", sub=_synth_resume["statut"], color="slate", icon="📉",
        ), unsafe_allow_html=True)
with rc5:
    _traj_actif = _pal_actif["trajectoire"] if _pal_actif is not None else None
    if _traj_actif is None:
        st.markdown(kpi_card("Trajectoire", "Non disponible", sub="Pas de point de départ pour ce palier", color="slate", icon="📍"), unsafe_allow_html=True)
    elif _traj_actif["pas_commence"]:
        st.markdown(kpi_card(
            "Trajectoire", "Pas encore commencée",
            sub=f"Démarre le {fmt_date_fr(_traj_actif['date_debut'])}", color="slate", icon="📍",
        ), unsafe_allow_html=True)
    else:
        st.markdown(kpi_card(
            "Trajectoire", fmt_gnf_court(_traj_actif["ecart_trajectoire"]),
            sub=_traj_actif["statut"], color=_traj_actif["couleur_statut"], icon="📍",
        ), unsafe_allow_html=True)
with rc6:
    if _pal_actif is not None and _pal_actif["ajustement_necessaire"] > 0:
        st.markdown(kpi_card(
            "Ajustement nécessaire", fmt_gnf_court(_pal_actif["ajustement_necessaire"]),
            sub=f"avant le {fmt_date_fr(_pal_actif['date_cible'])}", color="red", icon="⚠️",
        ), unsafe_allow_html=True)
    else:
        st.markdown(kpi_card("Ajustement nécessaire", "0 GNF", sub="✅ Aucun", color="green", icon="⚠️"), unsafe_allow_html=True)

st.markdown(spacer("0.8rem"), unsafe_allow_html=True)

for i_pal, calc in enumerate(_paliers_calc):
    est_actif = (i_pal == _idx_actif)
    atteint = calc["atteint"]
    pct = calc["progress_pct"]
    _sc, _sbg = _statut_color_map.get(calc["couleur_statut"], ("#4A4238", "#F5F1EA"))

    color   = "#3E7C51" if atteint else ("#B65C2E" if pct >= 50 else "#99651A")
    bar_col = "green"   if atteint else ("blue"    if pct >= 50 else "amber")

    if atteint:
        _date_prev_txt = f"Atteint le {fmt_date_fr(calc['date_atteinte'])}" if calc["date_atteinte"] else "Atteint"
    elif calc["date_previsionnelle"] is None:
        _date_prev_txt = "Prévision indisponible"
    else:
        _date_prev_txt = fmt_date_fr(calc["date_previsionnelle"])

    # L'indicateur d'effort change de forme selon la proximité de l'échéance —
    # un taux "par mois" n'a aucun sens à quelques jours de la cible.
    _effort_mode = calc["effort_mode"]
    if _effort_mode == "atteint":
        _effort_label, _effort_txt = "💰 Effort mensuel", "—"
    elif _effort_mode == "mensuel":
        _effort_label = "💰 Effort mensuel"
        _effort_txt = f"{fmt_gnf_court(calc['effort_mensuel'])} / mois"  # jamais de taux -> pas d'équivalent EUR
    elif _effort_mode == "avant_echeance":
        _effort_label, _effort_txt = "💰 Montant à apporter avant l'échéance", fmt_gnf(calc["reste_gnf"])
    elif _effort_mode == "aujourdhui":
        _effort_label, _effort_txt = "💰 Montant à apporter aujourd'hui", fmt_gnf(calc["reste_gnf"])
    else:  # "depasse"
        _effort_label, _effort_txt = "🔴 Échéance dépassée", f"Capital manquant : {fmt_gnf(calc['reste_gnf'])}"

    _apport_moy_txt = (
        fmt_gnf_court(calc["apport_mensuel_moyen"])  # jamais de taux -> pas d'équivalent EUR
        if calc["apport_mensuel_moyen"] else "Données insuffisantes"
    )

    # Écart PRÉVISIONNEL (projection du rythme réel vs date cible) — jamais
    # "de retard" avant l'échéance : c'est un risque projeté, pas un fait constaté.
    if atteint:
        _ecart_txt, _ecart_sous_texte = "—", ""
    elif calc["ecart_planning_jours"] is None:
        _ecart_txt, _ecart_sous_texte = "Indisponible", ""
    else:
        _ej = calc["ecart_planning_jours"]
        if _ej <= 0:
            _ecart_txt = f"{abs(_ej)} j d'avance"
            _ecart_sous_texte = ""
        else:
            _ecart_txt = f"+{_ej} jours (après la cible)"
            _ecart_sous_texte = (
                f"Au rythme réel actuel, l'objectif serait atteint environ {_ej} jours "
                "après la date cible." if _ej > TOLERANCE_AVANCE_JOURS else ""
            )

    # ── Projection SELON MON PLAN (100% GNF, strictement séparée du réel) ──────
    if atteint:
        _date_plan_txt = "Atteint"
    elif calc["date_selon_plan"] is None:
        _date_plan_txt = "Non atteint avec le planning actuel"
    else:
        _date_plan_txt = fmt_date_fr(calc["date_selon_plan"])

    _ecart_capital = calc["ecart_capital_planning"]
    if atteint:
        _marge_txt, _marge_color = "—", "#241F19"
    elif _ecart_capital >= 0:
        _marge_txt = f"✅ Besoin couvert par le planning · 🟢 Marge prévisionnelle : +{fmt_gnf(_ecart_capital)}"
        _marge_color = "#3E7C51"
    else:
        _marge_txt = f"🔴 Manque à couvrir : {fmt_gnf(abs(_ecart_capital))}"
        _marge_color = "#B3432F"

    # Apports prévus (avant l'échéance) VS reste réel — couverture du besoin par le seul planning.
    # Purement informatif : ne décide JAMAIS du statut du plan (voir _statut_du_plan),
    # qui se base uniquement sur la date d'atteinte projetée vs la date cible.
    if atteint:
        _apports_avant_txt, _couverture_txt = "—", "—"
    else:
        _apports_avant_txt = fmt_gnf(calc["apports_prevus_avant_echeance"])
        _cp = calc["couverture_plan_pct"]
        _couverture_txt = f"{_cp:.0f} %" if _cp is not None else "—"

    # Écart du PLAN (jours) — indépendant de l'écart "rythme réel" ci-dessus :
    # ici la projection vient des apports PRÉVUS, pas de l'historique réel.
    if atteint:
        _ecart_plan_txt = "—"
    elif calc["ecart_plan_jours"] is None:
        _ecart_plan_txt = "Non atteint avec le planning actuel"
    else:
        _epj = calc["ecart_plan_jours"]
        _ecart_plan_txt = f"{abs(_epj)} j d'avance" if _epj < 0 else (f"{_epj} j après la cible" if _epj > 0 else "Pile à la date cible")

    _sc_plan, _sbg_plan = _statut_color_map.get(calc["couleur_statut_plan"], ("#4A4238", "#F5F1EA"))
    _badge_statut_plan = (
        f'<span style="font-size:.65rem;font-weight:700;padding:.15rem .5rem;border-radius:20px;'
        f'background:{_sbg_plan};color:{_sc_plan};display:inline-block">{calc["statut_plan"]}</span>'
    )

    # ── Trajectoire idéale (ligne droite dans le temps vers ce palier) ─────────
    # Distincte du rythme réel et du plan. 3 états possibles :
    #   - None            : indisponible (1er palier, aucun point de départ défini, jamais inventé)
    #   - pas_commence     : la période de CE palier n'a pas encore débuté -> pas de jugement porté
    #   - normal           : trajectoire calculée et jugée
    _traj = calc["trajectoire"]
    if atteint:
        _traj_html = ""
    elif _traj is None:
        _traj_html = (
            f'<div><div style="{_lbl_style}">📍 Trajectoire idéale</div>'
            f'<div style="{_val_style};color:#7F7568">Trajectoire idéale indisponible (pas de point de départ pour ce palier)</div></div>'
        )
    elif _traj["pas_commence"]:
        _traj_html = (
            f'<div><div style="{_lbl_style}">📍 Trajectoire idéale</div>'
            f'<div style="{_val_style};color:#7F7568">Pas encore commencée — démarre le {fmt_date_fr(_traj["date_debut"])}</div></div>'
        )
    else:
        _sc_traj, _sbg_traj = _statut_color_map.get(_traj["couleur_statut"], ("#4A4238", "#F5F1EA"))
        _traj_html = (
            f'<div><div style="{_lbl_style}">📍 Capital attendu aujourd\'hui</div><div style="{_val_style}">{fmt_gnf(_traj["capital_ideal"])}</div></div>'
            f'<div><div style="{_lbl_style}">Écart de trajectoire</div>'
            f'<div style="{_val_style};color:{"#3E7C51" if _traj["ecart_trajectoire"] >= 0 else "#B3432F"}">'
            f'{"+" if _traj["ecart_trajectoire"] >= 0 else ""}{fmt_gnf(_traj["ecart_trajectoire"])}</div></div>'
            f'<div><div style="{_lbl_style}">Statut trajectoire</div><div>'
            f'<span style="font-size:.65rem;font-weight:700;padding:.15rem .5rem;border-radius:20px;'
            f'background:{_sbg_traj};color:{_sc_traj};display:inline-block">{_traj["statut"]}</span></div></div>'
        )

    # ── Alertes qui restent TOUJOURS visibles, même si le détail est replié ────
    _ajustement = calc["ajustement_necessaire"]
    if atteint or _ajustement <= 0:
        _ajustement_html = ""
    else:
        _ajustement_html = (
            '<div style="margin-top:.7rem;padding:.6rem .8rem;border-radius:8px;'
            'background:#FBEEEA;border:1px solid #E8C4BB">'
            '<div style="font-size:.72rem;font-weight:700;color:#991b1b;margin-bottom:.15rem">⚠️ Ajustement nécessaire</div>'
            f'<div style="font-size:.8rem;color:#7A2E1F">Ajoutez <strong>{fmt_gnf(_ajustement)}</strong> avant le '
            f'<strong>{fmt_date_fr(calc["date_cible"])}</strong> pour remettre ce palier dans les temps selon votre plan.</div>'
            "</div>"
        )

    # Un statut du plan défavorable (retard prévu, planning insuffisant) reste
    # visible directement sur la carte, même si le détail complet est replié.
    if not atteint and calc["couleur_statut_plan"] == "red":
        _statut_plan_alert_html = (
            '<div style="margin-top:.5rem;padding:.5rem .8rem;border-radius:8px;'
            'background:#FBEEEA;border:1px solid #E8C4BB;font-size:.8rem;font-weight:600;color:#991b1b">'
            f'{calc["statut_plan"]} (selon mon plan)'
            "</div>"
        )
    else:
        _statut_plan_alert_html = ""

    # Palier atteint : reste élégant mais plus discret. Palier actif : légèrement mis en avant.
    if atteint:
        _card_style = "opacity:.72"
    elif est_actif:
        _card_style = "border:2px solid #B65C2E;box-shadow:0 4px 14px rgba(182,92,46,.15)"
    else:
        _card_style = ""
    _badge_actif = (
        '<span style="font-size:.62rem;font-weight:700;padding:.1rem .5rem;border-radius:20px;'
        'background:#B65C2E;color:#fff;margin-left:.5rem;vertical-align:middle">🎯 Palier actif</span>'
        if est_actif else ""
    )

    # ── Carte principale : uniquement les informations les plus importantes ────
    _card_html = (
        f'<div class="obj-card" style="{_card_style}">'
        '<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:.6rem">'
        "<div>"
        f'<div class="obj-card-title">{calc["icone"]} {calc["nom"]} — {fmt_gnf_court(calc["montant_cible"])}{_badge_actif}</div>'
        "</div>"
        '<div style="text-align:right;flex-shrink:0;margin-left:1rem">'
        f'<div class="obj-pct" style="color:{color}">{fmt_pct(pct)}</div>'
        f'<span style="font-size:.65rem;font-weight:700;padding:.15rem .5rem;border-radius:20px;'
        f'background:{_sbg};color:{_sc};margin-top:.25rem;display:inline-block">{calc["statut"]}</span>'
        "</div>"
        "</div>"
        + progress_bar(pct, bar_col, "10px") +
        '<div style="display:flex;gap:1.6rem;margin-top:.8rem;flex-wrap:wrap">'
        f'<div><div style="{_lbl_style}">Capital actuel</div><div style="{_val_style}">{fmt_gnf(capital)}</div></div>'
        f'<div><div style="{_lbl_style}">Reste</div>'
        f'<div style="{_val_style};color:{"#3E7C51" if atteint else "#B3432F"}">'
        f'{fmt_gnf(calc["reste_gnf"]) if not atteint else "—"}</div></div>'
        f'<div><div style="{_lbl_style}">Date cible</div><div style="{_val_style}">{fmt_date_fr(calc["date_cible"])}</div></div>'
        f'<div><div style="{_lbl_style}">⏳ Jours restants</div><div style="{_val_style}">'
        f'{fmt_jours_restants(calc["jours_restants"], atteint, calc["date_atteinte"])}</div></div>'
        f'<div><div style="{_lbl_style}">📈 Selon rythme réel</div><div style="{_val_style}">{_date_prev_txt}</div></div>'
        f'<div><div style="{_lbl_style}">📅 Selon mon plan</div><div style="{_val_style}">{_date_plan_txt}</div></div>'
        f'<div><div style="{_lbl_style}">{_effort_label}</div><div style="{_val_style}">{_effort_txt}</div></div>'
        "</div>"
        + _ajustement_html
        + _statut_plan_alert_html
        + "</div>"
    )

    # ── Détails secondaires — repliés dans un expander, rien n'est supprimé ────
    _details_html = (
        '<div style="display:flex;gap:1.6rem;flex-wrap:wrap">'
        f'<div><div style="{_lbl_style}">Apport moyen mensuel (réel)</div><div style="{_val_style}">{_apport_moy_txt}</div></div>'
        f'<div><div style="{_lbl_style}">Apports prévus ce mois</div>'
        f'<div style="{_val_style}">{fmt_gnf(calc["apports_prevus_mois"])}</div></div>'
        f'<div><div style="{_lbl_style}">Capital prévu fin de mois</div>'
        f'<div style="{_val_style}">{fmt_gnf(calc["capital_prevu_fin_mois"])}</div></div>'
        f'<div><div style="{_lbl_style}">Écart prévisionnel (rythme réel)</div><div style="{_val_style}">{_ecart_txt}</div>'
        + (f'<div style="font-size:.68rem;color:#7F7568;margin-top:.15rem;max-width:220px">{_ecart_sous_texte}</div>' if _ecart_sous_texte else "")
        + '</div>'
        "</div>"
        '<div style="display:flex;gap:1.6rem;margin-top:.7rem;flex-wrap:wrap;padding-top:.7rem;border-top:1px dashed #E8E1D6">'
        f'<div><div style="{_lbl_style}">💰 Capital prévu à échéance</div><div style="{_val_style}">{fmt_gnf(calc["capital_prevu_echeance"])}</div></div>'
        f'<div><div style="{_lbl_style}">📅 Apports prévus avant échéance</div><div style="{_val_style}">{_apports_avant_txt}</div></div>'
        f'<div><div style="{_lbl_style}">Couverture du reste par le plan</div><div style="{_val_style}">{_couverture_txt}</div></div>'
        f'<div><div style="{_lbl_style}">Écart du plan</div><div style="{_val_style}">{_ecart_plan_txt}</div></div>'
        f'<div><div style="{_lbl_style}">Marge / manque prévisionnel</div>'
        f'<div style="{_val_style};color:{_marge_color}">{_marge_txt}</div></div>'
        f'<div><div style="{_lbl_style}">Statut du plan</div><div>{_badge_statut_plan}</div></div>'
        "</div>"
        '<div style="display:flex;gap:1.6rem;margin-top:.7rem;flex-wrap:wrap;padding-top:.7rem;border-top:1px dashed #E8E1D6">'
        + _traj_html +
        "</div>"
    )

    col_info, col_gauge = st.columns([3, 1])
    with col_info:
        st.markdown(_card_html, unsafe_allow_html=True)
        with st.expander("Voir les détails", expanded=False):
            st.markdown(_details_html, unsafe_allow_html=True)
    with col_gauge:
        st.markdown(spacer("0.5rem"), unsafe_allow_html=True)
        st.markdown('<div class="card" style="padding:.25rem">', unsafe_allow_html=True)
        st.plotly_chart(
            chart_objectifs_gauge(calc["nom"], pct, color), use_container_width=True,
            config={"displayModeBar": False}, key=f"gauge_palier_{i_pal}",
        )
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(spacer("0.25rem"), unsafe_allow_html=True)

# ── Plan d'apports prévisionnels (100% GNF) ─────────────────────────────────────
st.markdown(divider(), unsafe_allow_html=True)
st.markdown(section_header("Plan d'apports", "📅", "#6B5B95"), unsafe_allow_html=True)
st.caption(
    "Planning personnel en GNF, séparé du capital réel. Un apport prévu ne devient "
    "réel — et n'augmente le capital — que lorsqu'il est réellement enregistré dans les mouvements."
)

def _fmt_plan_label(_r) -> str:
    _mp = pd.to_datetime(_r["mois"], errors="coerce")
    _lbl_mois = fmt_date_fr(_mp.date()) if not pd.isna(_mp) else str(_r["mois"])
    return f'{_lbl_mois} — {fmt_gnf(_r["montant_prevu_gnf"])}'

_realise = realise_par_mois(df_mvt)  # pd.Series indexée par pd.Period('M'), en GNF réel

# ── Synthèse prévu vs réel (mois déjà échus uniquement) ────────────────────────
_synth = synthese_plan_vs_reel(df_plan, df_mvt, AUJOURDHUI)
sc1, sc2, sc3, sc4 = st.columns(4)
with sc1:
    st.markdown(kpi_card("Prévu échu", fmt_gnf(_synth["prevu_echu_gnf"]), icon="📋", color="slate"), unsafe_allow_html=True)
with sc2:
    st.markdown(kpi_card("Réellement apporté", fmt_gnf(_synth["reel_gnf"]), icon="💼", color="blue"), unsafe_allow_html=True)
with sc3:
    _c_ecart = "green" if _synth["ecart_gnf"] >= 0 else "red"
    st.markdown(kpi_card("Écart", fmt_gnf(_synth["ecart_gnf"]), icon="⚖️", color=_c_ecart), unsafe_allow_html=True)
with sc4:
    _txt_real = f"{_synth['taux_realisation_pct']:.1f} %" if _synth["taux_realisation_pct"] is not None else "—"
    st.markdown(kpi_card("Taux de réalisation", _txt_real, icon="📊", color="amber"), unsafe_allow_html=True)

# Période EXACTE comparée — jamais le capital accumulé avant le début du plan.
if _synth["date_debut_plan"] is not None:
    st.caption(
        f"Comparaison sur la période du {fmt_date_fr(_synth['date_debut_plan'])} à aujourd'hui uniquement "
        f"({_synth['statut']}). Le capital accumulé avant cette date n'est jamais compté ici."
    )

st.markdown(spacer("0.6rem"), unsafe_allow_html=True)

# ── Tableau mensuel : prévu / réalisé / écart / statut ─────────────────────────
if df_plan is None or df_plan.empty:
    st.markdown(
        empty_state("📅", "Aucun apport planifié", "Ajoutez votre premier apport prévu ci-dessous."),
        unsafe_allow_html=True,
    )
else:
    _lignes = []
    for _, _r in df_plan.iterrows():
        _mp = pd.to_datetime(_r["mois"], errors="coerce")
        if pd.isna(_mp):
            continue
        _periode = _mp.to_period("M")
        _prevu = float(pd.to_numeric(_r["montant_prevu_gnf"], errors="coerce") or 0.0)
        _reel = float(_realise.get(_periode, 0.0))
        _statut = statut_apport_mensuel(_mp.date(), _prevu, _reel, AUJOURDHUI)
        _lignes.append({
            "id": _r["id"],
            "Mois": fmt_date_fr(_mp.date()),
            "_periode": _periode,
            "Prévu (GNF)": _prevu,
            "Réalisé (GNF)": _reel,
            "Écart (GNF)": _reel - _prevu,
            "Statut": _statut,
        })
    _df_tableau = pd.DataFrame(_lignes).sort_values("_periode").drop(columns="_periode")
    st.dataframe(
        _df_tableau.drop(columns="id").style.format({
            "Prévu (GNF)": lambda v: fmt_gnf(v),
            "Réalisé (GNF)": lambda v: fmt_gnf(v),
            "Écart (GNF)": lambda v: fmt_gnf(v),
        }),
        use_container_width=True, hide_index=True,
    )

st.markdown(spacer("0.6rem"), unsafe_allow_html=True)

# ── CRUD : ajouter / modifier / supprimer un apport prévu ──────────────────────
_premier_jour_mois_prochain = (date.today().replace(day=28) + timedelta(days=4)).replace(day=1)

with st.expander("➕  Ajouter un apport prévu", expanded=False):
    with st.form("form_add_plan", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            _nouv_mois = st.date_input(
                "Mois de l'apport", value=_premier_jour_mois_prochain,
                format="DD/MM/YYYY", key="add_plan_mois",
            )
        with col2:
            _nouv_montant = st.number_input(
                "Montant prévu (GNF)", min_value=0.0, step=1_000_000.0, format="%.0f", key="add_plan_montant",
            )
        if st.form_submit_button("Ajouter", type="primary", disabled=READ_ONLY):
            if _nouv_montant <= 0:
                st.error("Le montant doit être supérieur à 0.")
            else:
                _mois_str = _nouv_mois.replace(day=1).isoformat()
                if add_plan_apport(_mois_str, _nouv_montant):
                    st.success(f"✅ Apport prévu ajouté pour {fmt_date_fr(_nouv_mois.replace(day=1))}.")
                    st.cache_data.clear()
                    st.rerun()

if df_plan is not None and not df_plan.empty:
    with st.expander("✏️  Modifier ou supprimer un apport prévu", expanded=False):
        _plan_map = {_r["id"]: _fmt_plan_label(_r) for _, _r in df_plan.iterrows()}
        _choix_plan = st.selectbox(
            "Apport prévu", list(_plan_map.keys()), format_func=lambda x: _plan_map.get(x, x), key="select_plan_edit",
        )
        if _choix_plan:
            _sel_rows = df_plan[df_plan["id"] == _choix_plan]
            if _sel_rows.empty:
                st.warning("Apport introuvable — rechargez la page.")
            else:
                _sel_plan = _sel_rows.iloc[0]
                with st.form("form_edit_plan"):
                    col1, col2 = st.columns(2)
                    with col1:
                        try:    _mois_val = pd.Timestamp(_sel_plan["mois"]).date()
                        except: _mois_val = date.today().replace(day=1)
                        _mod_mois = st.date_input("Mois", value=_mois_val, format="DD/MM/YYYY", key="edit_plan_mois")
                    with col2:
                        _mod_montant = st.number_input(
                            "Montant prévu (GNF)", min_value=0.0,
                            value=float(_sel_plan["montant_prevu_gnf"]), step=1_000_000.0, format="%.0f",
                            key="edit_plan_montant",
                        )
                    col_save, col_del = st.columns(2)
                    with col_save:
                        if st.form_submit_button("Mettre à jour", type="primary", disabled=READ_ONLY):
                            if update_plan_apport(_choix_plan, {
                                "mois": _mod_mois.replace(day=1).isoformat(),
                                "montant_prevu_gnf": _mod_montant,
                            }):
                                st.success("✅ Apport prévu mis à jour — toutes les projections sont recalculées.")
                                st.cache_data.clear()
                                st.rerun()
                    with col_del:
                        if st.form_submit_button("🗑️ Supprimer", disabled=READ_ONLY):
                            if delete_plan_apport(_choix_plan):
                                st.success("🗑️ Apport prévu supprimé.")
                                st.cache_data.clear()
                                st.rerun()

# ── 🧪 Simuler mon plan — en mémoire uniquement, jamais écrit sur le vrai plan ──
st.markdown(divider(), unsafe_allow_html=True)
st.markdown(section_header("Simuler mon plan", "🧪", "#6B5B95"), unsafe_allow_html=True)
st.caption(
    "Testez l'impact d'un changement sans toucher à votre planning réel. Rien n'est "
    "jamais enregistré ici — pour modifier votre vrai plan, utilisez les sections ci-dessus."
)

if df_plan is None or df_plan.empty:
    st.markdown(
        empty_state("🧪", "Rien à simuler", "Ajoutez d'abord des apports prévus ci-dessus."),
        unsafe_allow_html=True,
    )
else:
    _type_scenario = st.radio(
        "Type de scénario",
        ["A — Apport non réalisé", "B/C — Modifier le montant", "D — Décaler la date", "E — Apport exceptionnel"],
        horizontal=True, key="sim_type",
    )

    _df_plan_scenario = None
    if _type_scenario in ("A — Apport non réalisé", "B/C — Modifier le montant", "D — Décaler la date"):
        _sim_plan_map = {_r["id"]: _fmt_plan_label(_r) for _, _r in df_plan.iterrows()}
        _sim_choix = st.selectbox(
            "Apport à simuler", list(_sim_plan_map.keys()),
            format_func=lambda x: _sim_plan_map.get(x, x), key="sim_select",
        )
        _sim_row = df_plan[df_plan["id"] == _sim_choix].iloc[0]

        if _type_scenario == "A — Apport non réalisé":
            st.caption(f"Simule que l'apport « {_sim_plan_map[_sim_choix]} » n'a pas eu lieu (montant ramené à 0).")
            _df_plan_scenario = appliquer_scenario_plan(df_plan, "rater", plan_id=_sim_choix)
        elif _type_scenario == "B/C — Modifier le montant":
            _sim_montant = st.number_input(
                "Nouveau montant (GNF)", min_value=0.0, value=float(_sim_row["montant_prevu_gnf"]),
                step=1_000_000.0, format="%.0f", key="sim_montant",
            )
            _df_plan_scenario = appliquer_scenario_plan(df_plan, "modifier", plan_id=_sim_choix, nouveau_montant=_sim_montant)
        else:  # Décaler la date
            try:    _sim_mois_val = pd.Timestamp(_sim_row["mois"]).date()
            except: _sim_mois_val = date.today().replace(day=1)
            _sim_nouv_mois = st.date_input("Nouveau mois", value=_sim_mois_val, format="DD/MM/YYYY", key="sim_mois")
            _df_plan_scenario = appliquer_scenario_plan(
                df_plan, "decaler", plan_id=_sim_choix, nouveau_mois=_sim_nouv_mois.replace(day=1).isoformat(),
            )
    else:  # Apport exceptionnel
        col_exc1, col_exc2 = st.columns(2)
        with col_exc1:
            _sim_exc_mois = st.date_input(
                "Date de l'apport exceptionnel", value=date.today() + timedelta(days=30),
                format="DD/MM/YYYY", key="sim_exc_mois",
            )
        with col_exc2:
            _sim_exc_montant = st.number_input(
                "Montant (GNF)", min_value=0.0, step=1_000_000.0, format="%.0f", key="sim_exc_montant",
            )
        if _sim_exc_montant > 0:
            _df_plan_scenario = appliquer_scenario_plan(
                df_plan, "exceptionnel",
                nouveau_mois=_sim_exc_mois.replace(day=1).isoformat(), nouveau_montant=_sim_exc_montant,
            )

    if _df_plan_scenario is not None:
        st.markdown(spacer("0.6rem"), unsafe_allow_html=True)
        _lignes_comparaison = []
        for _p in PALIERS_CAPITAL:
            _proj_actuel_sim = calculer_projection_plan(capital, _p["montant_cible_gnf"], _p["date_cible"], df_plan, AUJOURDHUI, df_mvt)
            _proj_scenario_sim = calculer_projection_plan(capital, _p["montant_cible_gnf"], _p["date_cible"], _df_plan_scenario, AUJOURDHUI, df_mvt)
            _d_actuel = _proj_actuel_sim["date_selon_plan"]
            _d_scenario = _proj_scenario_sim["date_selon_plan"]
            if _d_actuel is not None and _d_scenario is not None:
                _impact_jours = (_d_scenario - _d_actuel).days
                if _impact_jours < 0:
                    _impact_txt = f"🟢 {abs(_impact_jours)} j plus tôt"
                elif _impact_jours == 0:
                    _impact_txt = "🟡 Aucun changement"
                else:
                    _impact_txt = f"🔴 {_impact_jours} j plus tard"
            elif _d_actuel is None and _d_scenario is not None:
                _impact_txt = "🟢 Devient atteignable"
            elif _d_actuel is not None and _d_scenario is None:
                _impact_txt = "🔴 Ne serait plus atteignable"
            else:
                _impact_txt = "🟡 Toujours non atteignable"
            _lignes_comparaison.append({
                "Palier": f"{_p['icone']} {_p['nom']}",
                "Plan actuel": fmt_date_fr(_d_actuel) if _d_actuel else "Non atteint",
                "Scénario": fmt_date_fr(_d_scenario) if _d_scenario else "Non atteint",
                "Impact": _impact_txt,
            })
        st.markdown('<div class="card" style="padding:1rem 1.25rem">', unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(_lignes_comparaison), use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)
        st.caption("⚠️ Simulation temporaire — rien n'a été enregistré dans votre plan réel.")

# ── Objectifs clôturés ──────────────────────────────────────────────────────────
if df_prog is not None and not df_prog.empty and "cloture" in df_prog.columns:
    cloturés = df_prog[df_prog["cloture"].astype(str).str.lower() == "true"]
    if not cloturés.empty:
        st.markdown(divider(), unsafe_allow_html=True)
        st.markdown(section_header("Objectifs clôturés", "🔒", "#6B6155"), unsafe_allow_html=True)
        for _, row in cloturés.iterrows():
            _pct    = row["progress_pct"]
            _reste  = row["reste_gnf"]
            _capgel = row.get("capital_gele_gnf", 0)
            _dcl    = str(row.get("date_cloture", ""))
            _color  = "#3E7C51" if bool(row["atteint"]) else "#7F7568"
            st.markdown(
                '<div class="obj-card" style="opacity:.85">'
                '<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:.4rem">'
                "<div>"
                f'<div class="obj-card-title">{row["nom_objectif"]}</div>'
                f'<div class="obj-card-desc">Échéance initiale : {row.get("date_cible", "")} · '
                f'Clôturé le {_dcl}</div>'
                "</div>"
                '<div style="text-align:right;flex-shrink:0;margin-left:1rem">'
                f'<div class="obj-pct" style="color:{_color}">{fmt_pct(_pct)}</div>'
                '<span style="font-size:.65rem;font-weight:700;padding:.15rem .5rem;border-radius:20px;'
                'background:#F5F1EA;color:#4A4238;margin-top:.25rem;display:inline-block">🔒 Clôturé</span>'
                "</div>"
                "</div>"
                + progress_bar(_pct, "amber" if not bool(row["atteint"]) else "green", "8px") +
                '<div style="display:flex;gap:2rem;margin-top:.6rem;flex-wrap:wrap">'
                "<div>"
                '<div style="font-size:.63rem;font-weight:600;color:#7F7568;margin-bottom:.1rem">Capital au moment de la clôture</div>'
                f'<div style="font-size:.85rem;font-weight:700;color:#241F19">{fmt_gnf(_capgel)}</div>'
                "</div>"
                "<div>"
                '<div style="font-size:.63rem;font-weight:600;color:#7F7568;margin-bottom:.1rem">Cible</div>'
                f'<div style="font-size:.85rem;font-weight:700;color:#241F19">{fmt_gnf(row["montant_cible_gnf"])}</div>'
                "</div>"
                "<div>"
                '<div style="font-size:.63rem;font-weight:600;color:#7F7568;margin-bottom:.1rem">Manquant à la clôture</div>'
                f'<div style="font-size:.85rem;font-weight:700;color:#B3432F">{fmt_gnf(_reste) if not bool(row["atteint"]) else "—"}</div>'
                "</div>"
                "</div>"
                "</div>",
                unsafe_allow_html=True,
            )
            st.markdown(spacer("0.25rem"), unsafe_allow_html=True)

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
            date_cib  = st.date_input("Date cible *", value=date.today() + timedelta(days=365), format="DD/MM/YYYY")
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
            _rows_obj = df_obj[df_obj["id"] == choix]
            if _rows_obj.empty:
                st.warning("Objectif introuvable — rechargez la page.")
            else:
                sel = _rows_obj.iloc[0]
                with st.form("form_edit_obj"):
                    col1, col2 = st.columns(2)
                    with col1:
                        n_nom = st.text_input("Nom", value=str(sel["nom_objectif"]))
                        n_cib = st.number_input("Montant cible (GNF)", value=float(sel["montant_cible_gnf"]),
                                                step=1_000_000.0, format="%.0f")
                    with col2:
                        try:    dc_val = pd.Timestamp(sel["date_cible"]).date()
                        except: dc_val = date.today()
                        n_date = st.date_input("Date cible", value=dc_val, format="DD/MM/YYYY")
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
