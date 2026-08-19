"""
Design system — composants HTML/CSS premium.
Style inspiré de Legend Farm : propre, aéré, cartes soignées, premium.
Adapté à un usage financier / suivi de capital : sobre, rassurant, SaaS.
"""

import streamlit as st
from utils.config import COULEUR_BADGE_MOUVEMENT, EMOJI_MOUVEMENT, LABELS_MOUVEMENT, PROJECT_NAME

# ── Palette — identité Legend Farm ──────────────────────────────────────────────
# "blue" reste la clé utilisée dans tout le code existant pour l'accent principal
# (KPI, boutons, hero…) — seule sa valeur change, du bleu SaaS générique vers la
# terre cuite chaude qui porte l'identité Legend Farm.
_ACCENT = {
    "navy":   ("#241F19", "#F5F1EA", "#4A4238"),  # structure, titres forts
    "blue":   ("#B65C2E", "#FBF0E7", "#F0D9C4"),  # accent principal Legend Farm
    "green":  ("#3E7C51", "#EEF5EF", "#BFD9C4"),  # positif, disponible, reçu
    "red":    ("#B3432F", "#FBEEEA", "#E8C4BB"),  # dépenses, sorties, erreurs
    "amber":  ("#99651A", "#FBF3E4", "#EAD2A0"),  # attente, attention, frais
    "teal":   ("#3B7A73", "#EDF5F3", "#C3DEDA"),  # forage, eau
    "orange": ("#8B4E1F", "#F3E9DC", "#E0C7A8"),  # énergie, chantier — volontairement plus brun/mat que "blue" (accent principal)
    "violet": ("#6B5B95", "#F1EEF7", "#D9D0E8"),  # frais, outils
    "slate":  ("#6B6155", "#F5F1EA", "#E8E1D6"),  # neutre, texte, bordures
}


def accent_colors() -> dict:
    """Retourne la palette complète pour usage externe."""
    return dict(_ACCENT)

# ── Formatage ─────────────────────────────────────────────────────────────────

def fmt_gnf(montant: float) -> str:
    try:
        return f"{int(round(float(montant))):,} GNF".replace(",", " ")
    except (TypeError, ValueError):
        return "—"


def fmt_eur(montant: float) -> str:
    try:
        return f"{montant:,.2f} €".replace(",", " ").replace(".", ",")
    except (TypeError, ValueError):
        return "—"


def fmt_montant(montant: float, devise: str) -> str:
    return fmt_eur(montant) if devise == "EUR" else fmt_gnf(montant)


def fmt_pct(valeur: float, decimales: int = 1) -> str:
    try:
        return f"{valeur:.{decimales}f} %"
    except (TypeError, ValueError):
        return "—"


def fmt_taux(taux: float) -> str:
    try:
        v = int(taux)
        if v <= 0:
            return "—"
        return f"{v:,} GNF/€".replace(",", " ")
    except (TypeError, ValueError):
        return "—"


# ══════════════════════════════════════════════════════════════════════════════

def fmt_gnf_court(montant: float, taux: float = 0) -> str:
    """
    Format compact pour les grands montants GNF.
    - < 1 000 000 : format normal  -> "450 000 GNF"
    - >= 1 000 000 : en millions   -> "43,9 M GNF"
    Si taux > 0, ajoute l'equivalent EUR -> "43,9 M GNF (~4 184 EUR)"
    """
    try:
        v = float(montant)
        if v >= 1_000_000:
            millions = v / 1_000_000
            if millions >= 100:
                gnf_txt = f"{millions:.0f} M GNF"
            else:
                gnf_txt = f"{millions:.1f} M GNF".replace(".", ",")
        else:
            gnf_txt = fmt_gnf(v)

        if taux and float(taux) > 0:
            eur = v / float(taux)
            gnf_txt += f" (~{fmt_eur(eur)})"
        return gnf_txt
    except (TypeError, ValueError):
        return "—"


# CSS GLOBAL
# ══════════════════════════════════════════════════════════════════════════════

def inject_css():
    st.markdown(
        """
<style>
/* ── Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,300;0,14..32,400;0,14..32,500;0,14..32,600;0,14..32,700;0,14..32,800;0,14..32,900&display=swap');

*, *::before, *::after { box-sizing: border-box; }

/* ══════════════════════════════════════════════════════════════════════
   DESIGN TOKENS — identité Legend Farm
   Terre cuite chaude + encre chaude + ivoire, plutôt que le bleu/gris
   froid générique des tableaux de bord SaaS. Une seule source de vérité :
   modifier la charte graphique globale se fait ici, et nulle part ailleurs.
   ══════════════════════════════════════════════════════════════════════ */
:root {
    /* Couleur */
    --lf-primary: #B65C2E;
    --lf-primary-hover: #9C4B22;
    --lf-primary-subtle: #FBF0E7;
    --lf-primary-subtle-border: #F0D9C4;

    --lf-bg: #FAF8F4;
    --lf-surface: #FFFFFF;
    --lf-surface-elevated: #FFFFFF;
    --lf-surface-subtle: #F5F1EA;
    --lf-border: #E8E1D6;
    --lf-border-subtle: #F0EBE2;

    --lf-text: #241F19;
    --lf-text-secondary: #6B6155;
    --lf-text-muted: #7F7568;
    --lf-on-primary: #FFFFFF;

    --lf-success: #3E7C51;
    --lf-success-bg: #EEF5EF;
    --lf-warning: #99651A;
    --lf-warning-bg: #FBF3E4;
    --lf-error: #B3432F;
    --lf-error-bg: #FBEEEA;
    --lf-info: #46688A;
    --lf-info-bg: #EBF1F6;

    /* Rayons */
    --lf-radius-sm: 8px;
    --lf-radius-md: 12px;
    --lf-radius-lg: 16px;
    --lf-radius-full: 999px;

    /* Ombres — discrètes, jamais décoratives */
    --lf-shadow-sm: 0 1px 2px rgba(36,31,25,.05);
    --lf-shadow-md: 0 2px 10px rgba(36,31,25,.06), 0 1px 2px rgba(36,31,25,.04);
    --lf-shadow-lg: 0 8px 28px rgba(36,31,25,.10);

    /* Échelle d'espacement — 4 / 8 / 12 / 16 / 24 / 32 / 48 */
    --sp-1: .25rem;
    --sp-2: .5rem;
    --sp-3: .75rem;
    --sp-4: 1rem;
    --sp-6: 1.5rem;
    --sp-8: 2rem;
    --sp-12: 3rem;
}

html, body, [class*="css"], .stApp {
    font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
    -webkit-font-smoothing: antialiased !important;
    -moz-osx-font-smoothing: grayscale !important;
}

/* ── Streamlit chrome ── */
#MainMenu, footer, [data-testid="stDecoration"],
[data-testid="stToolbar"] { visibility: hidden !important; }
header { visibility: visible !important; background: transparent !important; }
header [data-testid="stToolbar"],
header [data-testid="stDecoration"],
header [data-testid="stMainMenuPopover"] { visibility: hidden !important; }

/* ── App background ── */
.stApp { background: var(--lf-bg) !important; }
.main  { background: var(--lf-bg) !important; }

/* ── Main block ── */
.main .block-container {
    padding: var(--sp-6) var(--sp-8) var(--sp-12) var(--sp-8) !important;
    max-width: 1440px !important;
}

/* ── Headings ── */
h1 { font-size: 1.5rem !important; font-weight: 750 !important;
     letter-spacing: -0.02em !important; color: var(--lf-text) !important; margin: 0 !important; }
h2 { font-size: 1.05rem !important; font-weight: 650 !important; color: var(--lf-text) !important; }
h3 { font-size: .92rem !important; font-weight: 600 !important; color: var(--lf-text-secondary) !important; }
p  { color: var(--lf-text-secondary) !important; font-size: .875rem !important; line-height: 1.55 !important; }

/* ── Sidebar — encre chaude, structurée, identité propre ── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #211D18 0%, #1A1714 100%) !important;
    border-right: 1px solid rgba(255,255,255,0.04) !important;
    min-width: 252px !important;
}
section[data-testid="stSidebar"] > div { background: transparent !important; }
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] small {
    color: #A69C8D !important;
    font-size: .81rem !important;
}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 { color: #F5F1EA !important; }

/* Sidebar — marque Legend Farm */
.lf-brand {
    display: flex; align-items: center; gap: .6rem;
    padding: var(--sp-4) var(--sp-4) var(--sp-3) var(--sp-4);
    border-bottom: 1px solid rgba(255,255,255,.06);
    margin-bottom: var(--sp-2);
}
.lf-brand-mark {
    width: 34px; height: 34px; flex-shrink: 0;
    background: linear-gradient(135deg, var(--lf-primary) 0%, #8C4319 100%);
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1rem; font-weight: 800; color: #fff;
    box-shadow: 0 2px 8px rgba(182,92,46,.35);
}
.lf-brand-name { font-size: .92rem; font-weight: 700; color: #F5F1EA; letter-spacing: -.01em; line-height: 1.2; }
.lf-brand-tag  { font-size: .68rem; font-weight: 500; color: #857A6B; letter-spacing: .01em; }

/* Sidebar — logo / titre application (fallback natif Streamlit) */
[data-testid="stSidebarHeader"] {
    padding: .5rem .75rem 0 !important;
}

/* Sidebar nav items */
[data-testid="stSidebarNav"] { padding: .25rem 0 !important; }
[data-testid="stSidebarNav"] a {
    display: flex !important;
    align-items: center !important;
    gap: .55rem !important;
    border-radius: var(--lf-radius-sm) !important;
    padding: .5rem .8rem !important;
    margin: 1px .5rem !important;
    color: #A69C8D !important;
    font-size: .82rem !important;
    font-weight: 500 !important;
    text-decoration: none !important;
    transition: background .15s, color .15s !important;
    letter-spacing: 0 !important;
}
[data-testid="stSidebarNav"] a:hover {
    background: rgba(255,255,255,.05) !important;
    color: #E8E1D6 !important;
}
[data-testid="stSidebarNav"] a[aria-selected="true"] {
    background: rgba(182,92,46,.16) !important;
    color: #E8A578 !important;
    font-weight: 600 !important;
    box-shadow: inset 3px 0 0 var(--lf-primary) !important;
}
/* Sidebar group labels */
[data-testid="stSidebarNavSeparator"] {
    border-color: rgba(255,255,255,.05) !important;
    margin: .4rem .75rem !important;
}
[data-testid="stSidebarNavLink"] + [data-testid="stSidebarNavSeparator"] { margin-top: .6rem !important; }

/* Group title styling — discret, plus de majuscules criardes.
   NB : Streamlit rend chaque libellé de groupe comme un <header> natif,
   colorié par défaut en encre foncée (rgba(15,23,42,.85)) pensée pour une
   sidebar CLAIRE. Sur notre sidebar sombre, ce ton par défaut est presque
   invisible — bug réel constaté à l'écran et corrigé ici en ciblant le tag
   <header> directement (le sélecteur générique `span` ne correspondait à
   rien dans cette version de Streamlit). */
[data-testid="stSidebarNavItems"] header {
    font-size: .68rem !important;
    font-weight: 600 !important;
    text-transform: none !important;
    letter-spacing: .01em !important;
    color: #8A8070 !important;
    padding: .6rem .8rem .25rem !important;
    display: block !important;
}

/* La navigation compte 9 pages sur 4 groupes : au-delà d'une certaine
   hauteur de fenêtre, st.navigation replie les pages en trop derrière un
   bouton "Afficher plus" (rendu conditionnel côté React, pas un simple
   overflow CSS — impossible à neutraliser par CSS seul). On s'assure donc
   qu'il reste très visible plutôt que de tenter de le supprimer. */
[data-testid="stSidebarNavViewButton"] {
    display: flex !important;
    align-items: center !important;
    gap: .35rem !important;
    color: #E8A578 !important;
    font-size: .78rem !important;
    font-weight: 650 !important;
    background: rgba(182,92,46,.14) !important;
    border: 1px solid rgba(182,92,46,.3) !important;
    border-radius: var(--lf-radius-sm) !important;
    margin: .3rem .5rem !important;
    padding: .4rem .8rem !important;
    width: calc(100% - 1rem) !important;
}
[data-testid="stSidebarNavViewButton"]:hover {
    background: rgba(182,92,46,.22) !important;
    color: #F0B98D !important;
}
[data-testid="stSidebarNavViewButton"] svg { fill: #E8A578 !important; }

/* ── Page title area (h2 on each page) ── */
.stApp .main .block-container h2:first-of-type {
    font-size: 1.3rem !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em !important;
    color: var(--lf-text) !important;
}

/* ── HR ── */
hr {
    border: none !important;
    border-top: 1px solid var(--lf-border) !important;
    margin: var(--sp-4) 0 !important;
}

/* ── Cards ── */
.card {
    background: var(--lf-surface);
    border: 1px solid var(--lf-border);
    border-radius: var(--lf-radius-md);
    box-shadow: var(--lf-shadow-sm);
    padding: var(--sp-6);
    transition: border-color .15s, box-shadow .15s;
}
.card:hover {
    box-shadow: var(--lf-shadow-md);
    border-color: #DCD2C2;
}

/* ── KPI cards ── */
.kpi {
    background: var(--lf-surface);
    border: 1px solid var(--lf-border);
    border-radius: var(--lf-radius-md);
    box-shadow: var(--lf-shadow-sm);
    padding: var(--sp-4) var(--sp-4) var(--sp-4) var(--sp-4);
    position: relative;
    overflow: hidden;
    transition: border-color .15s, box-shadow .15s;
    margin-bottom: var(--sp-2);
}
.kpi::before {
    content: '';
    position: absolute;
    top: 0; left: 0; bottom: 0;
    width: 3px;
    background: var(--ka, var(--lf-primary));
}
.kpi:hover {
    box-shadow: var(--lf-shadow-md);
    border-color: #DCD2C2;
}
.kpi-hdr { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: var(--sp-3); }
.kpi-lbl {
    font-size: .74rem; font-weight: 600; text-transform: none;
    letter-spacing: 0; color: var(--lf-text-secondary);
}
.kpi-ico {
    width: 30px; height: 30px;
    background: var(--ka-bg, var(--lf-primary-subtle));
    border-radius: var(--lf-radius-sm);
    display: flex; align-items: center; justify-content: center;
    font-size: .92rem;
    flex-shrink: 0;
}
.kpi-val {
    font-size: 1.5rem; font-weight: 700; color: var(--lf-text);
    letter-spacing: -0.01em; line-height: 1.15;
    font-variant-numeric: tabular-nums;
}
.kpi-sub {
    font-size: .74rem; color: var(--lf-text-muted); font-weight: 500;
    margin-top: var(--sp-2); line-height: 1.4;
}

/* ── KPI de premier plan — hiérarchie à deux niveaux dans une même rangée ── */
.kpi-lg { padding: var(--sp-6) var(--sp-4) var(--sp-4) var(--sp-4); }
.kpi-lg .kpi-val { font-size: 2rem; letter-spacing: -0.02em; }
.kpi-lg .kpi-ico { width: 38px; height: 38px; font-size: 1.15rem; }
.kpi-lg .kpi-lbl { font-size: .78rem; font-weight: 650; }

/* ── Section header (Legend Farm style) ── */
.sec-hdr {
    display: flex; align-items: center; gap: var(--sp-2);
    margin: var(--sp-6) 0 var(--sp-3) 0;
}
.sec-bar {
    width: 3px; height: 13px;
    background: var(--sb, var(--lf-primary));
    border-radius: 2px; flex-shrink: 0;
}
.sec-ttl {
    font-size: .78rem; font-weight: 600;
    text-transform: none; letter-spacing: 0;
    color: var(--lf-text-secondary);
}
.sec-line {
    flex: 1; height: 1px;
    background: linear-gradient(90deg, var(--lf-border) 0%, transparent 80%);
}

/* ── Page header ── */
.pg-hdr { margin-bottom: var(--sp-6); }
.pg-hdr-top { display: flex; align-items: baseline; gap: .6rem; margin-bottom: .2rem; }
.pg-ttl {
    font-size: 1.4rem; font-weight: 700; color: var(--lf-text);
    letter-spacing: -0.02em;
}
.pg-badge {
    font-size: .68rem; font-weight: 600; text-transform: none;
    letter-spacing: 0; color: var(--lf-primary);
    background: var(--lf-primary-subtle); border-radius: var(--lf-radius-full);
    padding: .17rem .6rem;
}
.pg-desc { font-size: .85rem; color: var(--lf-text-secondary); font-weight: 450; margin-bottom: var(--sp-3); }
.pg-line {
    height: 1px;
    background: linear-gradient(90deg, var(--lf-border) 0%, var(--lf-primary-subtle-border) 30%, var(--lf-border) 100%);
}

/* ── Hero banner ── */
.hero {
    background: linear-gradient(135deg, #211D18 0%, #3A2A1E 55%, #8C4319 100%);
    border-radius: var(--lf-radius-lg);
    padding: var(--sp-6) var(--sp-8);
    color: #fff;
    position: relative;
    overflow: hidden;
    box-shadow: var(--lf-shadow-lg);
}
.hero::before {
    content: ''; position: absolute;
    top: -90px; right: -50px;
    width: 300px; height: 300px;
    background: rgba(255,255,255,.04); border-radius: 50%;
}
.hero::after {
    content: ''; position: absolute;
    bottom: -80px; right: 130px;
    width: 180px; height: 180px;
    background: rgba(255,255,255,.03); border-radius: 50%;
}
.hero-chip {
    display: inline-flex; align-items: center; gap: .35rem;
    background: rgba(255,255,255,.1);
    border: 1px solid rgba(255,255,255,.16);
    border-radius: var(--lf-radius-full); padding: .22rem .7rem;
    font-size: .72rem; font-weight: 600;
    letter-spacing: .01em; text-transform: none;
    color: rgba(255,255,255,.85); margin-bottom: var(--sp-3);
}
.hero-amount {
    font-size: 2.35rem; font-weight: 750;
    letter-spacing: -.03em; line-height: 1;
    margin-bottom: var(--sp-1);
    font-variant-numeric: tabular-nums;
}
.hero-sub { font-size: .82rem; color: rgba(255,255,255,.58); font-weight: 450; }
.hero-meta {
    display: flex; gap: var(--sp-6);
    margin-top: var(--sp-4); padding-top: var(--sp-3);
    border-top: 1px solid rgba(255,255,255,.1);
}
.hero-meta-item { display: flex; flex-direction: column; }
.hero-meta-lbl {
    font-size: .68rem; font-weight: 500;
    text-transform: none; letter-spacing: 0;
    color: rgba(255,255,255,.42); margin-bottom: .15rem;
}
.hero-meta-val { font-size: .9rem; font-weight: 650; color: rgba(255,255,255,.92); }

/* ── Progress bars ── */
.prog { background: var(--lf-surface-subtle); border-radius: var(--lf-radius-full); height: 6px; overflow: hidden; margin: .2rem 0; }
.prog-fill {
    height: 100%; border-radius: var(--lf-radius-full);
    background: var(--lf-primary); position: relative;
    transition: width .4s cubic-bezier(.4,0,.2,1);
}
.prog-fill::after {
    content: ''; position: absolute; inset: 0;
    background: linear-gradient(90deg, transparent 60%, rgba(255,255,255,.2));
}
.prog-fill.green  { background: var(--lf-success); }
.prog-fill.amber  { background: var(--lf-warning); }
.prog-fill.red    { background: var(--lf-error); }
.prog-fill.violet { background: #6B5B95; }

/* ── Badge mouvement ── */
.badge {
    display: inline-flex; align-items: center; gap: .28rem;
    padding: .2rem .55rem; border-radius: var(--lf-radius-sm);
    font-size: .72rem; font-weight: 600;
    letter-spacing: 0; text-transform: none;
    white-space: nowrap;
}

/* ── Table ── */
.th {
    font-size: .72rem; font-weight: 600;
    text-transform: none; letter-spacing: 0; color: var(--lf-text-muted);
    padding-bottom: var(--sp-2);
}
.row-date   { font-size: .8rem; font-weight: 500; color: var(--lf-text-secondary); }
.row-amount { font-size: .88rem; font-weight: 650; color: var(--lf-text); font-variant-numeric: tabular-nums; text-align: right; }
.th.th-num, .row-comment.num { text-align: right; }
.row-comment{ font-size: .78rem; color: var(--lf-text-secondary); line-height: 1.45; }

/* ── Obj card ── */
.obj-card {
    background: var(--lf-surface); border: 1px solid var(--lf-border);
    border-radius: var(--lf-radius-md); padding: var(--sp-4) var(--sp-6);
    box-shadow: var(--lf-shadow-sm);
    margin-bottom: var(--sp-3);
}
.obj-card-title { font-size: .95rem; font-weight: 650; color: var(--lf-text);
                  letter-spacing: -.005em; margin-bottom: .15rem; }
.obj-card-desc  { font-size: .8rem; color: var(--lf-text-secondary); margin-bottom: var(--sp-3); }
.obj-pct {
    font-size: 1.7rem; font-weight: 750;
    letter-spacing: -.02em; color: var(--lf-text); line-height: 1;
    font-variant-numeric: tabular-nums;
}

/* ── Empty state ── */
.empty-state {
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    padding: var(--sp-8) var(--sp-6); text-align: center;
    background: var(--lf-surface-subtle); border: 1.5px dashed var(--lf-border);
    border-radius: var(--lf-radius-md); color: var(--lf-text-muted);
}
.empty-state-icon { font-size: 2rem; margin-bottom: var(--sp-3); opacity: .65; }
.empty-state-title { font-size: .95rem; font-weight: 650; color: var(--lf-text-secondary); margin-bottom: var(--sp-1); }
.empty-state-desc  { font-size: .82rem; color: var(--lf-text-muted); max-width: 340px; }

/* ── Streamlit inputs ── */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stDateInput"] input {
    border-radius: var(--lf-radius-sm) !important;
    border: 1px solid var(--lf-border) !important;
    font-size: .875rem !important;
    background: var(--lf-surface-subtle) !important;
    color: var(--lf-text) !important;
    transition: border-color .15s, box-shadow .15s !important;
    padding: .5rem .75rem !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus,
[data-testid="stDateInput"] input:focus {
    border-color: var(--lf-primary) !important;
    box-shadow: 0 0 0 3px rgba(182,92,46,.12) !important;
    background: #fff !important;
    outline: none !important;
}
[data-testid="stTextArea"] textarea {
    border-radius: var(--lf-radius-sm) !important;
    border: 1px solid var(--lf-border) !important;
    font-size: .875rem !important;
    background: var(--lf-surface-subtle) !important;
    color: var(--lf-text) !important;
    resize: vertical !important;
}
[data-testid="stTextArea"] textarea:focus {
    border-color: var(--lf-primary) !important;
    box-shadow: 0 0 0 3px rgba(182,92,46,.12) !important;
    background: #fff !important;
}

/* Labels */
label, [data-testid="stWidgetLabel"] p {
    font-size: .8rem !important;
    font-weight: 550 !important;
    color: var(--lf-text-secondary) !important;
    letter-spacing: 0 !important;
    margin-bottom: .25rem !important;
}

/* Buttons */
.stButton > button, .stDownloadButton > button {
    border-radius: var(--lf-radius-sm) !important;
    font-weight: 600 !important;
    font-size: .84rem !important;
    padding: .5rem 1.15rem !important;
    transition: all .15s !important;
    letter-spacing: 0 !important;
}
button[kind="primary"] {
    background: var(--lf-primary) !important;
    border-color: var(--lf-primary) !important;
    color: #fff !important;
    box-shadow: 0 1px 2px rgba(182,92,46,.3) !important;
}
button[kind="primary"]:hover {
    background: var(--lf-primary-hover) !important;
    border-color: var(--lf-primary-hover) !important;
    box-shadow: 0 3px 10px rgba(182,92,46,.35) !important;
}
button[kind="secondary"] {
    background: var(--lf-surface) !important;
    border-color: var(--lf-border) !important;
    color: var(--lf-text-secondary) !important;
}
button[kind="secondary"]:hover {
    background: var(--lf-surface-subtle) !important;
    border-color: #DCD2C2 !important;
    color: var(--lf-text) !important;
}

/* Selectbox */
[data-testid="stSelectbox"] > div > div,
[data-baseweb="select"] > div:first-child {
    border-radius: var(--lf-radius-sm) !important;
    border-color: var(--lf-border) !important;
    font-size: .875rem !important;
    background: var(--lf-surface-subtle) !important;
    color: var(--lf-text) !important;
}
[data-baseweb="tag"] {
    background: var(--lf-primary-subtle) !important;
    border-radius: 5px !important;
}
[data-baseweb="tag"] span { color: var(--lf-primary-hover) !important; font-weight: 600 !important; }

/* Expander */
[data-testid="stExpander"] details {
    border-radius: var(--lf-radius-md) !important;
    border: 1px solid var(--lf-border) !important;
    background: var(--lf-surface) !important;
}
[data-testid="stExpander"] summary {
    font-size: .86rem !important;
    font-weight: 600 !important;
    color: var(--lf-text) !important;
    padding: .7rem 1rem !important;
}
[data-testid="stExpander"] summary:hover { background: var(--lf-surface-subtle) !important; }

/* Metrics */
[data-testid="stMetric"] {
    background: var(--lf-surface); border: 1px solid var(--lf-border);
    border-radius: var(--lf-radius-md); padding: var(--sp-4) var(--sp-4) !important;
}
[data-testid="stMetricLabel"] p {
    font-size: .74rem !important; font-weight: 600 !important;
    text-transform: none; letter-spacing: 0; color: var(--lf-text-secondary) !important;
}
[data-testid="stMetricValue"] {
    font-size: 1.3rem !important; font-weight: 700 !important;
    color: var(--lf-text) !important; letter-spacing: -.01em !important;
}

/* Checkbox */
[data-testid="stCheckbox"] label p {
    font-size: .85rem !important; color: var(--lf-text-secondary) !important;
}

/* Form container */
[data-testid="stForm"] {
    background: var(--lf-surface);
    border: 1px solid var(--lf-border);
    border-radius: var(--lf-radius-md);
    padding: var(--sp-6) !important;
    box-shadow: var(--lf-shadow-sm);
}

/* Column gap */
[data-testid="column"] { gap: 0 !important; }

/* Plotly chart container */
.stPlotlyChart > div {
    border-radius: var(--lf-radius-sm);
}

/* Spinner */
[data-testid="stSpinner"] { color: var(--lf-primary) !important; }

/* ── Tabs — pill style ── */
.stTabs [data-baseweb="tab-list"] {
    background: var(--lf-surface-subtle) !important;
    border-radius: var(--lf-radius-sm) !important;
    padding: .25rem !important;
    gap: 2px !important;
    border: none !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    border-radius: 6px !important;
    color: var(--lf-text-secondary) !important;
    font-size: .82rem !important;
    font-weight: 550 !important;
    padding: .4rem 1rem !important;
    border: none !important;
    outline: none !important;
    transition: background .15s, color .15s !important;
}
.stTabs [aria-selected="true"] {
    background: var(--lf-surface) !important;
    color: var(--lf-text) !important;
    box-shadow: var(--lf-shadow-sm) !important;
}
.stTabs [data-baseweb="tab"]:hover:not([aria-selected="true"]) {
    background: rgba(255,255,255,.6) !important;
    color: var(--lf-text) !important;
}
.stTabs [data-baseweb="tab-border"],
.stTabs [data-baseweb="tab-highlight"] { display: none !important; }
.stTabs [data-testid="stTabsContent"] { padding-top: var(--sp-3) !important; }

/* ── Radio — segmented control ── */
[data-testid="stRadio"] [role="radiogroup"] {
    gap: 2px !important;
    background: var(--lf-surface-subtle) !important;
    border-radius: var(--lf-radius-sm) !important;
    padding: .2rem !important;
    border: 1px solid var(--lf-border) !important;
}
[data-testid="stRadio"] [data-baseweb="radio"] > div:first-child {
    display: none !important;
}
[data-testid="stRadio"] [data-baseweb="radio"] {
    background: transparent !important;
    border-radius: 6px !important;
    padding: .25rem .7rem !important;
    cursor: pointer !important;
    transition: background .15s !important;
}
[data-testid="stRadio"] [data-baseweb="radio"]:has(input:checked) {
    background: var(--lf-surface) !important;
    box-shadow: var(--lf-shadow-sm) !important;
}
[data-testid="stRadio"] label p { font-size: .82rem !important; font-weight: 550 !important; color: var(--lf-text-secondary) !important; }
[data-testid="stRadio"] [data-baseweb="radio"]:has(input:checked) label p { color: var(--lf-text) !important; }

/* ── Form inside expander — remove double border ── */
[data-testid="stExpander"] [data-testid="stForm"] {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: .5rem 0 !important;
}

/* ── Alerts — couleurs douces, typées, cohérentes avec la palette ── */
[data-testid="stAlert"] {
    border-radius: var(--lf-radius-sm) !important;
    font-size: .84rem !important;
    border-left-width: 3px !important;
    padding: .65rem 1rem !important;
    margin-bottom: var(--sp-2) !important;
    box-shadow: none !important;
}
[data-testid="stAlert"] p { font-size: .84rem !important; color: inherit !important; }
/* Info */
[data-testid="stAlert"][data-baseweb="notification"][kind="info"],
div.stAlert > div[data-baseweb="notification"] {
    background: var(--lf-info-bg) !important;
    border-color: var(--lf-info) !important;
}
/* Warning */
div.stAlert > div[kind="warning"] {
    background: var(--lf-warning-bg) !important;
    border-color: var(--lf-warning) !important;
}
/* Error */
div.stAlert > div[kind="error"] {
    background: var(--lf-error-bg) !important;
    border-color: var(--lf-error) !important;
}
/* Success */
div.stAlert > div[kind="success"] {
    background: var(--lf-success-bg) !important;
    border-color: var(--lf-success) !important;
}

/* ── Conteneur de défilement horizontal pour tableaux larges (mobile) ── */
.table-scroll { overflow-x: auto; -webkit-overflow-scrolling: touch; }

/* ══════════════════════════════════════════════════════════════════════
   RESPONSIVE — ajustements ciblés, sans réempiler les colonnes Streamlit
   ══════════════════════════════════════════════════════════════════════ */
@media (max-width: 900px) {
    .main .block-container { padding: var(--sp-4) 1.1rem 2.5rem 1.1rem !important; }
    .hero { padding: 1.25rem 1.4rem; }
    .hero-amount { font-size: 1.85rem; }
    .hero-meta { gap: 1.1rem; flex-wrap: wrap; row-gap: .6rem; }
    .pg-ttl { font-size: 1.2rem; }
    .kpi-val { font-size: 1.25rem; }
    .obj-pct { font-size: 1.4rem; }
}
@media (max-width: 640px) {
    .main .block-container { padding: .75rem .75rem 2rem .75rem !important; }
    .hero { padding: 1rem 1.1rem; border-radius: var(--lf-radius-md); }
    .hero-amount { font-size: 1.5rem; }
    .hero-chip { font-size: .64rem; }
    .hero-meta { gap: .9rem; }
    .hero-meta-val { font-size: .82rem; }
    .kpi { padding: .85rem 1rem .8rem 1rem; }
    .kpi-val { font-size: 1.1rem; }
    .card, .obj-card { padding: 1rem 1.1rem; }
    .pg-ttl { font-size: 1.08rem; }
    .sec-ttl { font-size: .74rem; }
    /* En dessous de 640px, st.columns() empile ses colonnes verticalement —
       une ligne d'en-têtes ("Date", "Montant"…) perd alors tout lien visuel
       avec les valeurs qui s'affichent bien plus bas. Chaque ligne (date,
       badge, montant, commentaire) reste lisible seule, donc on masque
       l'en-tête plutôt que de laisser un en-tête orphelin en haut de liste. */
    .th { display: none; }
    .row-amount, .row-comment.num { text-align: left; }
}
</style>
""",
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# COMPOSANTS HTML
# ══════════════════════════════════════════════════════════════════════════════

def kpi_card(
    label: str,
    value: str,
    sub: str = "",
    color: str = "blue",
    icon: str = "",
    size: str = "md",
) -> str:
    """size="lg" marque un KPI de premier plan (valeur plus grande, icône plus
    grande) — pour distinguer visuellement le chiffre le plus important d'une
    rangée de KPI secondaires, plutôt qu'une collection de cartes identiques."""
    accent, bg_light, _ = _ACCENT.get(color, _ACCENT["blue"])
    icon_html = (
        f'<div class="kpi-ico" style="--ka-bg:{bg_light}">{icon}</div>'
        if icon else ""
    )
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    size_cls = " kpi-lg" if size == "lg" else ""
    return (
        f'<div class="kpi{size_cls}" style="--ka:{accent}">'
        f'  <div class="kpi-hdr">'
        f'    <div class="kpi-lbl">{label}</div>'
        f'    {icon_html}'
        f'  </div>'
        f'  <div class="kpi-val">{value}</div>'
        f'  {sub_html}'
        f'</div>'
    )


def sidebar_brand() -> str:
    """Marque Legend Farm affichée en tête de la sidebar, au-dessus de la navigation."""
    return (
        '<div class="lf-brand">'
        '  <div class="lf-brand-mark">LF</div>'
        '  <div>'
        f'    <div class="lf-brand-name">{PROJECT_NAME}</div>'
        '    <div class="lf-brand-tag">Suivi de capital</div>'
        '  </div>'
        '</div>'
    )


def page_header(title: str, icon: str = "", description: str = "", badge: str = "") -> str:
    icon_html  = f'{icon} ' if icon else ""
    badge_html = f'<span class="pg-badge">{badge}</span>' if badge else ""
    desc_html  = f'<div class="pg-desc">{description}</div>' if description else ""
    return (
        f'<div class="pg-hdr">'
        f'  <div class="pg-hdr-top">'
        f'    <div class="pg-ttl">{icon_html}{title}</div>'
        f'    {badge_html}'
        f'  </div>'
        f'  {desc_html}'
        f'  <div class="pg-line"></div>'
        f'</div>'
    )


def hero_banner(
    capital_gnf: float,
    pct_global: float,
    nb_investisseurs: int,
    nb_mouvements: int,
) -> str:
    gnf_str  = fmt_gnf(capital_gnf)
    pct_str  = fmt_pct(pct_global)
    return (
        f'<div class="hero">'
        f'  <div class="hero-chip">🌱 {PROJECT_NAME}</div>'
        f'  <div style="font-size:.72rem;font-weight:800;text-transform:uppercase;'
        f'letter-spacing:.12em;color:rgba(255,255,255,.72);margin:.65rem 0 .15rem 0">'
        f'Capital total valorisé</div>'
        f'  <div class="hero-amount">{gnf_str}</div>'
        f'  <div class="hero-sub">Progression vers l\'objectif de 500&thinsp;000&thinsp;000 GNF</div>'
        f'  <div class="hero-meta">'
        f'    <div class="hero-meta-item">'
        f'      <div class="hero-meta-lbl">Progression</div>'
        f'      <div class="hero-meta-val">{pct_str}</div>'
        f'    </div>'
        f'    <div class="hero-meta-item">'
        f'      <div class="hero-meta-lbl">Investisseurs</div>'
        f'      <div class="hero-meta-val">{nb_investisseurs}</div>'
        f'    </div>'
        f'    <div class="hero-meta-item">'
        f'      <div class="hero-meta-lbl">Mouvements</div>'
        f'      <div class="hero-meta-val">{nb_mouvements}</div>'
        f'    </div>'
        f'  </div>'
        f'</div>'
    )


def section_header(title: str, icon: str = "", color: str = "#2563EB") -> str:
    icon_html = f'{icon} ' if icon else ""
    return (
        f'<div class="sec-hdr">'
        f'  <div class="sec-bar" style="--sb:{color}"></div>'
        f'  <div class="sec-ttl">{icon_html}{title}</div>'
        f'  <div class="sec-line"></div>'
        f'</div>'
    )


def empty_state(icon: str, title: str, description: str = "") -> str:
    desc_html = f'<div class="empty-state-desc">{description}</div>' if description else ""
    return (
        f'<div class="empty-state">'
        f'  <div class="empty-state-icon">{icon}</div>'
        f'  <div class="empty-state-title">{title}</div>'
        f'  {desc_html}'
        f'</div>'
    )


def badge_mouvement(type_mvt: str, label: str | None = None) -> str:
    """
    label : texte affiché dans le badge. Si None, utilise LABELS_MOUVEMENT[type_mvt].
    type_mvt détermine toujours la couleur et l'emoji.
    """
    colors   = COULEUR_BADGE_MOUVEMENT.get(type_mvt, ("#374151", "#F3F4F6"))
    emoji    = EMOJI_MOUVEMENT.get(type_mvt, "")
    txt      = label if label is not None else LABELS_MOUVEMENT.get(type_mvt, type_mvt)
    return (
        f'<span class="badge" style="color:{colors[0]};background:{colors[1]}">'
        f'{emoji}&nbsp;{txt}'
        f'</span>'
    )


def progress_bar(pct: float, color: str = "blue", height: str = "7px") -> str:
    pct_c = max(0.0, min(100.0, pct))
    if color == "auto":
        color = "green" if pct_c >= 100 else ("blue" if pct_c >= 50 else "amber")
    return (
        f'<div class="prog" style="height:{height}">'
        f'<div class="prog-fill {color}" style="width:{pct_c:.1f}%"></div>'
        f'</div>'
    )


def progress_labeled(
    pct: float, label_left: str = "", label_right: str = "", color: str = "auto"
) -> str:
    pct_c = max(0.0, min(100.0, pct))
    if color == "auto":
        color = "green" if pct_c >= 100 else ("blue" if pct_c >= 50 else "amber")
    row = ""
    if label_left or label_right:
        row = (
            f'<div style="display:flex;justify-content:space-between;'
            f'margin-bottom:.25rem;font-size:.7rem;font-weight:600;color:#64748B">'
            f'<span>{label_left}</span><span>{label_right}</span></div>'
        )
    return row + progress_bar(pct_c, color)


def stat_row(label: str, value: str, color: str = "var(--lf-text)") -> str:
    return (
        f'<div style="display:flex;justify-content:space-between;'
        f'align-items:center;padding:.45rem 0;'
        f'border-bottom:1px solid var(--lf-border-subtle)">'
        f'<span style="font-size:.8rem;color:var(--lf-text-secondary);font-weight:500">{label}</span>'
        f'<span style="font-size:.84rem;font-weight:650;color:{color}">{value}</span>'
        f'</div>'
    )


def form_step(n: int, label: str, first: bool = False) -> str:
    """Marqueur d'étape numéroté pour les gros formulaires (Mouvements, Dépenses) —
    regroupe visuellement les champs d'une même intention sans avoir à imbriquer
    les widgets Streamlit dans des conteneurs (risqué sur un formulaire à logique
    conditionnelle complexe). Le numéro + la ligne de séparation jouent le rôle
    d'une frontière de section, à la place d'une simple étiquette de texte."""
    top = "" if first else 'margin-top:1.35rem;padding-top:1.1rem;border-top:1px solid var(--lf-border-subtle);'
    return (
        f'<div style="display:flex;align-items:center;gap:.5rem;{top}margin-bottom:.6rem">'
        f'  <div style="width:20px;height:20px;border-radius:999px;background:var(--lf-primary-subtle);'
        f'color:var(--lf-primary-hover);font-size:.68rem;font-weight:700;display:flex;'
        f'align-items:center;justify-content:center;flex-shrink:0">{n}</div>'
        f'  <div style="font-size:.82rem;font-weight:650;color:var(--lf-text)">{label}</div>'
        f'</div>'
    )


def divider() -> str:
    return '<hr style="border:none;border-top:1px solid var(--lf-border);margin:1rem 0">'


def spacer(h: str = "0.75rem") -> str:
    return f'<div style="height:{h}"></div>'


def summary_bar(items: list[tuple[str, str, str]]) -> str:
    """Barre de résumé financier. items = [(label, value, color_key), ...]"""
    cells = ""
    for i, (label, value, color) in enumerate(items):
        accent, bg, _ = _ACCENT.get(color, _ACCENT["slate"])
        sep = '<div style="width:1px;background:var(--lf-border);align-self:stretch;flex-shrink:0"></div>' if i > 0 else ""
        cells += (
            f'{sep}'
            f'<div style="flex:1;padding:.85rem 1.25rem">'
            f'  <div style="font-size:.72rem;font-weight:600;text-transform:none;'
            f'letter-spacing:0;color:var(--lf-text-muted);margin-bottom:.3rem">{label}</div>'
            f'  <div style="font-size:.98rem;font-weight:700;color:{accent};letter-spacing:-.01em;font-variant-numeric:tabular-nums">{value}</div>'
            f'</div>'
        )
    return (
        f'<div style="background:var(--lf-surface);border:1px solid var(--lf-border);border-radius:var(--lf-radius-md);'
        f'box-shadow:var(--lf-shadow-sm);display:flex;overflow:hidden">'
        f'{cells}'
        f'</div>'
    )


def preview_card(
    title: str,
    rows: list[tuple[str, str, str]],
    color: str = "blue",
    footer: str = "",
) -> str:
    """Carte de prévisualisation structurée. rows = [(label, value, color_key), ...]"""
    accent, bg, border = _ACCENT.get(color, _ACCENT["blue"])
    rows_html = ""
    for label, value, val_color in rows:
        vc = _ACCENT.get(val_color, _ACCENT["slate"])[0] if val_color else "var(--lf-text)"
        rows_html += (
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'padding:.4rem 0;border-bottom:1px solid {bg}">'
            f'<span style="font-size:.8rem;color:var(--lf-text-secondary);font-weight:500">{label}</span>'
            f'<span style="font-size:.86rem;font-weight:650;color:{vc};font-variant-numeric:tabular-nums">{value}</span>'
            f'</div>'
        )
    footer_html = (
        f'<div style="margin-top:.5rem;font-size:.76rem;color:{accent};font-weight:600">{footer}</div>'
        if footer else ""
    )
    return (
        f'<div style="background:{bg};border:1.5px solid {border};border-radius:var(--lf-radius-md);'
        f'padding:.9rem 1.1rem;margin-top:.5rem">'
        f'<div style="font-size:.76rem;font-weight:650;text-transform:none;letter-spacing:0;'
        f'color:{accent};margin-bottom:.5rem">{title}</div>'
        f'{rows_html}'
        f'{footer_html}'
        f'</div>'
    )


def cat_card(
    icon: str,
    name: str,
    description: str,
    montant: str,
    nb: int,
    pct: float,
    color: str = "blue",
    status: str = "",
    status_color: str = "green",
) -> str:
    """Carte catégorie dépenses."""
    accent, bg, border = _ACCENT.get(color, _ACCENT["blue"])
    sc, sbg, _ = _ACCENT.get(status_color, _ACCENT["green"])
    status_html = (
        f'<span style="font-size:.62rem;font-weight:700;background:{sbg};color:{sc};'
        f'padding:.15rem .45rem;border-radius:999px">{status}</span>'
        if status else ""
    )
    pct_c = max(0.0, min(100.0, pct))
    return (
        f'<div class="card" style="padding:.9rem 1.1rem;margin-bottom:.5rem">'
        f'<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:.5rem">'
        f'  <div style="display:flex;align-items:center;gap:.55rem">'
        f'    <div style="font-size:1.3rem;line-height:1">{icon}</div>'
        f'    <div>'
        f'      <div style="font-size:.88rem;font-weight:650;color:var(--lf-text);line-height:1.2">{name}</div>'
        f'      <div style="font-size:.7rem;color:var(--lf-text-muted);margin-top:.1rem;max-width:200px;line-height:1.35">{description[:55]}</div>'
        f'    </div>'
        f'  </div>'
        f'  <div style="text-align:right;flex-shrink:0;margin-left:.75rem">'
        f'    <div style="font-size:.9rem;font-weight:700;color:var(--lf-text);font-variant-numeric:tabular-nums">{montant}</div>'
        f'    <div style="font-size:.68rem;color:var(--lf-text-muted)">{nb} dépense{"s" if nb != 1 else ""}</div>'
        f'  </div>'
        f'</div>'
        f'<div style="background:var(--lf-surface-subtle);border-radius:999px;height:5px;overflow:hidden;margin-bottom:.35rem">'
        f'  <div style="background:{accent};width:{pct_c:.1f}%;height:100%;border-radius:999px"></div>'
        f'</div>'
        f'<div style="display:flex;justify-content:space-between;align-items:center">'
        f'  <span style="font-size:.68rem;color:var(--lf-text-muted)">{pct_c:.1f}% du total</span>'
        f'  {status_html}'
        f'</div>'
        f'</div>'
    )


# ══════════════════════════════════════════════════════════════════════════════
# COMPOSANTS INTERACTIFS (actions à risque, pagination)
# ══════════════════════════════════════════════════════════════════════════════

def attention_panel(items: list[tuple[str, str, str, str]]) -> str:
    """Panneau compact "Nécessite votre attention". items = [(icon, titre, détail, color_key)],
    color_key référence la palette _ACCENT. Si la liste est vide, affiche un état positif
    discret plutôt qu'un bloc vide.
    """
    if not items:
        return (
            '<div style="background:var(--lf-success-bg);border:1px solid var(--lf-success);border-radius:var(--lf-radius-md);'
            'padding:.7rem 1.1rem;font-size:.84rem;color:var(--lf-success);font-weight:600;'
            'display:flex;align-items:center;gap:.5rem">'
            '✓ Rien ne nécessite votre attention pour le moment.'
            '</div>'
        )
    rows = ""
    for icon, titre, detail, color in items:
        accent, bg, border = _ACCENT.get(color, _ACCENT["amber"])
        rows += (
            f'<div style="display:flex;align-items:center;gap:.7rem;padding:.55rem .8rem;'
            f'background:{bg};border:1px solid {border};border-radius:var(--lf-radius-sm);margin-bottom:.4rem">'
            f'<div style="font-size:1rem;flex-shrink:0">{icon}</div>'
            f'<div style="flex:1;min-width:0">'
            f'<div style="font-size:.83rem;font-weight:650;color:{accent}">{titre}</div>'
            f'<div style="font-size:.74rem;color:var(--lf-text-secondary)">{detail}</div>'
            f'</div>'
            f'</div>'
        )
    return f'<div>{rows}</div>'


def confirm_delete(item_key: str, description: str = "cet élément", icon: str = "🗑️") -> bool:
    """Bouton de suppression à confirmation explicite, en 2 clics, sans popup.

    Premier clic : affiche un message de confirmation avec deux actions claires
    (Annuler mis en avant, Oui secondaire). Ne renvoie True qu'au moment précis
    où l'utilisateur confirme réellement — jamais sur le premier clic.
    """
    flag_key = f"_confirm_del_{item_key}"
    if st.session_state.get(flag_key):
        st.markdown(
            f'<div style="font-size:.72rem;color:var(--lf-error);font-weight:650;margin-bottom:.3rem;line-height:1.35">'
            f'Supprimer {description} ?</div>',
            unsafe_allow_html=True,
        )
        cc1, cc2 = st.columns(2)
        with cc1:
            cancel = st.button("Annuler", key=f"{item_key}_cancel", type="primary", use_container_width=True)
        with cc2:
            confirm = st.button("Oui", key=f"{item_key}_confirm", type="secondary", use_container_width=True)
        if cancel:
            st.session_state[flag_key] = False
            st.rerun()
        if confirm:
            st.session_state[flag_key] = False
            return True
        return False

    if st.button(icon, key=f"{item_key}_trigger", help="Supprimer"):
        st.session_state[flag_key] = True
        st.rerun()
    return False


def paginate(df, key: str, page_size: int = 20):
    """Découpe un DataFrame déjà trié/filtré en pages et affiche les contrôles
    précédent/suivant (avec indicateur de page et nombre total de résultats).
    Ne rend aucun contrôle si tout tient sur une seule page. Renvoie la tranche
    de lignes correspondant à la page courante — les filtres s'appliquent avant,
    sur le DataFrame complet passé en entrée.
    """
    total = len(df)
    if total <= page_size:
        return df

    total_pages = -(-total // page_size)  # ceil
    page_key = f"_page_{key}"
    page = int(st.session_state.get(page_key, 1))
    page = max(1, min(page, total_pages))

    pc1, pc2, pc3 = st.columns([1, 2, 1])
    with pc1:
        prev_clicked = st.button("← Précédent", key=f"{key}_prev", disabled=(page <= 1), use_container_width=True)
    with pc3:
        next_clicked = st.button("Suivant →", key=f"{key}_next", disabled=(page >= total_pages), use_container_width=True)

    # Les deux clics sont résolus avant l'affichage du libellé, pour que "Page X / Y"
    # reflète toujours la page réellement sélectionnée dans ce même rendu (et pas
    # celle d'avant le clic sur "Suivant").
    if prev_clicked:
        page -= 1
    if next_clicked:
        page += 1

    with pc2:
        st.markdown(
            f'<div style="text-align:center;font-size:.8rem;color:var(--lf-text-secondary);font-weight:550;padding-top:.5rem">'
            f'Page {page} / {total_pages} — {total} résultat(s)</div>',
            unsafe_allow_html=True,
        )

    st.session_state[page_key] = page
    start = (page - 1) * page_size
    return df.iloc[start:start + page_size]
