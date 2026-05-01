"""Graphiques Plotly — thème premium, cohérent avec le design system."""

import plotly.graph_objects as go
import pandas as pd
from utils.config import COULEURS_CHART, COULEUR_PRIMAIRE, CAPITAL_CIBLE_GNF
from utils.formatting import fmt_gnf

_FONT = "Inter, system-ui, sans-serif"
_GRID = "rgba(226,232,240,0.7)"
_BG   = "rgba(0,0,0,0)"

_BASE = dict(
    paper_bgcolor=_BG,
    plot_bgcolor=_BG,
    font=dict(family=_FONT, color="#64748B", size=11),
    margin=dict(l=8, r=8, t=36, b=12),
    legend=dict(
        orientation="h", yanchor="bottom", y=-0.28, xanchor="center", x=0.5,
        font=dict(size=10, color="#94A3B8"),
        bgcolor="rgba(0,0,0,0)",
    ),
    hoverlabel=dict(
        bgcolor="#0F172A", font_size=12, font_color="#F8FAFC",
        font_family=_FONT, bordercolor="#1E3A5F",
    ),
)


def _layout_base_without(*keys: str) -> dict:
    return {key: value for key, value in _BASE.items() if key not in keys}


def _reduce_ticks(ticks: list, max_ticks: int) -> list:
    if len(ticks) <= max_ticks:
        return ticks
    tick_series = pd.Series(pd.to_datetime(ticks))
    targets = pd.date_range(tick_series.min(), tick_series.max(), periods=max_ticks)
    selected = []
    for target in targets:
        nearest_idx = (tick_series - target).abs().sort_values().index
        for idx in nearest_idx:
            candidate = tick_series.loc[idx].to_pydatetime()
            if candidate not in selected:
                selected.append(candidate)
                break
    return sorted(selected)


def _date_tick_values(values: pd.Series | pd.Index, max_ticks: int = 4) -> list:
    ticks = pd.Series(values).dropna().drop_duplicates().sort_values().tolist()
    if len(ticks) <= max_ticks:
        return ticks

    return _reduce_ticks(ticks, max_ticks)


def _month_tick_values(values: pd.Series | pd.Index, max_ticks: int = 4) -> list:
    series = pd.Series(pd.to_datetime(values)).dropna()
    if series.empty:
        return []
    start = series.min().to_period("M").to_timestamp()
    end = series.max().to_period("M").to_timestamp()
    ticks = pd.date_range(start, end, freq="MS").to_pydatetime().tolist()
    return _reduce_ticks(ticks, max_ticks)


def _date_axis(values: pd.Series | pd.Index, tickformat: str = "%d/%m") -> dict:
    series = pd.Series(pd.to_datetime(values)).dropna()
    use_months = not series.empty and (series.max() - series.min()).days > 31
    return dict(
        **_AXIS_X,
        title=None,
        tickmode="array",
        tickvals=_month_tick_values(values) if use_months else _date_tick_values(values),
        tickformat="%b %y" if use_months else tickformat,
        tickangle=-25,
        automargin=True,
    )

_AXIS_X = dict(
    showgrid=False, zeroline=False,
    tickfont=dict(size=10, color="#94A3B8"),
    linecolor="#E2E8F0", linewidth=1,
)
_AXIS_Y = dict(
    showgrid=True, gridcolor=_GRID, gridwidth=1, zeroline=False,
    tickfont=dict(size=10, color="#94A3B8"),
    linecolor="rgba(0,0,0,0)",
)


def chart_evolution_capital(df_evolution: pd.DataFrame) -> go.Figure:
    if df_evolution is None or df_evolution.empty:
        return _empty("Aucun mouvement enregistré")

    df = df_evolution.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.normalize()
    df = df.dropna(subset=["date"])
    if df.empty:
        return _empty("Aucun mouvement enregistré")
    tick_values = df["date"].drop_duplicates().sort_values()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["date"],
        y=df["capital_cumule"],
        mode="lines+markers",
        name="Capital",
        line=dict(color="#2563EB", width=2.5, shape="spline", smoothing=0.6),
        marker=dict(size=6, color="#2563EB", line=dict(color="#FFFFFF", width=1.5)),
        fill="tozeroy",
        fillcolor="rgba(37,99,235,0.08)",
        hovertemplate="<b>%{x|%d %b %Y}</b><br>Capital : %{y:,.0f} GNF<extra></extra>",
    ))
    fig.add_hline(
        y=CAPITAL_CIBLE_GNF,
        line=dict(color="#F43F5E", dash="dot", width=1.5),
        annotation_text="Objectif 500M",
        annotation_position="top right",
        annotation_font=dict(color="#F43F5E", size=10),
    )
    fig.update_layout(
        **_BASE,
        title=dict(text="Évolution du capital", font=dict(size=12, color="#475569", weight=700), x=0, xref="paper"),
        xaxis=_date_axis(tick_values),
        yaxis=dict(**_AXIS_Y, title=None, tickformat=","),
        height=320,
        showlegend=False,
    )
    return fig


def chart_parts_investisseurs(df_parts: pd.DataFrame) -> go.Figure:
    if df_parts is None or df_parts.empty:
        return _empty("Aucun investisseur")

    colors = COULEURS_CHART[: len(df_parts)]
    fig = go.Figure(go.Pie(
        labels=df_parts["nom"],
        values=df_parts["net_gnf"],
        hole=0.6,
        marker=dict(colors=colors, line=dict(color=_BG, width=2)),
        texttemplate="%{percent}",
        textposition="outside",
        hovertemplate="<b>%{label}</b><br>%{value:,.0f} GNF<br>%{percent}<extra></extra>",
        textinfo="percent",
    ))
    base_no_legend = {k: v for k, v in _BASE.items() if k != "legend"}
    fig.update_layout(
        **base_no_legend,
        title=dict(text="Répartition par investisseur", font=dict(size=12, color="#475569", weight=700), x=0, xref="paper"),
        showlegend=True,
        legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.02,
                    font=dict(size=10, color="#64748B"), bgcolor="rgba(0,0,0,0)"),
        height=260,
    )
    return fig


def chart_bar_investisseurs(df_parts: pd.DataFrame) -> go.Figure:
    if df_parts is None or df_parts.empty:
        return _empty("Aucun investisseur")

    df = df_parts.sort_values("net_gnf", ascending=True)
    colors = COULEURS_CHART[: len(df)]
    fig = go.Figure(go.Bar(
        x=df["net_gnf"],
        y=df["nom"],
        orientation="h",
        marker=dict(color=colors, line=dict(color="rgba(0,0,0,0)", width=0)),
        text=[fmt_gnf(v) for v in df["net_gnf"]],
        textposition="outside",
        textfont=dict(size=10, color="#475569"),
        hovertemplate="<b>%{y}</b><br>%{x:,.0f} GNF<extra></extra>",
    ))
    fig.update_layout(
        **_BASE,
        title=dict(text="Apports nets par investisseur", font=dict(size=12, color="#475569", weight=700), x=0, xref="paper"),
        xaxis=dict(**_AXIS_X, title=None, range=[0, df["net_gnf"].max() * 1.18]),
        yaxis=dict(**{k: v for k, v in _AXIS_Y.items() if k != "showgrid"}, title=None, showgrid=False),
        height=max(220, 52 * len(df)),
        showlegend=False,
    )
    return fig


def chart_apports_eur_par_investisseur(df_apports: pd.DataFrame) -> go.Figure:
    if df_apports is None or df_apports.empty:
        return _empty("Aucun apport EUR")

    df = df_apports.copy()
    df["apports_eur"] = pd.to_numeric(df["apports_eur"], errors="coerce").fillna(0)
    df = df[df["apports_eur"] > 0].sort_values("apports_eur", ascending=True)
    if df.empty:
        return _empty("Aucun apport EUR")

    fig = go.Figure(go.Bar(
        x=df["apports_eur"],
        y=df["nom"],
        orientation="h",
        marker=dict(color="#2563EB", opacity=0.85, line=dict(color="rgba(0,0,0,0)", width=0)),
        text=[f"{v:,.2f} €".replace(",", " ").replace(".", ",") for v in df["apports_eur"]],
        textposition="outside",
        textfont=dict(size=10, color="#475569"),
        customdata=df[["apports_equiv_gnf"]],
        hovertemplate="<b>%{y}</b><br>%{x:,.2f} EUR<br>Équiv. : %{customdata[0]:,.0f} GNF<extra></extra>",
    ))
    fig.update_layout(
        **_BASE,
        title=dict(text="Apports EUR par investisseur", font=dict(size=12, color="#475569", weight=700), x=0, xref="paper"),
        xaxis=dict(**_AXIS_X, title=None, range=[0, df["apports_eur"].max() * 1.18]),
        yaxis=dict(**{k: v for k, v in _AXIS_Y.items() if k != "showgrid"}, title=None, showgrid=False),
        height=max(220, 52 * len(df)),
        showlegend=False,
    )
    return fig


def chart_evolution_apports_investisseurs(df_evolution: pd.DataFrame) -> go.Figure:
    if df_evolution is None or df_evolution.empty:
        return _empty("Aucun apport")

    df = df_evolution.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.normalize()
    df["apports_eur_cumule"] = pd.to_numeric(df["apports_eur_cumule"], errors="coerce").fillna(0)
    df["apports_gnf_cumule"] = pd.to_numeric(df["apports_gnf_cumule"], errors="coerce").fillna(0)
    df = df.dropna(subset=["date"]).sort_values(["nom", "date"])
    if df.empty:
        return _empty("Aucun apport")

    fig = go.Figure()
    colors = COULEURS_CHART
    for idx, (nom, group) in enumerate(df.groupby("nom")):
        color = colors[idx % len(colors)]
        fig.add_trace(go.Scatter(
            x=group["date"],
            y=group["apports_gnf_cumule"],
            mode="lines+markers",
            name=f"{nom} · GNF",
            line=dict(color=color, width=2.5),
            marker=dict(size=6, line=dict(color="#FFFFFF", width=1.2)),
            hovertemplate="<b>%{fullData.name}</b><br>%{x|%d %b %Y}<br>%{y:,.0f} GNF<extra></extra>",
            yaxis="y",
        ))
        fig.add_trace(go.Scatter(
            x=group["date"],
            y=group["apports_eur_cumule"],
            mode="lines+markers",
            name=f"{nom} · EUR",
            line=dict(color=color, width=2.2, dash="dot"),
            marker=dict(size=6, symbol="diamond", line=dict(color="#FFFFFF", width=1.2)),
            hovertemplate="<b>%{fullData.name}</b><br>%{x|%d %b %Y}<br>%{y:,.2f} EUR<extra></extra>",
            yaxis="y2",
        ))

    tick_values = df["date"].drop_duplicates().sort_values()
    fig.update_layout(
        **_layout_base_without("legend"),
        title=dict(text="Évolution des apports par investisseur", font=dict(size=12, color="#475569", weight=700), x=0, xref="paper"),
        xaxis=_date_axis(tick_values),
        yaxis=dict(**_AXIS_Y, title=None, tickformat=",", side="left"),
        yaxis2=dict(
            title=None,
            overlaying="y",
            side="right",
            showgrid=False,
            zeroline=False,
            tickfont=dict(size=10, color="#94A3B8"),
        ),
        height=330,
        legend=dict(
            orientation="h", yanchor="bottom", y=-0.32, xanchor="center", x=0.5,
            font=dict(size=10, color="#94A3B8"), bgcolor="rgba(0,0,0,0)",
        ),
    )
    return fig


def chart_evolution_apports_investisseur(df_evolution: pd.DataFrame, nom: str) -> go.Figure:
    if df_evolution is None or df_evolution.empty:
        return _empty("Aucun apport")

    df = df_evolution.copy()
    df = df[df["nom"] == nom]
    if df.empty:
        return _empty("Aucun apport")

    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.normalize()
    df["apports_eur_cumule"] = pd.to_numeric(df["apports_eur_cumule"], errors="coerce").fillna(0)
    df["apports_gnf_cumule"] = pd.to_numeric(df["apports_gnf_cumule"], errors="coerce").fillna(0)
    df = df.dropna(subset=["date"]).sort_values("date")
    if df.empty:
        return _empty("Aucun apport")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["date"],
        y=df["apports_gnf_cumule"],
        mode="lines+markers",
        name="Équivalent GNF",
        line=dict(color="#059669", width=2.6),
        marker=dict(size=6, line=dict(color="#FFFFFF", width=1.2)),
        hovertemplate="<b>%{x|%d %b %Y}</b><br>%{y:,.0f} GNF<extra></extra>",
        yaxis="y",
    ))
    fig.add_trace(go.Scatter(
        x=df["date"],
        y=df["apports_eur_cumule"],
        mode="lines+markers",
        name="Apports EUR",
        line=dict(color="#2563EB", width=2.4, dash="dot"),
        marker=dict(size=6, symbol="diamond", line=dict(color="#FFFFFF", width=1.2)),
        hovertemplate="<b>%{x|%d %b %Y}</b><br>%{y:,.2f} EUR<extra></extra>",
        yaxis="y2",
    ))

    tick_values = df["date"].drop_duplicates().sort_values()
    fig.update_layout(
        **_layout_base_without("legend"),
        title=dict(text=f"Évolution des apports · {nom}", font=dict(size=12, color="#475569", weight=700), x=0, xref="paper"),
        xaxis=_date_axis(tick_values),
        yaxis=dict(**_AXIS_Y, title=None, tickformat=",", side="left"),
        yaxis2=dict(
            title=None,
            overlaying="y",
            side="right",
            showgrid=False,
            zeroline=False,
            tickfont=dict(size=10, color="#94A3B8"),
        ),
        height=290,
        legend=dict(
            orientation="h", yanchor="bottom", y=-0.28, xanchor="center", x=0.5,
            font=dict(size=10, color="#94A3B8"), bgcolor="rgba(0,0,0,0)",
        ),
    )
    return fig


def chart_valeurs_par_compte(df_comptes: pd.DataFrame) -> go.Figure:
    if df_comptes is None or df_comptes.empty:
        return _empty("Aucun compte")

    df = df_comptes.copy()
    df["valeur_gnf"] = pd.to_numeric(df["valeur_gnf"], errors="coerce").fillna(0)
    df = df[df["valeur_gnf"] > 0].sort_values("valeur_gnf", ascending=True)
    if df.empty:
        return _empty("Aucun solde positif")

    colors = df["devise"].astype(str).str.upper().map({"EUR": "#2563EB", "GNF": "#059669"}).fillna("#64748B")
    fig = go.Figure(go.Bar(
        x=df["valeur_gnf"],
        y=df["nom"],
        orientation="h",
        marker=dict(color=colors, line=dict(color="rgba(0,0,0,0)", width=0)),
        text=[fmt_gnf(v) for v in df["valeur_gnf"]],
        textposition="outside",
        textfont=dict(size=10, color="#475569"),
        customdata=df[["devise", "pays"]],
        hovertemplate="<b>%{y}</b><br>%{x:,.0f} GNF<br>%{customdata[1]} · %{customdata[0]}<extra></extra>",
    ))
    fig.update_layout(
        **_BASE,
        title=dict(text="Valeur par compte", font=dict(size=12, color="#475569", weight=700), x=0, xref="paper"),
        xaxis=dict(**_AXIS_X, title=None, tickformat=","),
        yaxis=dict(**{k: v for k, v in _AXIS_Y.items() if k != "showgrid"}, title=None, showgrid=False),
        height=max(240, 54 * len(df)),
        showlegend=False,
    )
    return fig


def chart_repartition_pays(df_pays: pd.DataFrame) -> go.Figure:
    if df_pays is None or df_pays.empty:
        return _empty("Aucune donnée pays")

    fig = go.Figure(go.Pie(
        labels=df_pays["pays"],
        values=df_pays["montant_gnf"],
        hole=0.58,
        marker=dict(colors=COULEURS_CHART[: len(df_pays)], line=dict(color=_BG, width=2)),
        hovertemplate="<b>%{label}</b><br>%{value:,.0f} GNF · %{percent}<extra></extra>",
        textinfo="percent+label",
        textfont=dict(size=10),
    ))
    fig.update_layout(
        **_BASE,
        title=dict(text="Par pays", font=dict(size=12, color="#475569", weight=700), x=0, xref="paper"),
        showlegend=False,
        height=260,
    )
    return fig


def chart_repartition_devise(df_devise: pd.DataFrame) -> go.Figure:
    if df_devise is None or df_devise.empty:
        return _empty("Aucune donnée devise")

    fig = go.Figure(go.Pie(
        labels=df_devise["devise"],
        values=df_devise["montant_gnf"],
        hole=0.58,
        marker=dict(colors=["#2563EB", "#059669"], line=dict(color=_BG, width=2)),
        hovertemplate="<b>%{label}</b><br>%{value:,.0f} GNF · %{percent}<extra></extra>",
        textinfo="percent+label",
        textfont=dict(size=10),
    ))
    fig.update_layout(
        **_BASE,
        title=dict(text="Par devise actuelle", font=dict(size=12, color="#475569", weight=700), x=0, xref="paper"),
        showlegend=False,
        height=260,
    )
    return fig


def chart_objectifs_gauge(nom: str, pct: float, couleur: str = "#2563EB") -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=pct,
        number=dict(suffix=" %", font=dict(size=26, color="#0F172A", family=_FONT), valueformat=".1f"),
        gauge=dict(
            axis=dict(range=[0, 100], tickwidth=0, visible=False),
            bar=dict(color=couleur, thickness=0.22),
            bgcolor="rgba(0,0,0,0)",
            borderwidth=0,
            steps=[dict(range=[0, 100], color="#F1F5F9")],
            threshold=dict(line=dict(color="#F43F5E", width=2), thickness=0.75, value=100),
        ),
        title=dict(text=nom, font=dict(size=11, color="#94A3B8", family=_FONT)),
    ))
    fig.update_layout(
        paper_bgcolor=_BG,
        font=dict(family=_FONT),
        margin=dict(l=12, r=12, t=60, b=8),
        height=200,
    )
    return fig


def chart_historique_taux(df_taux: pd.DataFrame) -> go.Figure:
    if df_taux is None or df_taux.empty:
        return _empty("Aucun taux enregistré")

    df = df_taux.copy()
    date_col = "date_taux" if "date_taux" in df.columns else "date"
    taux_col = "eur_to_gnf" if "eur_to_gnf" in df.columns else "taux_eur_gnf"
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df[taux_col] = pd.to_numeric(df[taux_col], errors="coerce")
    df = df.dropna(subset=[date_col, taux_col]).sort_values(date_col)

    fig = go.Figure(go.Scatter(
        x=df[date_col],
        y=df[taux_col],
        mode="lines+markers",
        line=dict(color="#7C3AED", width=2.5, shape="spline", smoothing=0.5),
        marker=dict(size=7, color="#7C3AED", line=dict(color="#fff", width=1.5)),
        hovertemplate="<b>%{x|%d %b %Y}</b><br>Taux : %{y:,.0f} GNF/€<extra></extra>",
    ))
    fig.update_layout(
        **_BASE,
        title=dict(text="Historique EUR → GNF", font=dict(size=12, color="#475569", weight=700), x=0, xref="paper"),
        xaxis=dict(**_AXIS_X, title=None, tickangle=-25, automargin=True),
        yaxis=dict(**_AXIS_Y, title=None),
        height=280,
        showlegend=False,
    )
    return fig


def chart_mouvements_par_mois(df_mvt: pd.DataFrame) -> go.Figure:
    if df_mvt is None or df_mvt.empty:
        return _empty("Aucun mouvement")

    df = df_mvt.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["montant_converti_gnf"] = pd.to_numeric(df["montant_converti_gnf"], errors="coerce").fillna(0)
    df = df.dropna(subset=["date"])
    df["mois"] = df["date"].dt.to_period("M").dt.to_timestamp()

    apports  = df[df["type_mouvement"] == "apport"].groupby("mois")["montant_converti_gnf"].sum()
    retraits = df[df["type_mouvement"].isin(["depense", "retrait"])].groupby("mois")["montant_converti_gnf"].sum()
    tick_values = pd.Index(apports.index).union(pd.Index(retraits.index)).sort_values()

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=apports.index, y=apports.values, name="Apports",
        marker=dict(color="#059669", opacity=0.85),
        hovertemplate="<b>%{x|%b %Y}</b><br>Apports : %{y:,.0f} GNF<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=retraits.index, y=retraits.values, name="Dépenses",
        marker=dict(color="#F43F5E", opacity=0.85),
        hovertemplate="<b>%{x|%b %Y}</b><br>Dépenses : %{y:,.0f} GNF<extra></extra>",
    ))
    fig.update_layout(
        **_BASE,
        barmode="group",
        title=dict(text="Apports & dépenses / mois", font=dict(size=12, color="#475569", weight=700), x=0, xref="paper"),
        xaxis=_date_axis(tick_values, "%b %Y"),
        yaxis=dict(**_AXIS_Y, title=None),
        height=260,
        bargap=0.25,
        bargroupgap=0.08,
    )
    return fig


def _empty(msg: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=msg, xref="paper", yref="paper", x=0.5, y=0.5,
        showarrow=False,
        font=dict(size=13, color="#94A3B8", family=_FONT),
    )
    fig.update_layout(
        paper_bgcolor=_BG, plot_bgcolor=_BG,
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        height=220, margin=dict(l=8, r=8, t=30, b=8),
    )
    return fig
