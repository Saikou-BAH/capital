"""Page Mouvements — saisie et visualisation."""

import streamlit as st
import pandas as pd
from datetime import date

from utils.config import TYPES_MOUVEMENT, DEVISES, TAUX_EUR_GNF_DEFAUT, FRAIS_RETRAIT_BAREME, ORANGE_MONEY_MAX_RETRAIT_GNF
from utils.data_loader import (
    get_mouvements, get_investisseurs, get_comptes, get_taux, add_mouvement, delete_mouvement,
)
from utils.calculs import convertir_en_gnf, get_dernier_taux, get_apports_disponibles, calcul_valeur_apport, get_transferts_gnf_sur_compte, get_frais_retrait_cash
from utils.formatting import (
    inject_css, kpi_card, page_header, section_header, preview_card,
    fmt_gnf, fmt_eur, fmt_taux, badge_mouvement, divider, spacer,
    empty_state, confirm_delete, form_step,
)
from utils.charts import chart_frais_retrait_par_mois
from utils.runtime import is_read_only_mode, read_only_notice

inject_css()
st.markdown(page_header("Mouvements", "💸", "Enregistrez vos apports, transferts et retraits."), unsafe_allow_html=True)

@st.cache_data(ttl=60)
def load():
    return get_mouvements(), get_investisseurs(), get_comptes(), get_taux()

df_mvt, df_inv, df_cpt, df_taux = load()
READ_ONLY = is_read_only_mode()

noms_inv = df_inv.set_index("id")["nom"].to_dict() if not df_inv.empty else {}
noms_cpt = df_cpt.set_index("id")["nom"].to_dict() if not df_cpt.empty else {}
compte_devises = df_cpt.set_index("id")["devise"].astype(str).str.upper().to_dict() if not df_cpt.empty else {}
compte_frais = df_cpt.set_index("id")["frais_pct"].apply(lambda x: float(x) if x not in ("", None) else 0.0).to_dict() if not df_cpt.empty else {}
dernier_taux = get_dernier_taux(df_taux)

# ── KPIs ──────────────────────────────────────────────────────────────────────
if not df_mvt.empty:
    df_mvt["montant_converti_gnf"] = pd.to_numeric(df_mvt["montant_converti_gnf"], errors="coerce").fillna(0)
    nb_total   = len(df_mvt)
    nb_apports = len(df_mvt[df_mvt["type_mouvement"] == "apport"])
    total_apports = df_mvt[df_mvt["type_mouvement"] == "apport"]["montant_converti_gnf"].sum()
    nb_transferts = len(df_mvt[df_mvt["type_mouvement"] == "transfert"])
    total_depenses = df_mvt[df_mvt["type_mouvement"].isin(["depense", "retrait"])]["montant_converti_gnf"].sum()
    nb_depenses = len(df_mvt[df_mvt["type_mouvement"].isin(["depense", "retrait"])])
    total_frais = df_mvt[df_mvt["type_mouvement"] == "frais_retrait"]["montant_converti_gnf"].sum()
    nb_frais = len(df_mvt[df_mvt["type_mouvement"] == "frais_retrait"])
else:
    nb_total = nb_apports = nb_transferts = nb_depenses = nb_frais = 0
    total_apports = total_depenses = total_frais = 0.0

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.markdown(kpi_card("Total mouvements", str(nb_total), icon="📋", color="blue"), unsafe_allow_html=True)
with c2:
    st.markdown(kpi_card("Apports", str(nb_apports), sub=fmt_gnf(total_apports), icon="💰", color="green"), unsafe_allow_html=True)
with c3:
    st.markdown(kpi_card("Dépenses & Retraits", fmt_gnf(total_depenses), sub=f"{nb_depenses} opération(s)", icon="💸", color="red"), unsafe_allow_html=True)
with c4:
    st.markdown(kpi_card("Frais de retrait", fmt_gnf(total_frais), sub=f"{nb_frais} opération(s)", icon="🏧", color="violet"), unsafe_allow_html=True)
with c5:
    st.markdown(kpi_card("Dernier taux EUR/GNF", fmt_taux(dernier_taux), icon="💱", color="amber"), unsafe_allow_html=True)

st.markdown(divider(), unsafe_allow_html=True)

# ── Graphique frais de retrait ────────────────────────────────────────────────
if not df_mvt.empty and nb_frais > 0:
    st.markdown(section_header("Frais de retrait", "🏧", "#6B5B95"), unsafe_allow_html=True)
    st.markdown('<div class="card" style="padding:.75rem 1rem .5rem 1rem">', unsafe_allow_html=True)
    st.plotly_chart(chart_frais_retrait_par_mois(df_mvt), use_container_width=True, config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown(divider(), unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# FORMULAIRE
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(section_header("Enregistrer un mouvement", "➕", "#B65C2E"), unsafe_allow_html=True)
st.markdown(spacer("0.25rem"), unsafe_allow_html=True)

TYPE_HELP = {
    "apport":    ("💰", "green",  "Nouvel argent injecté dans le projet — **augmente** le capital total."),
    "transfert": ("↔️", "blue",   "Argent existant déplacé d'un compte à un autre — **ne change pas** le capital."),
    "retrait":   ("📤", "amber",  "Argent qui sort du projet — **diminue** le capital total."),
}

if READ_ONLY:
    read_only_notice("L'enregistrement des mouvements")

st.markdown('<div class="card" style="padding:1.4rem 1.6rem">', unsafe_allow_html=True)

# ── Étape 1 : Type de mouvement ───────────────────────────────────────────────
st.markdown(form_step(1, "Type de mouvement", first=True), unsafe_allow_html=True)
type_mvt = st.radio(
    "Type de mouvement",
    TYPES_MOUVEMENT,
    horizontal=True,
    key="type_mvt_select",
    disabled=READ_ONLY,
    label_visibility="collapsed",
)
icn, clr, txt = TYPE_HELP.get(type_mvt, ("ℹ️", "blue", ""))
st.markdown(spacer("0.15rem"), unsafe_allow_html=True)

# Indicateur visuel du type sélectionné
_type_colors = {"apport": ("#3E7C51", "#EEF5EF", "#BFD9C4"), "transfert": ("#B65C2E", "#FBF0E7", "#F0D9C4"), "retrait": ("#99651A", "#FBF3E4", "#EAD2A0")}
_tc, _tbg, _tbr = _type_colors.get(type_mvt, ("#6B6155", "#F5F1EA", "#E8E1D6"))
st.markdown(
    f'<div style="background:{_tbg};border:1px solid {_tbr};border-radius:8px;'
    f'padding:.45rem .85rem;font-size:.83rem;color:{_tc};font-weight:500;margin-bottom:.5rem">'
    f'{icn} {txt.replace("**", "")}</div>',
    unsafe_allow_html=True,
)

# ── Étape 2 : Comptes ────────────────────────────────────────────────────────
st.markdown(form_step(2, "Comptes & investisseur"), unsafe_allow_html=True)

cpt_opts     = {cid: nm for cid, nm in noms_cpt.items()}
cpt_opts_eur = {cid: nm for cid, nm in noms_cpt.items() if compte_devises.get(cid, "") == "EUR"}
cpt_opts_gnf = {cid: nm for cid, nm in noms_cpt.items() if compte_devises.get(cid, "") == "GNF"}
gnf_disponible_src = None  # disponible sur le transfert GNF source sélectionné

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
    sel_apport_id = ""
    gnf_transfer_link_id = ""
    if not cpt_opts_eur:
        st.warning("Aucun compte en EUR disponible. Créez d'abord un compte en EUR dans la page Comptes.", icon=None)
    dst_id = st.selectbox(
        "Compte destination (EUR uniquement) *",
        options=[""] + list(cpt_opts_eur.keys()),
        format_func=lambda x: cpt_opts_eur.get(x, "— Aucun —") if x else "— Aucun —",
        key="mvt_dst_apport",
        disabled=READ_ONLY,
    )
    src_id = ""

elif type_mvt in ("depense", "retrait"):
    sel_apport_id = ""
    gnf_transfer_link_id = ""
    src_id = st.selectbox(
        "Compte source *",
        options=[""] + list(cpt_opts.keys()),
        format_func=lambda x: cpt_opts.get(x, "— Aucun —") if x else "— Aucun —",
        key="mvt_src_retrait",
        disabled=READ_ONLY,
    )
    dst_id = ""

elif type_mvt == "transfert":
    # ── Mode transfert : EUR depuis un apport OU interne GNF ─────────────────
    df_apports_dispo = get_apports_disponibles(df_mvt)
    MODE_APPORT = "💶 EUR depuis un apport"
    MODE_INTERNE = "🔄 Interne GNF (sans apport)"
    mode_transfert = st.radio(
        "Type de transfert",
        [MODE_APPORT, MODE_INTERNE],
        horizontal=True,
        key="mvt_mode_transfert",
        disabled=READ_ONLY,
    )

    if mode_transfert == MODE_APPORT:
        if df_apports_dispo.empty:
            st.warning("Aucun apport EUR avec solde disponible. Enregistrez d'abord un apport.", icon=None)
            sel_apport_id = ""
            src_id = ""
            dst_id = ""
            inv_id = list(noms_inv.keys())[0] if noms_inv else ""
        else:
            # Formatage de chaque apport pour la liste déroulante
            def _fmt_apport(aid):
                row = df_apports_dispo[df_apports_dispo["id"] == aid]
                if row.empty:
                    return aid
                r = row.iloc[0]
                inv_nm = noms_inv.get(str(r["investisseur_id"]), str(r["investisseur_id"]))
                eur_r = float(r.get("eur_restant", r["montant_origine"]))
                taux_e = float(r["taux_eur_gnf"]) if float(r["taux_eur_gnf"]) > 0 else 0
                gnf_e = eur_r * taux_e
                return f"{inv_nm} — {fmt_eur(eur_r)} restants ≈ {fmt_gnf(gnf_e)} (estimé)"

            apport_ids = list(df_apports_dispo["id"])
            sel_apport_id = st.selectbox(
                "Apport source *",
                options=apport_ids,
                format_func=_fmt_apport,
                key="mvt_apport_source",
                disabled=READ_ONLY,
            )

            apport_detail = calcul_valeur_apport(sel_apport_id, df_mvt)
            inv_id = apport_detail.get("investisseur_id", "")
            src_id = apport_detail.get("compte_destination_id", "")
            eur_max = apport_detail.get("eur_restant", 0.0)

            # Infos investisseur + compte source (lecture seule)
            nom_inv_apport = noms_inv.get(inv_id, inv_id)
            nom_src_apport = noms_cpt.get(src_id, src_id)
            st.markdown(
                f'<div style="background:#FBF0E7;border:1px solid #F0D9C4;border-radius:8px;'
                f'padding:.55rem .85rem;font-size:.84rem;color:#9C4B22;margin-top:.2rem;display:flex;gap:2rem">'
                f'<span>👤 <strong>{nom_inv_apport}</strong></span>'
                f'<span>🏦 Depuis : <strong>{nom_src_apport}</strong></span>'
                f'<span>💶 Solde : <strong>{fmt_eur(eur_max)}</strong></span>'
                f'</div>',
                unsafe_allow_html=True,
            )
            st.markdown(spacer("0.1rem"), unsafe_allow_html=True)

            dst_id = st.selectbox(
                "Compte destination *",
                options=[""] + list(cpt_opts.keys()),
                format_func=lambda x: cpt_opts.get(x, "— Aucun —") if x else "— Aucun —",
                key="mvt_dst_transfert_apport",
                disabled=READ_ONLY,
            )
        gnf_transfer_link_id = ""
    else:
        # Transfert interne GNF
        sel_apport_id = ""
        cs1, cs2 = st.columns(2)
        with cs1:
            src_id = st.selectbox(
                "Compte source *",
                options=[""] + list(cpt_opts.keys()),
                format_func=lambda x: cpt_opts.get(x, "— Aucun —") if x else "— Aucun —",
                key="mvt_src_transfert_interne",
                disabled=READ_ONLY,
            )
        with cs2:
            dst_id = st.selectbox(
                "Compte destination *",
                options=[""] + list(cpt_opts.keys()),
                format_func=lambda x: cpt_opts.get(x, "— Aucun —") if x else "— Aucun —",
                key="mvt_dst_transfert_interne",
                disabled=READ_ONLY,
            )

        # Option : lier à un transfert EUR→GNF entrant pour traçabilité apport
        df_transferts_src = get_transferts_gnf_sur_compte(src_id, df_mvt) if src_id else pd.DataFrame()
        if not df_transferts_src.empty:
            # Calcul du disponible pour chaque transfert AVANT d'afficher la liste
            def _dispo_pour_transfert(row_t):
                apport_id = str(row_t["apport_source_id"])
                gnf_recu  = float(row_t["montant_converti_gnf"])
                deja = pd.to_numeric(
                    df_mvt[
                        (df_mvt["type_mouvement"] == "transfert") &
                        (df_mvt["compte_source_id"].astype(str) == str(src_id)) &
                        (df_mvt["apport_source_id"].astype(str) == apport_id) &
                        (df_mvt["devise_origine"].astype(str).str.upper() == "GNF")
                    ]["montant_origine"],
                    errors="coerce",
                ).sum()
                return max(0.0, gnf_recu - deja)

            # Ne garder que les transferts avec encore du GNF disponible
            _dispos = {row_t["id"]: _dispo_pour_transfert(row_t) for _, row_t in df_transferts_src.iterrows()}
            df_transferts_dispo = df_transferts_src[df_transferts_src["id"].map(_dispos) > 0]

            if df_transferts_dispo.empty:
                st.info("Aucun transfert entrant avec du GNF disponible sur ce compte.", icon=None)
                sel_transfert_gnf_id = ""
                gnf_transfer_link_id = ""
                inv_id = st.selectbox(
                    "Investisseur *",
                    options=list(noms_inv.keys()) if noms_inv else [""],
                    format_func=lambda x: noms_inv.get(x, x),
                    key="mvt_inv_interne",
                    disabled=READ_ONLY,
                )
            else:
                def _fmt_transfert_gnf(tid):
                    if not tid:
                        return "— Sans liaison —"
                    row = df_transferts_dispo[df_transferts_dispo["id"] == tid]
                    if row.empty:
                        return str(tid)
                    r = row.iloc[0]
                    inv_nm = noms_inv.get(str(r["investisseur_id"]), str(r["investisseur_id"]))
                    dispo  = _dispos.get(tid, 0.0)
                    dt = str(r.get("date", ""))[:10]
                    return f"{inv_nm} — {fmt_gnf(dispo)} disponibles (reçu le {dt})"

                sel_transfert_gnf_id = st.selectbox(
                    "Lier à un transfert entrant (optionnel)",
                    options=[""] + list(df_transferts_dispo["id"]),
                    format_func=_fmt_transfert_gnf,
                    key="mvt_lier_transfert_gnf",
                    disabled=READ_ONLY,
                )

                if sel_transfert_gnf_id:
                    row_t = df_transferts_dispo[df_transferts_dispo["id"] == sel_transfert_gnf_id].iloc[0]
                    gnf_transfer_link_id = str(row_t["apport_source_id"])
                    inv_id = str(row_t["investisseur_id"])
                    nom_inv_t = noms_inv.get(inv_id, inv_id)
                    gnf_recu = float(row_t["montant_converti_gnf"])
                    dt_t = str(row_t.get("date", ""))[:10]
                    gnf_disponible_src = _dispos.get(sel_transfert_gnf_id, 0.0)

                    st.markdown(
                        f'<div style="background:#FBF0E7;border:1px solid #F0D9C4;border-radius:8px;'
                        f'padding:.55rem .85rem;font-size:.84rem;color:#9C4B22;margin-top:.2rem;display:flex;gap:2.5rem;flex-wrap:wrap">'
                        f'<span>👤 <strong>{nom_inv_t}</strong></span>'
                        f'<span>📅 Reçu le <strong>{dt_t}</strong></span>'
                        f'<span>💰 Total reçu : <strong>{fmt_gnf(gnf_recu)}</strong></span>'
                        f'<span>✅ Disponible : <strong style="color:#2F5D3C">{fmt_gnf(gnf_disponible_src)}</strong></span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(spacer("0.1rem"), unsafe_allow_html=True)
                else:
                    gnf_transfer_link_id = ""
                    inv_id = st.selectbox(
                        "Investisseur *",
                        options=list(noms_inv.keys()) if noms_inv else [""],
                        format_func=lambda x: noms_inv.get(x, x),
                        key="mvt_inv_interne",
                        disabled=READ_ONLY,
                    )
        else:
            gnf_transfer_link_id = ""
            inv_id = st.selectbox(
                "Investisseur *",
                options=list(noms_inv.keys()) if noms_inv else [""],
                format_func=lambda x: noms_inv.get(x, x),
                key="mvt_inv_interne",
                disabled=READ_ONLY,
            )

else:  # ajustement / frais_retrait
    sel_apport_id = ""
    gnf_transfer_link_id = ""
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

_frais_dst = compte_frais.get(dst_id, 0.0) if dst_id else 0.0

# ── Étape 3 : Montant ────────────────────────────────────────────────────────
st.markdown(form_step(3, "Montant"), unsafe_allow_html=True)

# ── Ligne montant + devise + taux + résultat ──────────────────────────────
_transfert_apport_mode = (type_mvt == "transfert" and bool(sel_apport_id))
_eur_max = apport_detail.get("eur_restant", 0.0) if _transfert_apport_mode else 0.0

cm1, cm2, cm3, cm4 = st.columns([2, 1.5, 2, 2])
with cm1:
    _step = 0.01 if (type_mvt in ("apport", "transfert")) else 1000.0
    _default_montant = float(_eur_max) if _transfert_apport_mode else 0.0
    montant = st.number_input(
        "Montant *", min_value=0.0, step=_step, format="%.2f",
        value=_default_montant,
        key="mvt_montant", disabled=READ_ONLY,
    )
with cm2:
    if type_mvt == "apport":
        devise = "EUR"
        st.markdown("<div style='font-weight:600;margin-bottom:.35rem'>Devise</div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:1rem;color:#241F19'>EUR</div>", unsafe_allow_html=True)
    elif type_mvt == "transfert" and _transfert_apport_mode:
        devise = "EUR"
        st.markdown("<div style='font-weight:600;margin-bottom:.35rem'>Devise</div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:1rem;color:#241F19'>EUR</div>", unsafe_allow_html=True)
    elif type_mvt == "transfert":
        devise = st.selectbox("Devise *", DEVISES, index=DEVISES.index("GNF"), key="mvt_devise_transfert", disabled=READ_ONLY)
    else:
        devise = st.selectbox("Devise *", DEVISES, key="mvt_devise", disabled=READ_ONLY)
with cm3:
    if devise == "EUR":
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

# ── Étape 4 : Aperçu automatique ────────────────────────────────────────────
_preview_rows = []
_preview_color = "blue"
_preview_footer = ""
_preview_matched_special = False

# Preview gain/perte de taux (transfert EUR depuis un apport)
if _transfert_apport_mode and montant > 0 and taux > 0:
    taux_estimatif = apport_detail.get("taux_estimatif", 0.0)
    if taux_estimatif and taux_estimatif > 0:
        gnf_estime = montant * taux_estimatif
        gnf_reel   = montant_gnf
        gain       = gnf_reel - gnf_estime
        gain_pct   = (gain / gnf_estime * 100) if gnf_estime else 0.0
        gain_color = "green" if gain > 1 else ("red" if gain < -1 else "slate")
        gain_icon  = "📈" if gain > 1 else ("📉" if gain < -1 else "=")
        gain_label = "Gain de taux" if gain > 1 else ("Perte de taux" if gain < -1 else "Égalité")
        gain_txt   = (f"+{fmt_gnf(gain)}" if gain > 1 else (fmt_gnf(gain) if gain < -1 else "—"))
        _preview_rows = [
            ("Montant envoyé (EUR)",  fmt_eur(montant),             "slate"),
            ("Taux appliqué",         f"{taux:,.0f} GNF/€",         "slate"),
            ("Montant converti GNF",  fmt_gnf(gnf_reel),            "blue"),
            ("Taux estimatif apport", f"{taux_estimatif:,.0f} GNF/€", "slate"),
            ("GNF estimé",            fmt_gnf(gnf_estime),          "slate"),
            (f"{gain_icon} {gain_label}",  f"{gain_txt} ({gain_pct:+.2f}%)" if abs(gain) > 1 else gain_txt, gain_color),
        ]
        _preview_color = gain_color
        _preview_footer = "Impact sur le capital : +{} GNF".format(fmt_gnf(gnf_reel))
        _preview_matched_special = True

# Preview frais de retrait cash (Orange Money)
_nom_src = noms_cpt.get(src_id, "") if src_id else ""
_frais_cash_taux: float | None = None
_frais_cash_gnf:  float | None = None

if type_mvt == "retrait" and _nom_src in FRAIS_RETRAIT_BAREME and montant_gnf > 0:
    if montant_gnf > ORANGE_MONEY_MAX_RETRAIT_GNF:
        st.error(
            f"🚫 **Plafond dépassé** — Orange Money limite les retraits à "
            f"**{ORANGE_MONEY_MAX_RETRAIT_GNF:,.0f} GNF** par opération.",
            icon=None,
        )
    else:
        _frais_cash_taux, _frais_cash_gnf = get_frais_retrait_cash(_nom_src, montant_gnf)
        if _frais_cash_taux is not None and _frais_cash_gnf is not None:
            _net_cash = montant_gnf - _frais_cash_gnf
            _tranche_txt = (
                "2 000 → 5 000 000 GNF" if montant_gnf <= 5_000_000
                else "5 000 001 → 15 000 000 GNF"
            )
            _preview_rows = [
                ("Montant retiré",      fmt_gnf(montant_gnf),       "slate"),
                ("Compte source",       _nom_src,                   "slate"),
                ("Taux frais",          f"{_frais_cash_taux*100:.2g}%  ·  tranche {_tranche_txt}", "amber"),
                ("Frais prélevés",      fmt_gnf(_frais_cash_gnf),   "violet"),
                ("Net reçu en espèces", fmt_gnf(_net_cash),         "green"),
            ]
            _preview_color = "violet"
            _preview_footer = f"Impact capital : −{fmt_gnf(_frais_cash_gnf)} (frais) · −{fmt_gnf(montant_gnf)} (retrait)"
            _preview_matched_special = True

# Preview frais sur transfert entrant
elif type_mvt == "transfert" and _frais_dst > 0 and dst_id and montant_gnf > 0:
    _frais_dst_gnf = round(montant_gnf * _frais_dst)
    _net_dst = montant_gnf - _frais_dst_gnf
    _preview_rows = [
        ("Montant envoyé",          fmt_gnf(montant_gnf),      "slate"),
        ("Compte destination",      noms_cpt.get(dst_id, dst_id), "slate"),
        ("Taux frais appliqué",     f"{_frais_dst*100:.0f}%",  "amber"),
        ("Frais prélevés",          fmt_gnf(_frais_dst_gnf),   "violet"),
        ("Montant réellement reçu", fmt_gnf(_net_dst),         "green"),
    ]
    _preview_color = "amber"
    _preview_footer = f"Un mouvement frais_retrait de {fmt_gnf(_frais_dst_gnf)} sera créé automatiquement."
    _preview_matched_special = True

# Aperçu générique — couvre tous les autres cas (aucun frais, aucun écart de taux) pour que
# la prévisualisation soit systématique, pas seulement sur les scénarios à calcul particulier.
if not _preview_matched_special and montant_gnf > 0:
    _label_type = {"apport": "Apport", "transfert": "Transfert", "retrait": "Retrait"}.get(type_mvt, str(type_mvt).capitalize())
    _preview_rows = [("Type de mouvement", _label_type, "slate")]
    if devise == "EUR":
        _preview_rows.append(("Montant envoyé", fmt_eur(montant), "slate"))
        _preview_rows.append(("Taux appliqué", f"{taux:,.0f} GNF/€".replace(",", " "), "slate"))
        _preview_rows.append(("Montant converti GNF", fmt_gnf(montant_gnf), "blue"))
    else:
        _preview_rows.append(("Montant", fmt_gnf(montant_gnf), "blue"))
    if src_id:
        _preview_rows.append(("Compte source", noms_cpt.get(src_id, src_id), "slate"))
    if dst_id:
        _preview_rows.append(("Compte destination", noms_cpt.get(dst_id, dst_id), "slate"))
    if inv_id:
        _preview_rows.append(("Investisseur", noms_inv.get(inv_id, inv_id), "slate"))

    if type_mvt == "apport":
        _preview_color = "green"
        _preview_footer = f"Impact sur le capital : +{fmt_gnf(montant_gnf)}"
    elif type_mvt == "retrait":
        _preview_color = "red"
        _preview_footer = f"Impact sur le capital : −{fmt_gnf(montant_gnf)}"
    elif type_mvt == "transfert":
        _preview_color = "blue"
        _preview_footer = "Transfert interne — le capital total valorisé ne change pas."

if _preview_rows and montant_gnf > 0:
    st.markdown(form_step(4, "Aperçu de l'opération"), unsafe_allow_html=True)
    st.markdown(
        preview_card("Simulation avant validation", _preview_rows, _preview_color, _preview_footer),
        unsafe_allow_html=True,
    )

# ── Étape 5 : Valider ─────────────────────────────────────────────────────────
st.markdown(form_step(5, "Commentaire & validation"), unsafe_allow_html=True)

commentaire = st.text_area("Commentaire", placeholder="Description du mouvement…", height=70, key="mvt_commentaire", disabled=READ_ONLY)
compte_dans_capital = type_mvt in ("apport", "retrait")

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
        errors.append("Un retrait requiert un compte source — choisissez le compte d'où sort l'argent.")
    if type_mvt == "retrait" and src_id and _nom_src in FRAIS_RETRAIT_BAREME:
        if montant_gnf > ORANGE_MONEY_MAX_RETRAIT_GNF:
            errors.append(
                f"Impossible de retirer plus de {ORANGE_MONEY_MAX_RETRAIT_GNF:,.0f} GNF "
                f"en une seule opération sur Orange Money."
            )
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
                if _transfert_apport_mode and montant > _eur_max + 0.01:
                    errors.append(f"Le montant ({montant:,.2f} €) dépasse le solde disponible sur cet apport ({_eur_max:,.2f} €).")
            elif src_dev == dst_dev:
                if src_dev == "GNF" and devise != "GNF":
                    errors.append("Le transfert interne GNF doit être saisi en GNF.")
                if src_dev == "EUR" and devise != "EUR":
                    errors.append("Le transfert interne EUR doit être saisi en EUR.")
                if src_dev == "GNF" and gnf_transfer_link_id and gnf_disponible_src is not None:
                    if montant > gnf_disponible_src + 0.01:
                        errors.append(
                            f"Le montant ({montant:,.0f} GNF) dépasse le disponible "
                            f"({gnf_disponible_src:,.0f} GNF) sur ce transfert source."
                        )
            else:
                errors.append(
                    "Seuls les transferts internes par devise et les transferts EUR→GNF sont pris en charge."
                )

    if errors:
        for e in errors:
            st.error(e)
    else:
        _apport_src = sel_apport_id if _transfert_apport_mode else gnf_transfer_link_id
        ok = add_mouvement(
            date_mvt=date_mvt.isoformat(), type_mouvement=type_mvt,
            investisseur_id=inv_id, montant_origine=montant,
            devise_origine=devise, taux_eur_gnf=taux,
            montant_converti_gnf=montant_gnf,
            compte_source_id=src_id, compte_destination_id=dst_id,
            commentaire=commentaire.strip(),
            compte_dans_capital=compte_dans_capital,
            apport_source_id=_apport_src,
        )
        if ok:
            frais_pct_dst = compte_frais.get(dst_id, 0.0) if dst_id else 0.0
            if type_mvt == "transfert" and frais_pct_dst > 0 and dst_id:
                frais_gnf = round(montant_gnf * frais_pct_dst)
                nom_dst = noms_cpt.get(dst_id, dst_id)
                add_mouvement(
                    date_mvt=date_mvt.isoformat(),
                    type_mouvement="frais_retrait",
                    investisseur_id=inv_id,
                    montant_origine=frais_gnf,
                    devise_origine="GNF",
                    taux_eur_gnf=1,
                    montant_converti_gnf=frais_gnf,
                    compte_source_id=dst_id,
                    compte_destination_id="",
                    commentaire=f"Frais de retrait {frais_pct_dst*100:.0f}% — {nom_dst}",
                    compte_dans_capital=True,
                    apport_source_id=_apport_src,
                )
                st.success(
                    f"✅ **Transfert** enregistré — **{fmt_gnf(montant_gnf)}** le {date_mvt}  \n"
                    f"🏧 **Frais de retrait** déduits automatiquement : **{fmt_gnf(frais_gnf)}** ({frais_pct_dst*100:.0f}%)"
                )
            elif type_mvt == "retrait" and _frais_cash_gnf and _frais_cash_gnf > 0:
                add_mouvement(
                    date_mvt=date_mvt.isoformat(),
                    type_mouvement="frais_retrait",
                    investisseur_id=inv_id,
                    montant_origine=_frais_cash_gnf,
                    devise_origine="GNF",
                    taux_eur_gnf=1,
                    montant_converti_gnf=_frais_cash_gnf,
                    compte_source_id=src_id,
                    compte_destination_id="",
                    commentaire=f"Frais retrait {_frais_cash_taux*100:.2g}% — {_nom_src}",
                    compte_dans_capital=True,
                    apport_source_id="",
                )
                st.success(
                    f"✅ **Retrait** enregistré — **{fmt_gnf(montant_gnf)}** le {date_mvt}  \n"
                    f"🏧 **Frais de retrait** déduits automatiquement : "
                    f"**{fmt_gnf(_frais_cash_gnf)}** ({_frais_cash_taux*100:.2g}%)"
                )
            else:
                st.success(
                    f"✅ **{type_mvt.capitalize()}** enregistré — "
                    f"**{fmt_gnf(montant_gnf)}** le {date_mvt}"
                )
            st.cache_data.clear()
            st.rerun()

st.markdown('</div>', unsafe_allow_html=True)

st.markdown(divider(), unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# DERNIÈRES OPÉRATIONS — le tableau complet, les filtres et la recherche vivent
# désormais sur la page Historique (voir lien ci-dessous) pour éviter deux
# grands tableaux quasi identiques.
# ══════════════════════════════════════════════════════════════════════════════
_col_hd, _col_lk = st.columns([5, 1.5])
with _col_hd:
    st.markdown(section_header("Dernières opérations", "📋", "#6B6155"), unsafe_allow_html=True)
with _col_lk:
    st.markdown(spacer("1rem"), unsafe_allow_html=True)
    st.page_link("pages/7_Historique.py", label="Historique complet →", icon="📜")

st.markdown(spacer("0.25rem"), unsafe_allow_html=True)

if not df_mvt.empty:
    df_recent = df_mvt.copy()
    df_recent["date"] = pd.to_datetime(df_recent["date"], errors="coerce")
    df_recent["montant_converti_gnf"] = pd.to_numeric(df_recent["montant_converti_gnf"], errors="coerce").fillna(0)
    df_recent["investisseur"] = df_recent["investisseur_id"].map(noms_inv).fillna(df_recent["investisseur_id"])
    df_recent["src_nom"]      = df_recent["compte_source_id"].map(noms_cpt).fillna("—")
    df_recent["dst_nom"]      = df_recent["compte_destination_id"].map(noms_cpt).fillna("—")
    df_recent = df_recent.sort_values("date", ascending=False).head(8)

    st.markdown('<div class="card" style="padding:1rem 1.25rem">', unsafe_allow_html=True)

    h = st.columns([1.3, 1.6, 2, 2.4, 1.7, 1.7, 2.2, 1.1])
    _mv_labels = ["Date", "Type", "Investisseur", "Montant GNF", "Source", "Destination", "Commentaire", ""]
    _mv_classes = ["th", "th", "th", "th th-num", "th", "th", "th", "th"]
    for col, lbl, cls in zip(h, _mv_labels, _mv_classes):
        with col:
            st.markdown(f'<div class="{cls}">{lbl}</div>', unsafe_allow_html=True)
    st.markdown('<hr style="border:none;border-top:1.5px solid #E8E1D6;margin:.4rem 0">', unsafe_allow_html=True)

    for _, row in df_recent.iterrows():
        c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([1.3, 1.6, 2, 2.4, 1.7, 1.7, 2.2, 1.1])
        with c1:
            st.markdown(f'<div class="row-date">{str(row["date"])[:10] if pd.notna(row["date"]) else "—"}</div>', unsafe_allow_html=True)
        with c2:
            _type_row = str(row["type_mouvement"])
            _badge_label = None
            if _type_row == "frais_retrait":
                _src_nom = row.get("src_nom", "") or ""
                _commentaire = str(row.get("commentaire", ""))
                if "Orange Marchand" in _src_nom or "Orange Marchand" in _commentaire:
                    _badge_label = "Frais Orange Marchand"
            st.markdown(badge_mouvement(_type_row, label=_badge_label), unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div style="font-size:.85rem;color:#4A4238;font-weight:500">{row.get("investisseur","—")}</div>', unsafe_allow_html=True)
        with c4:
            st.markdown(f'<div class="row-amount">{fmt_gnf(row["montant_converti_gnf"])}</div>', unsafe_allow_html=True)
            if str(row.get("devise_origine","")) == "EUR":
                st.markdown(f'<div class="row-comment num">{fmt_eur(row["montant_origine"])} @ {fmt_taux(row["taux_eur_gnf"])}</div>', unsafe_allow_html=True)
        with c5:
            st.markdown(f'<div class="row-comment">{row.get("src_nom","—")}</div>', unsafe_allow_html=True)
        with c6:
            st.markdown(f'<div class="row-comment">{row.get("dst_nom","—")}</div>', unsafe_allow_html=True)
        with c7:
            st.markdown(f'<div class="row-comment">{str(row.get("commentaire",""))[:50]}</div>', unsafe_allow_html=True)
        with c8:
            if not READ_ONLY:
                _desc = f"ce mouvement du {str(row['date'])[:10]} ({fmt_gnf(row['montant_converti_gnf'])})"
                if confirm_delete(f"mvt_del_{row['id']}", _desc):
                    if delete_mouvement(row["id"]):
                        st.cache_data.clear()
                        st.rerun()
        st.markdown('<hr style="border:none;border-top:1px solid #F5F1EA;margin:.25rem 0">', unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
else:
    st.markdown(
        empty_state("💸", "Aucun mouvement enregistré", "Utilisez le formulaire ci-dessus pour créer le premier mouvement."),
        unsafe_allow_html=True,
    )
