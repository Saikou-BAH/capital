"""
Design system — composants HTML/CSS premium.
Style inspiré de Legend Farm : propre, aéré, cartes soignées, premium.
Adapté à un usage financier / suivi de capital : sobre, rassurant, SaaS.
"""

import streamlit as st
from utils.config import COULEUR_BADGE_MOUVEMENT, EMOJI_MOUVEMENT

# ── Palette ───────────────────────────────────────────────────────────────────
_ACCENT = {
    "blue":   ("#2563EB", "#EFF6FF", "#BFDBFE"),
    "green":  ("#059669", "#ECFDF5", "#A7F3D0"),
    "amber":  ("#D97706", "#FFFBEB", "#FDE68A"),
    "red":    ("#DC2626", "#FEF2F2", "#FECACA"),
    "violet": ("#7C3AED", "#F5F3FF", "#DDD6FE"),
    "slate":  ("#475569", "#F8FAFC", "#CBD5E1"),
}

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
# CSS GLOBAL
# ══════════════════════════════════════════════════════════════════════════════

def inject_css():
    st.markdown(
        """
<style>
/* ── Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,300;0,14..32,400;0,14..32,500;0,14..32,600;0,14..32,700;0,14..32,800;0,14..32,900&display=swap');

*, *::before, *::after { box-sizing: border-box; }

html, body, [class*="css"], .stApp {
    font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
    -webkit-font-smoothing: antialiased !important;
    -moz-osx-font-smoothing: grayscale !important;
}

/* ── Streamlit chrome ── */
#MainMenu, footer, [data-testid="stDecoration"],
[data-testid="stToolbar"], header { visibility: hidden !important; }

/* ── App background ── */
.stApp { background: #F0F4F8 !important; }
.main  { background: #F0F4F8 !important; }

/* ── Main block ── */
.main .block-container {
    padding: 1.5rem 2.25rem 3rem 2.25rem !important;
    max-width: 1500px !important;
}

/* ── Headings ── */
h1 { font-size: 1.6rem !important; font-weight: 800 !important;
     letter-spacing: -0.03em !important; color: #0F172A !important; margin: 0 !important; }
h2 { font-size: 1.1rem !important; font-weight: 700 !important; color: #1E293B !important; }
h3 { font-size: .95rem !important; font-weight: 600 !important; color: #334155 !important; }
p  { color: #475569 !important; font-size: .875rem !important; }

/* ── Sidebar premium ── */
section[data-testid="stSidebar"] {
    background: #0F172A !important;
    border-right: 1px solid rgba(255,255,255,0.06) !important;
    min-width: 240px !important;
}
section[data-testid="stSidebar"] > div { background: transparent !important; }
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] small { color: #94A3B8 !important; font-size: .82rem !important; }
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 { color: #F1F5F9 !important; }

/* Sidebar nav */
[data-testid="stSidebarNav"] { padding: .5rem 0 !important; }
[data-testid="stSidebarNav"] a {
    display: flex !important;
    align-items: center !important;
    gap: .5rem !important;
    border-radius: 8px !important;
    padding: .5rem .85rem !important;
    margin: 1px .5rem !important;
    color: #94A3B8 !important;
    font-size: .82rem !important;
    font-weight: 500 !important;
    text-decoration: none !important;
    transition: background .15s, color .15s !important;
}
[data-testid="stSidebarNav"] a:hover {
    background: rgba(255,255,255,.07) !important;
    color: #E2E8F0 !important;
}
[data-testid="stSidebarNav"] a[aria-selected="true"] {
    background: rgba(37,99,235,.2) !important;
    color: #93C5FD !important;
    font-weight: 600 !important;
    box-shadow: inset 3px 0 0 #3B82F6 !important;
}
[data-testid="stSidebarNavSeparator"] { border-color: rgba(255,255,255,.06) !important; }

/* ── Page title area (h2 on each page) ── */
.stApp .main .block-container h2:first-of-type {
    font-size: 1.35rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.025em !important;
    color: #0F172A !important;
}

/* ── HR ── */
hr {
    border: none !important;
    border-top: 1px solid #E2E8F0 !important;
    margin: 1rem 0 !important;
}

/* ── Cards ── */
.card {
    background: #fff;
    border: 1px solid #E2E8F0;
    border-radius: 14px;
    box-shadow: 0 1px 3px rgba(15,23,42,.04), 0 1px 2px rgba(15,23,42,.03);
    padding: 1.5rem;
    transition: box-shadow .2s, transform .2s;
}
.card:hover {
    box-shadow: 0 4px 16px rgba(15,23,42,.08);
    transform: translateY(-1px);
}

/* ── KPI cards ── */
.kpi {
    background: #fff;
    border: 1px solid #E2E8F0;
    border-radius: 14px;
    box-shadow: 0 1px 3px rgba(15,23,42,.04);
    padding: 1.1rem 1.25rem 1rem 1.25rem;
    position: relative;
    overflow: hidden;
    transition: box-shadow .2s, transform .2s;
    margin-bottom: .5rem;
}
.kpi::after {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: var(--ka, #2563EB);
}
.kpi:hover {
    box-shadow: 0 6px 20px rgba(15,23,42,.09);
    transform: translateY(-1px);
}
.kpi-hdr { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: .55rem; }
.kpi-lbl {
    font-size: .65rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: .1em; color: #94A3B8;
}
.kpi-ico {
    width: 34px; height: 34px;
    background: var(--ka-bg, #EFF6FF);
    border-radius: 9px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1rem;
    flex-shrink: 0;
}
.kpi-val {
    font-size: 1.45rem; font-weight: 800; color: #0F172A;
    letter-spacing: -0.02em; line-height: 1.1;
    font-variant-numeric: tabular-nums;
}
.kpi-sub {
    font-size: .7rem; color: #94A3B8; font-weight: 500;
    margin-top: .35rem; line-height: 1.4;
}

/* ── Section header (Legend Farm style) ── */
.sec-hdr {
    display: flex; align-items: center; gap: .55rem;
    margin: 1.6rem 0 .9rem 0;
}
.sec-bar {
    width: 3px; height: 14px;
    background: var(--sb, #2563EB);
    border-radius: 2px; flex-shrink: 0;
}
.sec-ttl {
    font-size: .72rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: .1em;
    color: #475569;
}
.sec-line {
    flex: 1; height: 1px;
    background: linear-gradient(90deg, #E2E8F0 0%, transparent 80%);
}

/* ── Page header ── */
.pg-hdr { margin-bottom: 1.25rem; }
.pg-hdr-top { display: flex; align-items: baseline; gap: .6rem; margin-bottom: .2rem; }
.pg-ttl {
    font-size: 1.45rem; font-weight: 800; color: #0F172A;
    letter-spacing: -0.03em;
}
.pg-badge {
    font-size: .65rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: .08em; color: #2563EB;
    background: #EFF6FF; border-radius: 20px;
    padding: .15rem .55rem;
}
.pg-desc { font-size: .82rem; color: #64748B; font-weight: 500; margin-bottom: .65rem; }
.pg-line {
    height: 1px;
    background: linear-gradient(90deg, #E2E8F0 0%, rgba(37,99,235,.18) 30%, #E2E8F0 100%);
}

/* ── Hero banner ── */
.hero {
    background: linear-gradient(135deg, #0F2451 0%, #1E3A8A 55%, #2563EB 100%);
    border-radius: 16px;
    padding: 1.75rem 2rem;
    color: #fff;
    position: relative;
    overflow: hidden;
    box-shadow: 0 8px 32px rgba(37,99,235,.22), 0 2px 8px rgba(15,23,42,.12);
}
.hero::before {
    content: ''; position: absolute;
    top: -90px; right: -50px;
    width: 300px; height: 300px;
    background: rgba(255,255,255,.05); border-radius: 50%;
}
.hero::after {
    content: ''; position: absolute;
    bottom: -80px; right: 130px;
    width: 180px; height: 180px;
    background: rgba(255,255,255,.04); border-radius: 50%;
}
.hero-chip {
    display: inline-flex; align-items: center; gap: .3rem;
    background: rgba(255,255,255,.12);
    border: 1px solid rgba(255,255,255,.18);
    border-radius: 20px; padding: .2rem .65rem;
    font-size: .67rem; font-weight: 700;
    letter-spacing: .06em; text-transform: uppercase;
    color: rgba(255,255,255,.8); margin-bottom: .7rem;
}
.hero-amount {
    font-size: 2.5rem; font-weight: 900;
    letter-spacing: -.04em; line-height: 1;
    margin-bottom: .25rem;
}
.hero-sub { font-size: .8rem; color: rgba(255,255,255,.6); font-weight: 500; }
.hero-meta {
    display: flex; gap: 1.5rem;
    margin-top: 1.1rem; padding-top: .9rem;
    border-top: 1px solid rgba(255,255,255,.12);
}
.hero-meta-item { display: flex; flex-direction: column; }
.hero-meta-lbl {
    font-size: .62rem; font-weight: 600;
    text-transform: uppercase; letter-spacing: .08em;
    color: rgba(255,255,255,.45); margin-bottom: .1rem;
}
.hero-meta-val { font-size: .88rem; font-weight: 700; color: rgba(255,255,255,.9); }

/* ── Progress bars ── */
.prog { background: #F1F5F9; border-radius: 999px; height: 7px; overflow: hidden; margin: .2rem 0; }
.prog-fill {
    height: 100%; border-radius: 999px;
    background: #2563EB; position: relative;
    transition: width .4s cubic-bezier(.4,0,.2,1);
}
.prog-fill::after {
    content: ''; position: absolute; inset: 0;
    background: linear-gradient(90deg, transparent 60%, rgba(255,255,255,.25));
}
.prog-fill.green  { background: #059669; }
.prog-fill.amber  { background: #D97706; }
.prog-fill.red    { background: #DC2626; }
.prog-fill.violet { background: #7C3AED; }

/* ── Badge mouvement ── */
.badge {
    display: inline-flex; align-items: center; gap: .25rem;
    padding: .18rem .5rem; border-radius: 6px;
    font-size: .65rem; font-weight: 700;
    letter-spacing: .05em; text-transform: uppercase;
    white-space: nowrap;
}

/* ── Table ── */
.th {
    font-size: .65rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: .09em; color: #94A3B8;
    padding-bottom: .35rem;
}
.row-date   { font-size: .78rem; font-weight: 600; color: #64748B; }
.row-amount { font-size: .9rem; font-weight: 700; color: #0F172A; }
.row-comment{ font-size: .74rem; color: #94A3B8; line-height: 1.4; }

/* ── Obj card ── */
.obj-card {
    background: #fff; border: 1px solid #E2E8F0;
    border-radius: 14px; padding: 1.3rem 1.5rem;
    box-shadow: 0 1px 3px rgba(15,23,42,.04);
    margin-bottom: .75rem;
}
.obj-card-title { font-size: .95rem; font-weight: 700; color: #0F172A;
                  letter-spacing: -.01em; margin-bottom: .15rem; }
.obj-card-desc  { font-size: .76rem; color: #94A3B8; margin-bottom: .75rem; }
.obj-pct {
    font-size: 1.75rem; font-weight: 900;
    letter-spacing: -.03em; color: #0F172A; line-height: 1;
}

/* ── Empty state ── */
.empty-state {
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    padding: 3.5rem 2rem; text-align: center;
    background: #fff; border: 1.5px dashed #CBD5E1;
    border-radius: 14px; color: #94A3B8;
}
.empty-state-icon { font-size: 2.4rem; margin-bottom: .75rem; opacity: .7; }
.empty-state-title { font-size: .95rem; font-weight: 700; color: #475569; margin-bottom: .35rem; }
.empty-state-desc  { font-size: .8rem; color: #94A3B8; max-width: 340px; }

/* ── Streamlit inputs ── */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stDateInput"] input {
    border-radius: 8px !important;
    border: 1px solid #CBD5E1 !important;
    font-size: .875rem !important;
    background: #FAFBFC !important;
    color: #1E293B !important;
    transition: border-color .15s, box-shadow .15s !important;
    padding: .5rem .75rem !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus,
[data-testid="stDateInput"] input:focus {
    border-color: #2563EB !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,.1) !important;
    background: #fff !important;
    outline: none !important;
}
[data-testid="stTextArea"] textarea {
    border-radius: 8px !important;
    border: 1px solid #CBD5E1 !important;
    font-size: .875rem !important;
    background: #FAFBFC !important;
    color: #1E293B !important;
    resize: vertical !important;
}
[data-testid="stTextArea"] textarea:focus {
    border-color: #2563EB !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,.1) !important;
    background: #fff !important;
}

/* Labels */
label, [data-testid="stWidgetLabel"] p {
    font-size: .78rem !important;
    font-weight: 600 !important;
    color: #374151 !important;
    letter-spacing: .01em !important;
    margin-bottom: .2rem !important;
}

/* Buttons */
.stButton > button, .stDownloadButton > button {
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: .83rem !important;
    padding: .5rem 1.25rem !important;
    transition: all .15s !important;
    letter-spacing: .01em !important;
}
button[kind="primary"] {
    background: #2563EB !important;
    border-color: #2563EB !important;
    color: #fff !important;
    box-shadow: 0 1px 3px rgba(37,99,235,.35) !important;
}
button[kind="primary"]:hover {
    background: #1D4ED8 !important;
    box-shadow: 0 4px 14px rgba(37,99,235,.45) !important;
    transform: translateY(-1px);
}
button[kind="secondary"] {
    background: #F8FAFC !important;
    border-color: #CBD5E1 !important;
    color: #475569 !important;
}
button[kind="secondary"]:hover {
    background: #F1F5F9 !important;
    border-color: #94A3B8 !important;
}

/* Selectbox */
[data-testid="stSelectbox"] > div > div,
[data-baseweb="select"] > div:first-child {
    border-radius: 8px !important;
    border-color: #CBD5E1 !important;
    font-size: .875rem !important;
    background: #FAFBFC !important;
    color: #1E293B !important;
}
[data-baseweb="tag"] {
    background: #EFF6FF !important;
    border-radius: 5px !important;
}
[data-baseweb="tag"] span { color: #1D4ED8 !important; font-weight: 600 !important; }

/* Expander */
[data-testid="stExpander"] details {
    border-radius: 10px !important;
    border: 1px solid #E2E8F0 !important;
    background: #fff !important;
}
[data-testid="stExpander"] summary {
    font-size: .85rem !important;
    font-weight: 600 !important;
    color: #334155 !important;
    padding: .7rem 1rem !important;
}
[data-testid="stExpander"] summary:hover { background: #F8FAFC !important; }

/* Alerts */
[data-testid="stAlert"] {
    border-radius: 10px !important;
    font-size: .84rem !important;
    border-width: 1px !important;
    border-left-width: 3px !important;
}

/* Metrics */
[data-testid="stMetric"] {
    background: #fff; border: 1px solid #E2E8F0;
    border-radius: 12px; padding: 1rem 1.2rem !important;
}
[data-testid="stMetricLabel"] p {
    font-size: .68rem !important; font-weight: 700 !important;
    text-transform: uppercase; letter-spacing: .09em; color: #94A3B8 !important;
}
[data-testid="stMetricValue"] {
    font-size: 1.35rem !important; font-weight: 800 !important;
    color: #0F172A !important; letter-spacing: -.02em !important;
}

/* Checkbox */
[data-testid="stCheckbox"] label p {
    font-size: .84rem !important; color: #374151 !important;
}

/* Form container */
[data-testid="stForm"] {
    background: #fff;
    border: 1px solid #E2E8F0;
    border-radius: 14px;
    padding: 1.5rem !important;
    box-shadow: 0 1px 3px rgba(15,23,42,.04);
}

/* Column gap */
[data-testid="column"] { gap: 0 !important; }

/* Plotly chart container */
.stPlotlyChart > div {
    border-radius: 12px;
}

/* Spinner */
[data-testid="stSpinner"] { color: #2563EB !important; }
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
) -> str:
    accent, bg_light, _ = _ACCENT.get(color, _ACCENT["blue"])
    icon_html = (
        f'<div class="kpi-ico" style="--ka-bg:{bg_light}">{icon}</div>'
        if icon else ""
    )
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    return (
        f'<div class="kpi" style="--ka:{accent}">'
        f'  <div class="kpi-hdr">'
        f'    <div class="kpi-lbl">{label}</div>'
        f'    {icon_html}'
        f'  </div>'
        f'  <div class="kpi-val">{value}</div>'
        f'  {sub_html}'
        f'</div>'
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
    dernier_taux: float,
    nb_investisseurs: int,
    nb_mouvements: int,
) -> str:
    gnf_str  = fmt_gnf(capital_gnf)
    pct_str  = fmt_pct(pct_global)
    taux_str = fmt_taux(dernier_taux)
    return (
        f'<div class="hero">'
        f'  <div class="hero-chip">🌱 Legend Farm</div>'
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
        f'      <div class="hero-meta-lbl">Taux EUR / GNF</div>'
        f'      <div class="hero-meta-val">{taux_str}</div>'
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


def badge_mouvement(type_mvt: str) -> str:
    colors = COULEUR_BADGE_MOUVEMENT.get(type_mvt, ("#374151", "#F3F4F6"))
    emoji  = EMOJI_MOUVEMENT.get(type_mvt, "")
    return (
        f'<span class="badge" style="color:{colors[0]};background:{colors[1]}">'
        f'{emoji}&nbsp;{type_mvt}'
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


def stat_row(label: str, value: str, color: str = "#0F172A") -> str:
    return (
        f'<div style="display:flex;justify-content:space-between;'
        f'align-items:center;padding:.45rem 0;'
        f'border-bottom:1px solid #F1F5F9">'
        f'<span style="font-size:.78rem;color:#64748B;font-weight:500">{label}</span>'
        f'<span style="font-size:.82rem;font-weight:700;color:{color}">{value}</span>'
        f'</div>'
    )


def divider() -> str:
    return '<hr style="border:none;border-top:1px solid #E2E8F0;margin:1rem 0">'


def spacer(h: str = "0.75rem") -> str:
    return f'<div style="height:{h}"></div>'
