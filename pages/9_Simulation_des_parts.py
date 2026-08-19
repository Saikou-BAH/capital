"""Page Simulation des parts — simulation uniquement, aucune écriture dans les CSV."""

import streamlit as st
import pandas as pd

from utils.data_loader import get_investisseurs, get_mouvements, get_comptes, get_taux
from utils.calculs import parts_par_investisseur, get_dernier_taux
from utils.config import (
    OBJECTIF_DECEMBRE_MONTANT,
    OBJECTIF_DECEMBRE_NOM,
    OBJECTIF_SEPTEMBRE_MONTANT,
    OBJECTIF_SEPTEMBRE_NOM,
)
from utils.formatting import (
    inject_css, page_header, section_header, kpi_card,
    divider, spacer, fmt_gnf, fmt_eur, fmt_pct,
)
from utils.charts import chart_simulation_parts_bar, chart_simulation_parts_pie
from utils.simulation_parts import calculer_parametres_parts

inject_css()

FRAIS_APPORT_PCT: float = 0.01  # 1 %


def _label_objectif(nom: str, montant: float) -> str:
    return f'{nom} — {fmt_gnf(montant).replace("\u202f", " ")}'


OBJECTIF_SEPTEMBRE_LABEL = _label_objectif(OBJECTIF_SEPTEMBRE_NOM, float(OBJECTIF_SEPTEMBRE_MONTANT))
OBJECTIF_DECEMBRE_LABEL = _label_objectif(OBJECTIF_DECEMBRE_NOM, float(OBJECTIF_DECEMBRE_MONTANT))

OBJECTIFS_SIMULATION = {
    OBJECTIF_SEPTEMBRE_LABEL: {
        "code": "septembre",
        "nom": OBJECTIF_SEPTEMBRE_NOM,
        "montant": float(OBJECTIF_SEPTEMBRE_MONTANT),
    },
    OBJECTIF_DECEMBRE_LABEL: {
        "code": "decembre",
        "nom": OBJECTIF_DECEMBRE_NOM,
        "montant": float(OBJECTIF_DECEMBRE_MONTANT),
    },
}

# ── En-tête ────────────────────────────────────────────────────────────────────
st.markdown(
    page_header(
        "Simulation des parts", "🧮",
        "Répartition simulée des parts de la ferme — aucune donnée modifiée.",
    ),
    unsafe_allow_html=True,
)

st.warning(
    "⚠️ **Cette page est une simulation.** Elle ne modifie jamais les données réelles. "
    "Les parts officielles doivent être validées juridiquement entre les associés.",
)
st.info(
    "La simulation est calculée sur l’objectif sélectionné : 250M ou 500M. "
    "Elle ne modifie pas les données réelles."
)
st.markdown(divider(), unsafe_allow_html=True)

# ── Chargement des données réelles (lecture seule) ────────────────────────────
@st.cache_data(ttl=60)
def _load():
    return get_investisseurs(), get_mouvements(), get_comptes(), get_taux()


df_inv, df_mvt, df_cpt, df_taux = _load()
df_parts = parts_par_investisseur(df_mvt, df_inv)
dernier_taux_reel = get_dernier_taux(df_taux)

# ── Helpers ────────────────────────────────────────────────────────────────────

def _contient(nom: str, mot: str) -> bool:
    return mot.lower() in str(nom).lower()


def _brut_en_gnf(montant: float, devise: str, taux: float) -> float:
    if devise == "EUR" and taux > 0:
        return montant * taux
    return montant


def _frais(brut_gnf: float) -> float:
    return brut_gnf * FRAIS_APPORT_PCT


def _net(brut_gnf: float) -> float:
    return brut_gnf * (1.0 - FRAIS_APPORT_PCT)


# ── Paramètres ─────────────────────────────────────────────────────────────────
st.markdown(section_header("Paramètres de la simulation", "⚙️", "#B65C2E"), unsafe_allow_html=True)

col_p1, col_p2, col_p3 = st.columns([1.4, 2.2, 2.2])

with col_p1:
    objectif_choisi = st.selectbox(
        "Objectif de simulation",
        options=list(OBJECTIFS_SIMULATION.keys()),
        index=list(OBJECTIFS_SIMULATION.keys()).index(OBJECTIF_DECEMBRE_LABEL),
    )
    objectif_selection = OBJECTIFS_SIMULATION[objectif_choisi]
    objectif_cash_gnf = float(objectif_selection["montant"])
    objectif_nom = str(objectif_selection["nom"])
    objectif_label = str(objectif_choisi)
    st.markdown(
        '<div style="background:#FBF0E7;border:1px solid #F0D9C4;border-radius:8px;padding:.7rem 1rem">'
        '<div style="font-size:.63rem;font-weight:650;text-transform:none;letter-spacing:0;'
        'color:#B65C2E;margin-bottom:.25rem">Objectif cash sélectionné</div>'
        f'<div style="font-size:1rem;font-weight:900;color:#241F19">{fmt_gnf(objectif_cash_gnf)}</div>'
        f'<div style="font-size:.7rem;color:#6B6155;margin-top:.15rem">{objectif_nom}</div>'
        '</div>',
        unsafe_allow_html=True,
    )

with col_p2:
    pct_reserve_total = st.slider(
        "% réservé total par BAH Sounoune (fondateur)",
        min_value=0, max_value=49, value=15, step=1,
        help="Part réservée pour l'idée, la conception et le pilotage du projet. "
             "Les % restants se répartissent au prorata des apports cash.",
    )
    if pct_reserve_total > 0:
        pct_donne_alseny = st.slider(
            "% cédé à BAH Alseny (gestionnaire) depuis la réserve",
            min_value=0, max_value=pct_reserve_total, value=0, step=1,
            help="Part que BAH Sounoune cède au gestionnaire. Peut être 0.",
        )
    else:
        pct_donne_alseny = 0
        st.caption("Aucune réserve définie — rien à céder à BAH Alseny.")

with col_p3:
    taux_defaut = float(dernier_taux_reel) if dernier_taux_reel and dernier_taux_reel > 0 else 10500.0
    taux_sim = st.number_input(
        "Taux EUR / GNF utilisé pour les conversions",
        min_value=1.0, value=taux_defaut, step=100.0, format="%.0f",
    )
    if dernier_taux_reel and dernier_taux_reel > 0:
        st.caption(f"Taux réel le plus récent : {fmt_gnf(dernier_taux_reel)}/€")
    else:
        st.caption("Aucun taux réel disponible — valeur saisie manuellement.")

# ── Calcul dérivé des parts ────────────────────────────────────────────────────
parametres_parts = calculer_parametres_parts(
    objectif_cash_gnf=objectif_cash_gnf,
    part_reservee_totale_pct=pct_reserve_total,
    part_donnee_bah_alseny_pct=pct_donne_alseny,
)
part_cash_pct = parametres_parts.part_cash_pct
pct_fondateur_garde = parametres_parts.part_fondateur_gardee_pct
valorisation_totale = parametres_parts.valorisation_totale_implicite
valeur_1_pct = parametres_parts.valeur_1_pourcent_gnf

st.markdown(
    '<div style="background:#EEF5EF;border:1px solid #BFD9C4;border-radius:8px;'
    'padding:.6rem 1rem;margin:.5rem 0;display:flex;gap:2rem;flex-wrap:wrap;font-size:.83rem;color:#241F19">'
    f'<span>🎯 Objectif <strong>{objectif_label}</strong></span>'
    f'<span>🏆 Fondateur garde <strong>{fmt_pct(pct_fondateur_garde, 0)}</strong>'
    f' — <strong style="color:#6B5B95">{fmt_gnf(pct_fondateur_garde / 100 * valorisation_totale)}</strong></span>'
    f'<span>🤝 BAH Alseny reçoit <strong>{fmt_pct(pct_donne_alseny, 0)}</strong>'
    f' — <strong style="color:#6B5B95">{fmt_gnf(pct_donne_alseny / 100 * valorisation_totale)}</strong></span>'
    f'<span>💰 Part cash disponible <strong>{fmt_pct(part_cash_pct, 0)}</strong></span>'
    f'<span>🏭 Valorisation implicite <strong>{fmt_gnf(valorisation_totale)}</strong></span>'
    f'<span>📐 Valeur de 1 % <strong>{fmt_gnf(valeur_1_pct)}</strong></span>'
    '</div>',
    unsafe_allow_html=True,
)
st.markdown(divider(), unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION : investisseurs existants + apports supplémentaires simulés
# ══════════════════════════════════════════════════════════════════════════════

st.markdown(
    section_header("Investisseurs actuels — apports supplémentaires simulés", "👥", "#6B5B95"),
    unsafe_allow_html=True,
)
st.caption(
    "Les apports réels sont récupérés automatiquement depuis les données. "
    "Les 1 % de frais s'appliquent uniquement sur les nouveaux apports simulés."
)

# Construire la liste des investisseurs réels
inv_list: list[dict] = []
alseny_present = False

if not df_parts.empty:
    for _, r in df_parts.iterrows():
        nom = str(r["nom"])
        est_als = _contient(nom, "Alseny")
        inv_list.append({
            "id":       str(r["investisseur_id"]),
            "nom":      nom,
            "reel_net": float(r["net_gnf"]),
            "est_soun": _contient(nom, "Sounoune"),
            "est_als":  est_als,
        })
        if est_als:
            alseny_present = True

# Ajouter BAH Alseny automatiquement s'il n'existe pas encore
if not alseny_present:
    inv_list.append({
        "id":       "__bah_alseny__",
        "nom":      "BAH Alseny",
        "reel_net": 0.0,
        "est_soun": False,
        "est_als":  True,
    })

# Saisie des apports supplémentaires pour chaque investisseur existant
saisies_existants: list[dict] = []

for idx, inv in enumerate(inv_list):
    badge = (
        "🏆 Fondateur" if inv["est_soun"]
        else ("🤝 Gestionnaire" if inv["est_als"] else "💼 Investisseur")
    )
    with st.expander(
        f"{badge} — {inv['nom']}  ·  Apport réel net : {fmt_gnf(inv['reel_net'])}",
        expanded=True,
    ):
        col_a, col_b, col_c, col_d = st.columns([2.5, 1.2, 1.5, 3])
        with col_a:
            apport_brut = st.number_input(
                "Apport supplémentaire brut",
                min_value=0.0, value=0.0, step=100_000.0, format="%.0f",
                key=f"ex_brut_{idx}",
            )
        with col_b:
            devise = st.selectbox("Devise", ["GNF", "EUR"], key=f"ex_devise_{idx}")
        with col_c:
            if devise == "EUR":
                taux_inv = st.number_input(
                    "Taux €/GNF", min_value=1.0, value=taux_sim,
                    step=100.0, format="%.0f", key=f"ex_taux_{idx}",
                )
            else:
                taux_inv = 0.0
                st.caption("— (GNF natif)")
        with col_d:
            note_inv = st.text_input("Note (optionnelle)", key=f"ex_note_{idx}")

        brut_gnf = _brut_en_gnf(apport_brut, devise, taux_inv)
        frais_gnf = _frais(brut_gnf)
        net_sim_gnf = _net(brut_gnf)

        if brut_gnf > 0:
            st.markdown(
                '<div style="background:#EEF5EF;border:1px solid #BFD9C4;border-radius:6px;'
                'padding:.4rem .85rem;font-size:.8rem;margin-top:.2rem">'
                f'Brut GNF : <strong>{fmt_gnf(brut_gnf)}</strong> — '
                f'Frais 1 % : <strong style="color:#B3432F">−{fmt_gnf(frais_gnf)}</strong> — '
                f'Net simulé : <strong style="color:#3E7C51">{fmt_gnf(net_sim_gnf)}</strong>'
                '</div>',
                unsafe_allow_html=True,
            )

        saisies_existants.append({
            "id":          inv["id"],
            "nom":         inv["nom"],
            "reel_net":    inv["reel_net"],
            "est_soun":    inv["est_soun"],
            "est_als":     inv["est_als"],
            "brut_gnf":    brut_gnf,
            "frais_gnf":   frais_gnf,
            "net_sim_gnf": net_sim_gnf,
            "note":        note_inv,
        })

st.markdown(divider(), unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION : nouveaux investisseurs simulés
# ══════════════════════════════════════════════════════════════════════════════

st.markdown(
    section_header("Nouveaux associés / investisseurs simulés", "➕", "#3E7C51"),
    unsafe_allow_html=True,
)

n_new = int(st.number_input(
    "Nombre de nouvelles personnes à simuler (max 10)",
    min_value=0, max_value=10, value=0, step=1,
))

ROLES_NOUVEAU = ["Nouvel associé", "Investisseur cash", "Autre"]
saisies_nouveaux: list[dict] = []

for i in range(n_new):
    st.markdown(
        f'<div style="font-weight:700;font-size:.84rem;color:#241F19;margin:.55rem 0 .1rem 0">'
        f'Personne {i + 1}</div>',
        unsafe_allow_html=True,
    )
    c1, c2, c3, c4, c5, c6 = st.columns([2.2, 1.5, 2, 1.2, 1.5, 2.5])
    with c1:
        n_nom = st.text_input("Nom", placeholder="Prénom NOM", key=f"nv_nom_{i}")
    with c2:
        n_role = st.selectbox("Rôle", ROLES_NOUVEAU, key=f"nv_role_{i}")
    with c3:
        n_brut = st.number_input(
            "Apport brut", min_value=0.0, value=0.0,
            step=100_000.0, format="%.0f", key=f"nv_brut_{i}",
        )
    with c4:
        n_devise = st.selectbox("Devise", ["GNF", "EUR"], key=f"nv_devise_{i}")
    with c5:
        if n_devise == "EUR":
            n_taux = st.number_input(
                "Taux €/GNF", min_value=1.0, value=taux_sim,
                step=100.0, format="%.0f", key=f"nv_taux_{i}",
            )
        else:
            n_taux = 0.0
            st.caption("— (GNF)")
    with c6:
        n_note = st.text_input("Note", key=f"nv_note_{i}")

    n_brut_gnf = _brut_en_gnf(n_brut, n_devise, n_taux)
    n_frais_gnf = _frais(n_brut_gnf)
    n_net_gnf = _net(n_brut_gnf)

    if n_brut_gnf > 0:
        st.markdown(
            '<div style="background:#EEF5EF;border:1px solid #BFD9C4;border-radius:6px;'
            'padding:.35rem .8rem;font-size:.78rem;margin-bottom:.35rem">'
            f'Brut GNF : <strong>{fmt_gnf(n_brut_gnf)}</strong> — '
            f'Frais 1 % : <strong style="color:#B3432F">−{fmt_gnf(n_frais_gnf)}</strong> — '
            f'Net : <strong style="color:#3E7C51">{fmt_gnf(n_net_gnf)}</strong>'
            '</div>',
            unsafe_allow_html=True,
        )

    saisies_nouveaux.append({
        "nom":      n_nom.strip() if n_nom.strip() else f"Personne {i + 1}",
        "role":     n_role,
        "brut_gnf": n_brut_gnf,
        "frais_gnf": n_frais_gnf,
        "net_gnf":  n_net_gnf,
        "note":     n_note,
    })

st.markdown(divider(), unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# CALCULS FINAUX
# ══════════════════════════════════════════════════════════════════════════════

cash_reel_total  = sum(s["reel_net"] for s in saisies_existants)
cash_sim_nets    = (
    sum(s["net_sim_gnf"] for s in saisies_existants)
    + sum(n["net_gnf"] for n in saisies_nouveaux)
)
total_frais_sim  = (
    sum(s["frais_gnf"] for s in saisies_existants)
    + sum(n["frais_gnf"] for n in saisies_nouveaux)
)
cash_total_apres = cash_reel_total + cash_sim_nets
cash_restant     = max(0.0, objectif_cash_gnf - cash_total_apres)
part_restante_pct = (cash_restant / valorisation_totale * 100.0) if cash_restant > 0 else 0.0
surplus           = max(0.0, cash_total_apres - objectif_cash_gnf)

# Construire les lignes du tableau de simulation
lignes: list[dict] = []

for s in saisies_existants:
    total_net  = s["reel_net"] + s["net_sim_gnf"]
    part_cash  = (total_net / valorisation_totale * 100.0) if valorisation_totale > 0 else 0.0
    part_bonus = pct_fondateur_garde if s["est_soun"] else (pct_donne_alseny if s["est_als"] else 0.0)
    part_fin   = part_cash + part_bonus
    valeur_gnf = part_fin / 100.0 * valorisation_totale
    valeur_eur = (valeur_gnf / taux_sim) if taux_sim > 0 else 0.0
    role       = "🏆 Fondateur" if s["est_soun"] else ("🤝 Gestionnaire" if s["est_als"] else "💼 Investisseur")

    lignes.append({
        "Personne":             s["nom"],
        "Rôle":                 role,
        "Apport réel net GNF":  s["reel_net"],
        "Apport sim. brut GNF": s["brut_gnf"],
        "Frais 1 %":            s["frais_gnf"],
        "Apport sim. net GNF":  s["net_sim_gnf"],
        "Apport total net GNF": total_net,
        "% cash":               part_cash,
        "% réservé / bonus":    part_bonus,
        "% final":              part_fin,
        "Valeur implicite GNF": valeur_gnf,
        "Équivalent EUR":       valeur_eur,
        "Notes":                s["note"],
    })

for n in saisies_nouveaux:
    part_cash  = (n["net_gnf"] / valorisation_totale * 100.0) if valorisation_totale > 0 else 0.0
    valeur_gnf = part_cash / 100.0 * valorisation_totale
    valeur_eur = (valeur_gnf / taux_sim) if taux_sim > 0 else 0.0

    lignes.append({
        "Personne":             n["nom"],
        "Rôle":                 n["role"],
        "Apport réel net GNF":  0.0,
        "Apport sim. brut GNF": n["brut_gnf"],
        "Frais 1 %":            n["frais_gnf"],
        "Apport sim. net GNF":  n["net_gnf"],
        "Apport total net GNF": n["net_gnf"],
        "% cash":               part_cash,
        "% réservé / bonus":    0.0,
        "% final":              part_cash,
        "Valeur implicite GNF": valeur_gnf,
        "Équivalent EUR":       valeur_eur,
        "Notes":                n["note"],
    })

if cash_restant > 0:
    lignes.append({
        "Personne":             "Cash restant à apporter",
        "Rôle":                 "À trouver",
        "Apport réel net GNF":  0.0,
        "Apport sim. brut GNF": 0.0,
        "Frais 1 %":            0.0,
        "Apport sim. net GNF":  0.0,
        "Apport total net GNF": cash_restant,
        "% cash":               part_restante_pct,
        "% réservé / bonus":    0.0,
        "% final":              part_restante_pct,
        "Valeur implicite GNF": cash_restant,
        "Équivalent EUR":       (cash_restant / taux_sim) if taux_sim > 0 else 0.0,
        "Notes":                f"Nécessaire pour atteindre {fmt_gnf(objectif_cash_gnf)}",
    })

df_sim = pd.DataFrame(lignes)

# ── KPIs ──────────────────────────────────────────────────────────────────────
st.markdown(section_header("Indicateurs clés", "📊", "#241F19"), unsafe_allow_html=True)

k0, k1, k2, k3 = st.columns(4)
with k0:
    st.markdown(kpi_card("Objectif sélectionné", objectif_nom, icon="🎯", color="blue"), unsafe_allow_html=True)
with k1:
    st.markdown(kpi_card("Objectif cash", fmt_gnf(objectif_cash_gnf), icon="💼", color="navy"), unsafe_allow_html=True)
with k2:
    st.markdown(kpi_card("Cash réel actuel", fmt_gnf(cash_reel_total), icon="💰", color="green"), unsafe_allow_html=True)
with k3:
    st.markdown(kpi_card("Cash simulé ajouté", fmt_gnf(cash_sim_nets), icon="➕", color="amber"), unsafe_allow_html=True)

k4, k5, k6 = st.columns(3)
with k4:
    st.markdown(kpi_card("Cash total après simulation", fmt_gnf(cash_total_apres), icon="💼", color="violet"), unsafe_allow_html=True)
with k5:
    if cash_restant > 0:
        st.markdown(kpi_card("Cash restant à apporter", fmt_gnf(cash_restant), icon="⚠️", color="red"), unsafe_allow_html=True)
    else:
        surplus_txt = f"Surplus : +{fmt_gnf(surplus)}" if surplus > 0 else "Objectif atteint ✅"
        st.markdown(kpi_card("Cash restant à apporter", surplus_txt, icon="✅", color="green"), unsafe_allow_html=True)
with k6:
    st.markdown(kpi_card("Total frais simulés (1 %)", fmt_gnf(total_frais_sim), icon="🏧", color="slate"), unsafe_allow_html=True)

k7, k8, k9 = st.columns(3)
with k7:
    st.markdown(kpi_card("Valorisation totale implicite", fmt_gnf(valorisation_totale), icon="🏭", color="navy"), unsafe_allow_html=True)
with k8:
    st.markdown(kpi_card("Valeur de 1 %", fmt_gnf(valeur_1_pct), icon="📐", color="teal"), unsafe_allow_html=True)
with k9:
    _prt = fmt_pct(part_restante_pct) if cash_restant > 0 else "—"
    _ico = "📉" if cash_restant > 0 else "🎉"
    _col = "amber" if cash_restant > 0 else "green"
    st.markdown(kpi_card("Part cash restante", _prt, icon=_ico, color=_col), unsafe_allow_html=True)

st.markdown(divider(), unsafe_allow_html=True)

# ── Tableau principal ──────────────────────────────────────────────────────────
st.markdown(section_header("Répartition simulée", "📋", "#B65C2E"), unsafe_allow_html=True)

if not df_sim.empty:
    _LBL = (
        "font-size:.63rem;font-weight:650;text-transform:none;"
        "letter-spacing:0;color:#7F7568"
    )
    _RATIOS = [2, 1.5, 2, 2, 1.4, 2, 2, 1.2, 1.4, 1.5, 2.2, 1.8, 2.5]
    _HEADERS = [
        "Personne", "Rôle", "Apport réel net", "Apport sim. brut",
        "Frais 1 %", "Apport sim. net", "Total net",
        "% cash", "% bonus", "% final",
        "Valeur GNF", "Équiv. EUR", "Notes",
    ]

    st.markdown('<div class="table-scroll"><div style="min-width:1020px">', unsafe_allow_html=True)

    hdr_cols = st.columns(_RATIOS)
    for col, h in zip(hdr_cols, _HEADERS):
        with col:
            st.markdown(f'<div style="{_LBL}">{h}</div>', unsafe_allow_html=True)
    st.markdown(
        '<hr style="border:none;border-top:1.5px solid #E8E1D6;margin:.25rem 0">',
        unsafe_allow_html=True,
    )

    for _, row in df_sim.iterrows():
        is_restant = row["Personne"] == "Cash restant à apporter"
        pct_f = float(row["% final"])
        pct_col = "#3E7C51" if pct_f >= 20 else ("#B65C2E" if pct_f >= 5 else "#99651A")

        r_cols = st.columns(_RATIOS)
        _vals = [
            f'<div style="font-size:.82rem;font-weight:700;color:#241F19">{row["Personne"]}</div>',
            f'<div style="font-size:.74rem;color:#6B6155">{row["Rôle"]}</div>',
            (f'<div style="font-size:.78rem;font-weight:600;color:#241F19">{fmt_gnf(row["Apport réel net GNF"])}</div>'
             if row["Apport réel net GNF"] > 0
             else '<div style="font-size:.78rem;color:#E8E1D6">—</div>'),
            (f'<div style="font-size:.78rem;color:#241F19">{fmt_gnf(row["Apport sim. brut GNF"])}</div>'
             if row["Apport sim. brut GNF"] > 0
             else '<div style="font-size:.78rem;color:#E8E1D6">—</div>'),
            (f'<div style="font-size:.78rem;color:#B3432F">−{fmt_gnf(row["Frais 1 %"])}</div>'
             if row["Frais 1 %"] > 0
             else '<div style="font-size:.78rem;color:#E8E1D6">—</div>'),
            (f'<div style="font-size:.78rem;font-weight:600;color:#3E7C51">{fmt_gnf(row["Apport sim. net GNF"])}</div>'
             if row["Apport sim. net GNF"] > 0
             else '<div style="font-size:.78rem;color:#E8E1D6">—</div>'),
            f'<div style="font-size:.84rem;font-weight:800;color:#241F19">{fmt_gnf(row["Apport total net GNF"])}</div>',
            f'<div style="font-size:.82rem;font-weight:700;color:#B65C2E">{fmt_pct(row["% cash"])}</div>',
            (f'<div style="font-size:.82rem;font-weight:700;color:#6B5B95">{fmt_pct(float(row["% réservé / bonus"]))}</div>'
             if float(row["% réservé / bonus"]) > 0
             else '<div style="font-size:.78rem;color:#E8E1D6">—</div>'),
            f'<div style="font-size:.92rem;font-weight:900;color:{pct_col}">{fmt_pct(row["% final"])}</div>',
            f'<div style="font-size:.78rem;font-weight:700;color:#241F19">{fmt_gnf(row["Valeur implicite GNF"])}</div>',
            (f'<div style="font-size:.78rem;color:#6B6155">{fmt_eur(row["Équivalent EUR"])}</div>'
             if taux_sim > 0
             else '<div style="font-size:.78rem;color:#E8E1D6">—</div>'),
            f'<div style="font-size:.72rem;color:#7F7568">{str(row["Notes"])[:50]}</div>',
        ]
        for col, v in zip(r_cols, _vals):
            with col:
                st.markdown(v, unsafe_allow_html=True)
        st.markdown(
            '<hr style="border:none;border-top:1px solid #F5F1EA;margin:.15rem 0">',
            unsafe_allow_html=True,
        )

    st.markdown('</div></div>', unsafe_allow_html=True)

    # Message si objectif cash atteint / dépassé
    if cash_restant <= 0:
        if surplus > 0:
            st.success(
                f"🎉 L'objectif cash de {fmt_gnf(objectif_cash_gnf)} est atteint et dépassé "
                f"de {fmt_gnf(surplus)}."
            )
        else:
            st.success(f"🎉 L'objectif cash de {fmt_gnf(objectif_cash_gnf)} est exactement atteint !")
    else:
        st.info(
            f"Il reste **{fmt_gnf(cash_restant)}** à apporter "
            f"({fmt_pct(part_restante_pct)} de la ferme) pour atteindre l'objectif."
        )

st.markdown(divider(), unsafe_allow_html=True)

# ── Bloc de contrôle ───────────────────────────────────────────────────────────
st.markdown(section_header("Contrôle des totaux", "✅", "#3E7C51"), unsafe_allow_html=True)

df_att = df_sim[df_sim["Personne"] != "Cash restant à apporter"].copy() if not df_sim.empty else pd.DataFrame()
total_pct_cash_att  = float(df_att["% cash"].sum())  if not df_att.empty else 0.0
total_pct_bonus_att = float(df_att["% réservé / bonus"].sum()) if not df_att.empty else 0.0
total_pct_final_att = float(df_att["% final"].sum())  if not df_att.empty else 0.0
total_pct_tout      = float(df_sim["% final"].sum())   if not df_sim.empty else 0.0
ecart_100           = 100.0 - total_pct_tout

ct1, ct2, ct3, ct4 = st.columns(4)
with ct1:
    st.markdown(kpi_card("Total % cash attribué", fmt_pct(total_pct_cash_att), icon="💰", color="blue"), unsafe_allow_html=True)
with ct2:
    st.markdown(kpi_card("Total % bonus/fondateur", fmt_pct(total_pct_bonus_att), icon="🏆", color="violet"), unsafe_allow_html=True)
with ct3:
    st.markdown(kpi_card("Total % attribué (sans restant)", fmt_pct(total_pct_final_att), icon="✅", color="green"), unsafe_allow_html=True)
with ct4:
    _ecart_col = "green" if abs(ecart_100) < 0.5 else ("amber" if abs(ecart_100) < 5 else "red")
    st.markdown(kpi_card("Écart avec 100 %", fmt_pct(abs(ecart_100)), icon="🎯", color=_ecart_col), unsafe_allow_html=True)

if abs(ecart_100) < 0.5:
    st.success("✅ La répartition est équilibrée — le total est proche de 100 %.")
elif cash_restant > 0:
    st.warning(
        f"Il reste **{fmt_pct(part_restante_pct)}** à attribuer "
        f"({fmt_gnf(cash_restant)} de cash encore à trouver)."
    )
else:
    st.info(f"Écart résiduel de {fmt_pct(abs(ecart_100))} — vérifiez les paramètres.")

st.markdown(divider(), unsafe_allow_html=True)

# ── Graphiques ─────────────────────────────────────────────────────────────────
st.markdown(section_header("Visualisation", "📈", "#B65C2E"), unsafe_allow_html=True)

if not df_sim.empty and df_sim["% final"].sum() > 0:
    g1, g2 = st.columns(2)

    with g1:
        st.markdown('<div class="card" style="padding:.75rem 1rem .5rem">', unsafe_allow_html=True)
        st.plotly_chart(chart_simulation_parts_bar(df_sim), use_container_width=True, config={"displayModeBar": False}, key="sim_bar_parts")
        st.markdown('</div>', unsafe_allow_html=True)

    with g2:
        st.markdown('<div class="card" style="padding:.75rem 1rem .5rem">', unsafe_allow_html=True)
        st.plotly_chart(chart_simulation_parts_pie(df_sim), use_container_width=True, config={"displayModeBar": False}, key="sim_pie_parts")
        st.markdown('</div>', unsafe_allow_html=True)
else:
    st.info("Aucune donnée suffisante pour les graphiques.")

st.markdown(spacer("0.5rem"), unsafe_allow_html=True)

# ── Rappel obligatoire ─────────────────────────────────────────────────────────
st.markdown(
    '<div style="background:#FEF9C3;border:1px solid #FDE047;border-radius:8px;'
    'padding:.75rem 1.2rem;font-size:.83rem;color:#713F12;margin-top:.5rem;text-align:center">'
    '⚠️ <strong>Cette page est une simulation.</strong> Elle ne modifie jamais les données réelles. '
    'Les parts officielles doivent être validées juridiquement entre les associés.'
    '</div>',
    unsafe_allow_html=True,
)
