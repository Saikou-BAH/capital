"""Page Mouvements — saisie et visualisation."""

import streamlit as st
import pandas as pd
from datetime import date

from utils.config import TYPES_MOUVEMENT, DEVISES, TAUX_EUR_GNF_DEFAUT
from utils.data_loader import (
    get_mouvements, get_investisseurs, get_comptes, get_taux, add_mouvement,
)
from utils.calculs import convertir_en_gnf, get_dernier_taux
from utils.formatting import (
    inject_css, kpi_card, section_header, fmt_gnf, fmt_eur, fmt_taux,
    badge_mouvement, divider, spacer,
)
from utils.runtime import is_read_only_mode, read_only_notice

st.set_page_config(page_title="Mouvements", page_icon="💸", layout="wide")
inject_css()

st.markdown("## 💸 Mouvements")
st.markdown(divider(), unsafe_allow_html=True)

@st.cache_data(ttl=60)
def load():
    return get_mouvements(), get_investisseurs(), get_comptes(), get_taux()

df_mvt, df_inv, df_cpt, df_taux = load()
READ_ONLY = is_read_only_mode()

noms_inv = df_inv.set_index("id")["nom"].to_dict() if not df_inv.empty else {}
noms_cpt = df_cpt.set_index("id")["nom"].to_dict() if not df_cpt.empty else {}
compte_devises = df_cpt.set_index("id")["devise"].astype(str).str.upper().to_dict() if not df_cpt.empty else {}
dernier_taux = get_dernier_taux(df_taux)

# ── KPIs ──────────────────────────────────────────────────────────────────────
if not df_mvt.empty:
    df_mvt["montant_converti_gnf"] = pd.to_numeric(df_mvt["montant_converti_gnf"], errors="coerce").fillna(0)
    nb_total   = len(df_mvt)
    nb_apports = len(df_mvt[df_mvt["type_mouvement"] == "apport"])
    total_apports = df_mvt[df_mvt["type_mouvement"] == "apport"]["montant_converti_gnf"].sum()
    nb_transferts = len(df_mvt[df_mvt["type_mouvement"] == "transfert"])
    total_depenses = df_mvt[df_mvt["type_mouvement"].isin(["depense", "retrait"])]["montant_converti_gnf"].sum()
else:
    nb_total = nb_apports = nb_transferts = 0
    total_apports = total_depenses = 0.0

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(kpi_card("Total mouvements", str(nb_total), icon="📋", color="blue"), unsafe_allow_html=True)
with c2:
    st.markdown(kpi_card("Apports", str(nb_apports), sub=fmt_gnf(total_apports), icon="💰", color="green"), unsafe_allow_html=True)
with c3:
    st.markdown(kpi_card("Dépenses", fmt_gnf(total_depenses), sub=f"{nb_transferts} transfert(s) hors apports", icon="💸", color="red"), unsafe_allow_html=True)
with c4:
    st.markdown(kpi_card("Dernier taux EUR/GNF", fmt_taux(dernier_taux), icon="💱", color="amber"), unsafe_allow_html=True)

st.markdown(divider(), unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# FORMULAIRE
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(section_header("Enregistrer un mouvement", "➕", "#2563EB"), unsafe_allow_html=True)
st.markdown(spacer("0.25rem"), unsafe_allow_html=True)

TYPE_HELP = {
    "apport":     ("💰", "green",  "Nouvel argent injecté dans le projet — **augmente** le capital total."),
    "transfert":  ("↔️", "blue",   "Argent existant déplacé d'un compte à un autre — **ne change pas** le capital."),
    "depense":    ("💸", "red",    "Dépense payée depuis un compte — **diminue** le capital net disponible."),
    "retrait":    ("📤", "amber",  "Argent qui sort du projet — **diminue** le capital total."),
    "ajustement": ("🔧", "violet", "Correction d'une erreur — n'affecte pas le capital calculé."),
}

if READ_ONLY:
    read_only_notice("L'enregistrement des mouvements")

# Type selector OUTSIDE the form so it triggers reruns and drives field visibility
type_mvt = st.selectbox(
    "Type de mouvement *",
    TYPES_MOUVEMENT,
    key="type_mvt_select",
    disabled=READ_ONLY,
)
icn, clr, txt = TYPE_HELP.get(type_mvt, ("ℹ️", "blue", ""))
st.info(f"{icn} {txt}", icon=None)
st.markdown(spacer("0.25rem"), unsafe_allow_html=True)

cpt_opts = {cid: nm for cid, nm in noms_cpt.items()}

# ── Ligne 1 : date + investisseur ──────────────────────────────────────────
r1c1, r1c2 = st.columns([2, 3])
with r1c1:
    date_mvt = st.date_input("Date *", value=date.today(), format="DD/MM/YYYY", key="mvt_date", disabled=READ_ONLY)
    st.caption(f"Date enregistrée : {date_mvt.isoformat()}")
with r1c2:
    inv_id = st.selectbox(
        "Investisseur *",
        options=list(noms_inv.keys()) if noms_inv else [""],
        format_func=lambda x: noms_inv.get(x, x),
        key="mvt_inv",
        disabled=READ_ONLY,
    )

st.markdown(spacer("0.1rem"), unsafe_allow_html=True)

# ── Ligne 2 : comptes (selon type) ─────────────────────────────────────────
if type_mvt == "apport":
    dst_id = st.selectbox(
        "Compte destination *",
        options=[""] + list(cpt_opts.keys()),
        format_func=lambda x: cpt_opts.get(x, "— Aucun —") if x else "— Aucun —",
        key="mvt_dst_apport",
        disabled=READ_ONLY,
    )
    src_id = ""

elif type_mvt in ("depense", "retrait"):
    src_id = st.selectbox(
        "Compte source *",
        options=[""] + list(cpt_opts.keys()),
        format_func=lambda x: cpt_opts.get(x, "— Aucun —") if x else "— Aucun —",
        key="mvt_src_retrait",
        disabled=READ_ONLY,
    )
    dst_id = ""

elif type_mvt == "transfert":
    cs1, cs2 = st.columns(2)
    with cs1:
        src_id = st.selectbox(
            "Compte source *",
            options=[""] + list(cpt_opts.keys()),
            format_func=lambda x: cpt_opts.get(x, "— Aucun —") if x else "— Aucun —",
            key="mvt_src_transfert",
            disabled=READ_ONLY,
        )
    with cs2:
        dst_id = st.selectbox(
            "Compte destination *",
            options=[""] + list(cpt_opts.keys()),
            format_func=lambda x: cpt_opts.get(x, "— Aucun —") if x else "— Aucun —",
            key="mvt_dst_transfert",
            disabled=READ_ONLY,
        )

else:  # ajustement
    cs1, cs2 = st.columns(2)
    with cs1:
        src_id = st.selectbox(
            "Compte source (optionnel)",
            options=[""] + list(cpt_opts.keys()),
            format_func=lambda x: cpt_opts.get(x, "— Aucun —") if x else "— Aucun —",
            key="mvt_src_ajustement",
            disabled=READ_ONLY,
        )
    with cs2:
        dst_id = st.selectbox(
            "Compte destination (optionnel)",
            options=[""] + list(cpt_opts.keys()),
            format_func=lambda x: cpt_opts.get(x, "— Aucun —") if x else "— Aucun —",
            key="mvt_dst_ajustement",
            disabled=READ_ONLY,
        )

st.markdown(spacer("0.1rem"), unsafe_allow_html=True)

# ── Ligne 3 : montant + devise + taux + résultat ───────────────────────────
cm1, cm2, cm3, cm4 = st.columns([2, 1.5, 2, 2])
with cm1:
    montant = st.number_input("Montant *", min_value=0.0, step=1000.0, format="%.2f", key="mvt_montant", disabled=READ_ONLY)
with cm2:
    if type_mvt == "apport":
        devise = "EUR"
        st.markdown("<div style='font-weight:600;margin-bottom:.35rem'>Devise</div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:1rem;color:#1F2937'>EUR</div>", unsafe_allow_html=True)
    elif type_mvt == "transfert":
        devise = st.selectbox("Devise *", DEVISES, index=DEVISES.index("EUR"), key="mvt_devise_transfert", disabled=READ_ONLY)
    else:
        devise = st.selectbox("Devise *", DEVISES, key="mvt_devise", disabled=READ_ONLY)
with cm3:
    if devise == "EUR" or type_mvt == "transfert":
        taux = st.number_input(
            "Taux EUR → GNF *", min_value=0.0,
            value=float(dernier_taux) if dernier_taux > 0 else 0.0,
            step=50.0,
            help=(
                "Saisissez manuellement le taux utilisé pour cette opération. "
                "Pour un apport en EUR, c'est un taux de valorisation (reporting). "
                "Pour un transfert EUR→GNF, c'est le taux réel appliqué. "
                "Pour un transfert interne GNF, ce champ est ignoré."
            ),
            key="mvt_taux",
            disabled=READ_ONLY,
        )
    else:
        taux = 1.0
        st.markdown(spacer("0.5rem"), unsafe_allow_html=True)
        st.caption("GNF — pas de conversion")
with cm4:
    montant_gnf = convertir_en_gnf(montant, devise, taux)
    st.markdown(
        kpi_card("Montant converti GNF", fmt_gnf(montant_gnf), color="green"),
        unsafe_allow_html=True,
    )

commentaire = st.text_area("Commentaire", placeholder="Description du mouvement…", height=70, key="mvt_commentaire", disabled=READ_ONLY)
compte_dans_capital = type_mvt in ("apport", "depense", "retrait")

submitted = st.button("💾  Enregistrer le mouvement", type="primary", key="mvt_submit", disabled=READ_ONLY)
if submitted:
    errors = []
    if montant <= 0:
        errors.append("Le montant doit être supérieur à 0.")
    if devise == "EUR" and taux <= 0:
        errors.append("Le taux EUR → GNF est obligatoire pour un mouvement en EUR.")
    if not inv_id:
        errors.append("L'investisseur est obligatoire.")
    if type_mvt == "apport":
        if not dst_id:
            errors.append("Un apport requiert un compte de destination.")
        elif compte_devises.get(dst_id, "") != "EUR":
            errors.append("Un apport en EUR doit être enregistré vers un compte en EUR.")
    if type_mvt in ("depense", "retrait") and not src_id:
        errors.append("Une dépense requiert un compte source.")
    if type_mvt == "transfert":
        if not src_id or not dst_id:
            errors.append("Un transfert requiert un compte source ET un compte destination.")
        elif src_id == dst_id:
            errors.append("Le compte source et destination ne peuvent pas être identiques.")
        else:
            src_dev = compte_devises.get(src_id, "")
            dst_dev = compte_devises.get(dst_id, "")
            if src_dev == "EUR" and dst_dev == "GNF":
                if devise != "EUR":
                    errors.append("Le transfert EUR→GNF doit être saisi en EUR.")
            elif src_dev == dst_dev:
                if src_dev == "GNF" and devise != "GNF":
                    errors.append("Le transfert interne GNF doit être saisi en GNF.")
                if src_dev == "EUR" and devise != "EUR":
                    errors.append("Le transfert interne EUR doit être saisi en EUR.")
            else:
                errors.append(
                    "Seuls les transferts internes par devise et les transferts EUR→GNF sont pris en charge."
                )

    if errors:
        for e in errors:
            st.error(e)
    else:
        ok = add_mouvement(
            date_mvt=date_mvt.isoformat(), type_mouvement=type_mvt,
            investisseur_id=inv_id, montant_origine=montant,
            devise_origine=devise, taux_eur_gnf=taux,
            montant_converti_gnf=montant_gnf,
            compte_source_id=src_id, compte_destination_id=dst_id,
            commentaire=commentaire.strip(),
            compte_dans_capital=compte_dans_capital,
        )
        if ok:
            st.success(
                f"✅ **{type_mvt.capitalize()}** enregistré — "
                f"**{fmt_gnf(montant_gnf)}** le {date_mvt}"
            )
            st.cache_data.clear()
            st.rerun()

st.markdown(divider(), unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TABLEAU DES MOUVEMENTS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(section_header("Historique des mouvements", "📋", "#475569"), unsafe_allow_html=True)
st.markdown(spacer("0.25rem"), unsafe_allow_html=True)

# Filtres
f1, f2, f3, f4, f5 = st.columns(5)
with f1:
    f_type = st.multiselect("Type", TYPES_MOUVEMENT, key="f_mvt_type")
with f2:
    inv_choices = ["Tous"] + sorted(noms_inv.values())
    f_inv = st.selectbox("Investisseur", inv_choices, key="f_mvt_inv")
with f3:
    f_dev = st.multiselect("Devise", DEVISES, key="f_mvt_dev")
with f4:
    f_dmin = st.date_input("Du", value=None, key="f_mvt_dmin")
with f5:
    f_dmax = st.date_input("Au", value=None, key="f_mvt_dmax")

st.markdown(spacer("0.5rem"), unsafe_allow_html=True)

if not df_mvt.empty:
    df_show = df_mvt.copy()
    df_show["date"] = pd.to_datetime(df_show["date"], errors="coerce")
    df_show["investisseur"] = df_show["investisseur_id"].map(noms_inv).fillna(df_show["investisseur_id"])
    df_show["src_nom"]      = df_show["compte_source_id"].map(noms_cpt).fillna("—")
    df_show["dst_nom"]      = df_show["compte_destination_id"].map(noms_cpt).fillna("—")

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

    df_show = df_show.sort_values("date", ascending=False)

    st.markdown(
        f'<div style="font-size:.78rem;color:#94A3B8;font-weight:500;margin-bottom:.75rem">'
        f'{len(df_show)} mouvement(s)</div>',
        unsafe_allow_html=True,
    )

    # En-têtes
    h = st.columns([1.4, 1.8, 2.2, 3, 2, 2, 3])
    for col, lbl in zip(h, ["Date", "Type", "Investisseur", "Montant GNF", "Source", "Destination", "Commentaire"]):
        with col:
            st.markdown(f'<div class="th">{lbl}</div>', unsafe_allow_html=True)
    st.markdown('<hr style="border:none;border-top:1.5px solid #E2E8F0;margin:.4rem 0">', unsafe_allow_html=True)

    for _, row in df_show.iterrows():
        c1,c2,c3,c4,c5,c6,c7 = st.columns([1.4,1.8,2.2,3,2,2,3])
        with c1:
            st.markdown(f'<div class="row-date">{str(row["date"])[:10] if pd.notna(row["date"]) else "—"}</div>', unsafe_allow_html=True)
        with c2:
            st.markdown(badge_mouvement(str(row["type_mouvement"])), unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div style="font-size:.85rem;color:#334155;font-weight:500">{row.get("investisseur","—")}</div>', unsafe_allow_html=True)
        with c4:
            st.markdown(f'<div class="row-amount">{fmt_gnf(row["montant_converti_gnf"])}</div>', unsafe_allow_html=True)
            if str(row.get("devise_origine","")) == "EUR":
                st.markdown(f'<div class="row-comment">{fmt_eur(row["montant_origine"])} @ {fmt_taux(row["taux_eur_gnf"])}</div>', unsafe_allow_html=True)
        with c5:
            st.markdown(f'<div class="row-comment">{row.get("src_nom","—")}</div>', unsafe_allow_html=True)
        with c6:
            st.markdown(f'<div class="row-comment">{row.get("dst_nom","—")}</div>', unsafe_allow_html=True)
        with c7:
            st.markdown(f'<div class="row-comment">{str(row.get("commentaire",""))[:60]}</div>', unsafe_allow_html=True)
        st.markdown('<hr style="border:none;border-top:1px solid #F8FAFC;margin:.25rem 0">', unsafe_allow_html=True)
else:
    st.info("Aucun mouvement enregistré. Utilisez le formulaire ci-dessus.")
