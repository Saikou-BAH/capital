"""Graphiques Plotly — thème premium, cohérent avec le design system."""

import plotly.graph_objects as go
import pandas as pd
from utils.config import (
    COULEURS_CHART, COULEUR_PRIMAIRE, CAPITAL_CIBLE_GNF,
    OBJECTIF_SEPTEMBRE_MONTANT, OBJECTIF_SEPTEMBRE_DATE, OBJECTIF_SEPTEMBRE_NOM,
    OBJECTIF_DECEMBRE_MONTANT, OBJECTIF_DECEMBRE_DATE, OBJECTIF_DECEMBRE_NOM,
)
from utils.formatting import fmt_gnf

_FONT = "Inter, system-ui, sans-serif"
_GRID = "rgba(232,225,214,0.8)"
_BG   = "rgba(0,0,0,0)"

_BASE = dict(
    paper_bgcolor=_BG,
    plot_bgcolor=_BG,
    font=dict(family=_FONT, color="#6B6155", size=11),
    margin=dict(l=8, r=8, t=36, b=12),
    legend=dict(
        orientation="h", yanchor="bottom", y=-0.28, xanchor="center", x=0.5,
        font=dict(size=10, color="#7F7568"),
        bgcolor="rgba(0,0,0,0)",
    ),
    hoverlabel=dict(
        bgcolor="#241F19", font_size=12, font_color="#FAF8F4",
        font_family=_FONT, bordercolor="#3A2A1E",
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
    tickfont=dict(size=10, color="#7F7568"),
    linecolor="#E8E1D6", linewidth=1,
)
_AXIS_Y = dict(
    showgrid=True, gridcolor=_GRID, gridwidth=1, zeroline=False,
    tickfont=dict(size=10, color="#7F7568"),
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
    df = df.sort_values("date")
    tick_values = df["date"].drop_duplicates().sort_values()

    fig = go.Figure()

    # Projection linéaire si ≥ 2 points
    if len(df) >= 2:
        import numpy as np
        x_num = (df["date"] - df["date"].iloc[0]).dt.days.values
        y_vals = df["capital_cumule"].values
        coef = np.polyfit(x_num, y_vals, 1)  # pente en GNF/jour
        pente = coef[0]
        if pente > 0:
            # date d'atteinte objectif final
            jours_restants = (OBJECTIF_DECEMBRE_MONTANT - y_vals[-1]) / pente
            date_proj = df["date"].iloc[-1] + pd.Timedelta(days=max(0, jours_restants))
            x_proj = pd.date_range(start=df["date"].iloc[-1], end=date_proj, periods=20)
            y_proj = y_vals[-1] + pente * (x_proj - df["date"].iloc[-1]).days.values
            fig.add_trace(go.Scatter(
                x=x_proj, y=y_proj,
                mode="lines",
                name="Projection",
                line=dict(color="#B65C2E", width=1.5, dash="dot"),
                opacity=0.4,
                hovertemplate="<b>Projection</b><br>%{x|%b %Y}<br>%{y:,.0f} GNF<extra></extra>",
            ))

    # Courbe capital réel
    fig.add_trace(go.Scatter(
        x=df["date"],
        y=df["capital_cumule"],
        mode="lines+markers",
        name="Capital réel",
        line=dict(color="#B65C2E", width=2.5, shape="spline", smoothing=0.6),
        marker=dict(size=6, color="#B65C2E", line=dict(color="#FFFFFF", width=1.5)),
        fill="tozeroy",
        fillcolor="rgba(182,92,46,0.08)",
        hovertemplate="<b>%{x|%d %b %Y}</b><br>Capital : %{y:,.0f} GNF<extra></extra>",
    ))

    # Ligne objectif Septembre
    fig.add_hline(
        y=OBJECTIF_SEPTEMBRE_MONTANT,
        line=dict(color="#99651A", dash="dash", width=1.2),
        annotation_text="Sept. 250M",
        annotation_position="top left",
        annotation_font=dict(color="#99651A", size=10),
    )
    # Ligne objectif Décembre
    fig.add_hline(
        y=OBJECTIF_DECEMBRE_MONTANT,
        line=dict(color="#B3432F", dash="dot", width=1.5),
        annotation_text="Déc. 500M",
        annotation_position="top right",
        annotation_font=dict(color="#B3432F", size=10),
    )

    fig.update_layout(
        **_layout_base_without("legend"),
        title=dict(text="Évolution du capital & objectifs", font=dict(size=13, color="#6B6155", weight=650), x=0, xref="paper"),
        xaxis=_date_axis(tick_values),
        yaxis=dict(**_AXIS_Y, title=None, tickformat=","),
        height=340,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
            font=dict(size=10), bgcolor="rgba(0,0,0,0)",
        ),
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
        title=dict(text="Répartition par investisseur", font=dict(size=12, color="#6B6155", weight=650), x=0, xref="paper"),
        showlegend=True,
        legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.02,
                    font=dict(size=10, color="#6B6155"), bgcolor="rgba(0,0,0,0)"),
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
        cliponaxis=False,
        textfont=dict(size=10, color="#6B6155"),
        hovertemplate="<b>%{y}</b><br>%{x:,.0f} GNF<extra></extra>",
    ))
    fig.update_layout(
        **_BASE,
        title=dict(text="Apports nets par investisseur", font=dict(size=12, color="#6B6155", weight=650), x=0, xref="paper"),
        xaxis=dict(**_AXIS_X, title=None, range=[0, df["net_gnf"].max() * 1.18]),
        yaxis=dict(**{k: v for k, v in _AXIS_Y.items() if k != "showgrid"}, title=None, showgrid=False),
        height=max(220, 52 * len(df)),
        showlegend=False,
    )
    return fig


def _cycle_colors(n: int) -> list[str]:
    if n <= len(COULEURS_CHART):
        return COULEURS_CHART[:n]
    return (COULEURS_CHART * (n // len(COULEURS_CHART) + 1))[:n]


def chart_simulation_parts_bar(df_sim: pd.DataFrame) -> go.Figure:
    """Barres des parts finales (%) par personne — page Simulation des parts."""
    if df_sim is None or df_sim.empty or df_sim["% final"].sum() <= 0:
        return _empty("Aucune donnée de simulation")

    df = df_sim.sort_values("% final", ascending=True)
    fig = go.Figure(go.Bar(
        x=df["% final"],
        y=df["Personne"],
        orientation="h",
        marker=dict(color=_cycle_colors(len(df)), line=dict(color="rgba(0,0,0,0)", width=0)),
        text=[f"{v:.1f} %" for v in df["% final"]],
        textposition="outside",
        cliponaxis=False,
        textfont=dict(size=10, color="#6B6155"),
        hovertemplate="<b>%{y}</b><br>%{x:.1f} %<extra></extra>",
    ))
    fig.update_layout(
        **_BASE,
        title=dict(text="Parts finales par personne (%)", font=dict(size=12, color="#6B6155", weight=650), x=0, xref="paper"),
        xaxis=dict(**_AXIS_X, title=None, range=[0, max(df["% final"].max() * 1.2, 1)]),
        yaxis=dict(**{k: v for k, v in _AXIS_Y.items() if k != "showgrid"}, title=None, showgrid=False),
        height=max(220, 46 * len(df)),
        showlegend=False,
    )
    return fig


def chart_simulation_parts_pie(df_sim: pd.DataFrame) -> go.Figure:
    """Camembert des parts finales (%) par personne — page Simulation des parts."""
    if df_sim is None or df_sim.empty or df_sim["% final"].sum() <= 0:
        return _empty("Aucune donnée de simulation")

    fig = go.Figure(go.Pie(
        labels=df_sim["Personne"],
        values=df_sim["% final"],
        hole=0.38,
        marker=dict(colors=_cycle_colors(len(df_sim)), line=dict(color=_BG, width=2)),
        hovertemplate="<b>%{label}</b><br>%{percent}<extra></extra>",
        textinfo="percent+label",
        textfont=dict(size=10),
    ))
    fig.update_layout(
        **_BASE,
        title=dict(text="Répartition finale (camembert)", font=dict(size=12, color="#6B6155", weight=650), x=0, xref="paper"),
        showlegend=False,
        height=320,
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
        marker=dict(color="#46688A", opacity=0.85, line=dict(color="rgba(0,0,0,0)", width=0)),
        text=[f"{v:,.2f} €".replace(",", " ").replace(".", ",") for v in df["apports_eur"]],
        textposition="outside",
        cliponaxis=False,
        textfont=dict(size=10, color="#6B6155"),
        customdata=df[["apports_equiv_gnf"]],
        hovertemplate="<b>%{y}</b><br>%{x:,.2f} EUR<br>Équiv. : %{customdata[0]:,.0f} GNF<extra></extra>",
    ))
    fig.update_layout(
        **_BASE,
        title=dict(text="Apports EUR par investisseur", font=dict(size=12, color="#6B6155", weight=650), x=0, xref="paper"),
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
        title=dict(text="Évolution des apports par investisseur", font=dict(size=12, color="#6B6155", weight=650), x=0, xref="paper"),
        xaxis=_date_axis(tick_values),
        yaxis=dict(**_AXIS_Y, title=None, tickformat=",", side="left"),
        yaxis2=dict(
            title=None,
            overlaying="y",
            side="right",
            showgrid=False,
            zeroline=False,
            tickfont=dict(size=10, color="#7F7568"),
        ),
        height=330,
        legend=dict(
            orientation="h", yanchor="bottom", y=-0.32, xanchor="center", x=0.5,
            font=dict(size=10, color="#7F7568"), bgcolor="rgba(0,0,0,0)",
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
        line=dict(color="#3E7C51", width=2.6),
        marker=dict(size=6, line=dict(color="#FFFFFF", width=1.2)),
        hovertemplate="<b>%{x|%d %b %Y}</b><br>%{y:,.0f} GNF<extra></extra>",
        yaxis="y",
    ))
    fig.add_trace(go.Scatter(
        x=df["date"],
        y=df["apports_eur_cumule"],
        mode="lines+markers",
        name="Apports EUR",
        line=dict(color="#46688A", width=2.4, dash="dot"),
        marker=dict(size=6, symbol="diamond", line=dict(color="#FFFFFF", width=1.2)),
        hovertemplate="<b>%{x|%d %b %Y}</b><br>%{y:,.2f} EUR<extra></extra>",
        yaxis="y2",
    ))

    tick_values = df["date"].drop_duplicates().sort_values()
    fig.update_layout(
        **_layout_base_without("legend"),
        title=dict(text=f"Évolution des apports · {nom}", font=dict(size=12, color="#6B6155", weight=650), x=0, xref="paper"),
        xaxis=_date_axis(tick_values),
        yaxis=dict(**_AXIS_Y, title=None, tickformat=",", side="left"),
        yaxis2=dict(
            title=None,
            overlaying="y",
            side="right",
            showgrid=False,
            zeroline=False,
            tickfont=dict(size=10, color="#7F7568"),
        ),
        height=290,
        legend=dict(
            orientation="h", yanchor="bottom", y=-0.28, xanchor="center", x=0.5,
            font=dict(size=10, color="#7F7568"), bgcolor="rgba(0,0,0,0)",
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

    colors = df["devise"].astype(str).str.upper().map({"EUR": "#46688A", "GNF": "#3E7C51"}).fillna("#7F7568")
    fig = go.Figure(go.Bar(
        x=df["valeur_gnf"],
        y=df["nom"],
        orientation="h",
        marker=dict(color=colors, line=dict(color="rgba(0,0,0,0)", width=0)),
        text=[fmt_gnf(v) for v in df["valeur_gnf"]],
        textposition="outside",
        cliponaxis=False,
        textfont=dict(size=10, color="#6B6155"),
        customdata=df[["devise", "pays"]],
        hovertemplate="<b>%{y}</b><br>%{x:,.0f} GNF<br>%{customdata[1]} · %{customdata[0]}<extra></extra>",
    ))
    fig.update_layout(
        **_BASE,
        title=dict(text="Valeur par compte", font=dict(size=12, color="#6B6155", weight=650), x=0, xref="paper"),
        xaxis=dict(**_AXIS_X, title=None, tickformat=",", range=[0, df["valeur_gnf"].max() * 1.25]),
        yaxis=dict(**{k: v for k, v in _AXIS_Y.items() if k != "showgrid"}, title=None, showgrid=False),
        height=max(240, 54 * len(df)),
        showlegend=False,
    )
    return fig


def chart_evolution_soldes_comptes(df_mvt: pd.DataFrame, df_cpt: pd.DataFrame) -> go.Figure:
    if df_mvt is None or df_mvt.empty or df_cpt is None or df_cpt.empty:
        return _empty("Aucun mouvement enregistré")

    df = df_mvt.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["montant_converti_gnf"] = pd.to_numeric(df["montant_converti_gnf"], errors="coerce").fillna(0)
    df = df.dropna(subset=["date"])
    df["mois"] = df["date"].dt.to_period("M").dt.to_timestamp()

    cpt_map = df_cpt.set_index("id")["nom"].to_dict()
    all_months = pd.date_range(df["mois"].min(), df["mois"].max(), freq="MS")

    fig = go.Figure()
    colors = COULEURS_CHART

    for idx, (cpt_id, nom) in enumerate(cpt_map.items()):
        entrees = df[df["compte_destination_id"] == cpt_id].groupby("mois")["montant_converti_gnf"].sum()
        sorties = df[df["compte_source_id"] == cpt_id].groupby("mois")["montant_converti_gnf"].sum()

        flux = entrees.subtract(sorties, fill_value=0).reindex(all_months, fill_value=0)
        cumul = flux.cumsum()

        if cumul.abs().sum() == 0:
            continue

        color = colors[idx % len(colors)]
        fig.add_trace(go.Scatter(
            x=cumul.index,
            y=cumul.values,
            mode="lines+markers",
            name=nom,
            line=dict(color=color, width=2.2),
            marker=dict(size=5, line=dict(color="#FFFFFF", width=1.2)),
            hovertemplate=f"<b>{nom}</b><br>%{{x|%b %Y}}<br>Solde : %{{y:,.0f}} GNF<extra></extra>",
        ))

    if not fig.data:
        return _empty("Aucune donnée de solde disponible")

    tick_values = _month_tick_values(all_months, max_ticks=6)
    fig.update_layout(
        **_layout_base_without("legend"),
        title=dict(text="Évolution du solde par compte", font=dict(size=12, color="#6B6155", weight=650), x=0, xref="paper"),
        xaxis=dict(**_AXIS_X, title=None, tickmode="array", tickvals=tick_values, tickformat="%b %y", tickangle=-25, automargin=True),
        yaxis=dict(**_AXIS_Y, title=None, tickformat=","),
        height=340,
        legend=dict(
            orientation="h", yanchor="bottom", y=-0.28, xanchor="center", x=0.5,
            font=dict(size=10, color="#7F7568"), bgcolor="rgba(0,0,0,0)",
        ),
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
        title=dict(text="Par pays", font=dict(size=12, color="#6B6155", weight=650), x=0, xref="paper"),
        showlegend=False,
        height=260,
    )
    return fig


def chart_repartition_devise(df_devise: pd.DataFrame) -> go.Figure:
    if df_devise is None or df_devise.empty:
        return _empty("Aucune donnée devise")

    _color_map = {"EUR": "#46688A", "GNF": "#3E7C51"}
    _colors = df_devise["devise"].astype(str).str.upper().map(_color_map).fillna("#7F7568").tolist()

    fig = go.Figure(go.Pie(
        labels=df_devise["devise"],
        values=df_devise["montant_gnf"],
        hole=0.58,
        marker=dict(colors=_colors, line=dict(color=_BG, width=2)),
        hovertemplate="<b>%{label}</b><br>%{value:,.0f} GNF · %{percent}<extra></extra>",
        textinfo="percent+label",
        textfont=dict(size=10),
    ))
    fig.update_layout(
        **_BASE,
        title=dict(text="Par devise actuelle", font=dict(size=12, color="#6B6155", weight=650), x=0, xref="paper"),
        showlegend=False,
        height=260,
    )
    return fig


def chart_objectifs_gauge(nom: str, pct: float, couleur: str = "#B65C2E") -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=pct,
        number=dict(suffix=" %", font=dict(size=26, color="#241F19", family=_FONT), valueformat=".1f"),
        gauge=dict(
            axis=dict(range=[0, 100], tickwidth=0, visible=False),
            bar=dict(color=couleur, thickness=0.22),
            bgcolor="rgba(0,0,0,0)",
            borderwidth=0,
            steps=[dict(range=[0, 100], color="#F5F1EA")],
            threshold=dict(line=dict(color="#B3432F", width=2), thickness=0.75, value=100),
        ),
        title=dict(text=nom, font=dict(size=11, color="#7F7568", family=_FONT)),
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
        line=dict(color="#6B5B95", width=2.5, shape="spline", smoothing=0.5),
        marker=dict(size=7, color="#6B5B95", line=dict(color="#fff", width=1.5)),
        hovertemplate="<b>%{x|%d %b %Y}</b><br>Taux : %{y:,.0f} GNF/€<extra></extra>",
    ))
    fig.update_layout(
        **_BASE,
        title=dict(text="Historique EUR → GNF", font=dict(size=12, color="#6B6155", weight=650), x=0, xref="paper"),
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
    sorties  = df[df["type_mouvement"].isin(["depense", "retrait", "frais_retrait"])].groupby("mois")["montant_converti_gnf"].sum()
    tick_values = pd.Index(apports.index).union(pd.Index(sorties.index)).sort_values()

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=apports.index, y=apports.values, name="Apports",
        marker=dict(color="#3E7C51", opacity=0.85),
        hovertemplate="<b>%{x|%b %Y}</b><br>Apports : %{y:,.0f} GNF<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=sorties.index, y=sorties.values, name="Dépenses & Frais",
        marker=dict(color="#B3432F", opacity=0.85),
        hovertemplate="<b>%{x|%b %Y}</b><br>Sorties : %{y:,.0f} GNF<extra></extra>",
    ))
    n_months = len(tick_values)
    fig.update_layout(
        **_layout_base_without("legend"),
        barmode="group",
        title=dict(text="Apports & sorties / mois", font=dict(size=13, color="#6B6155", weight=650), x=0, xref="paper"),
        xaxis=dict(
            **_date_axis(tick_values, "%b %Y"),
            rangeslider=dict(visible=n_months > 6, thickness=0.06),
        ),
        yaxis=dict(**_AXIS_Y, title=None),
        height=320,
        bargap=0.3,
        bargroupgap=0.08,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=11),
        ),
    )
    return fig


def chart_frais_par_investisseur(df_mvt: pd.DataFrame, df_inv: pd.DataFrame) -> go.Figure:
    if df_mvt is None or df_mvt.empty:
        return _empty("Aucun frais enregistré")

    df = df_mvt[df_mvt["type_mouvement"] == "frais_retrait"].copy()
    if df.empty:
        return _empty("Aucun frais de retrait enregistré")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["montant_converti_gnf"] = pd.to_numeric(df["montant_converti_gnf"], errors="coerce").fillna(0)
    df = df.dropna(subset=["date"])
    df["mois"] = df["date"].dt.to_period("M").dt.to_timestamp()

    if df_inv is not None and not df_inv.empty:
        noms = df_inv[["id", "nom"]].rename(columns={"id": "investisseur_id"})
        df = df.merge(noms, on="investisseur_id", how="left")
        df["nom"] = df["nom"].fillna(df["investisseur_id"])
    else:
        df["nom"] = df["investisseur_id"]

    investisseurs = sorted(df["nom"].dropna().unique())
    colors = COULEURS_CHART

    fig = go.Figure()
    for i, nom in enumerate(investisseurs):
        grp = df[df["nom"] == nom].groupby("mois")["montant_converti_gnf"].sum()
        total = grp.sum()
        fig.add_trace(go.Bar(
            x=grp.index,
            y=grp.values,
            name=f"{nom} · {fmt_gnf(total)}",
            marker=dict(color=colors[i % len(colors)], opacity=0.85),
            hovertemplate=f"<b>{nom}</b><br>%{{x|%b %Y}}<br>Frais : %{{y:,.0f}} GNF<extra></extra>",
        ))

    all_mois = df["mois"].drop_duplicates().sort_values()
    fig.update_layout(
        **_layout_base_without("legend"),
        barmode="stack",
        title=dict(text="Frais de retrait par investisseur", font=dict(size=13, color="#6B6155", weight=650), x=0, xref="paper"),
        xaxis=_date_axis(all_mois, "%b %Y"),
        yaxis=dict(**_AXIS_Y, title=None),
        height=300,
        bargap=0.35,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
            font=dict(size=11), bgcolor="rgba(0,0,0,0)",
        ),
    )
    return fig


def chart_frais_retrait_par_mois(df_mvt: pd.DataFrame) -> go.Figure:
    if df_mvt is None or df_mvt.empty:
        return _empty("Aucun frais enregistré")

    df = df_mvt.copy()
    df = df[df["type_mouvement"] == "frais_retrait"]
    if df.empty:
        return _empty("Aucun frais de retrait enregistré")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["montant_converti_gnf"] = pd.to_numeric(df["montant_converti_gnf"], errors="coerce").fillna(0)
    df = df.dropna(subset=["date"])
    df["mois"] = df["date"].dt.to_period("M").dt.to_timestamp()

    frais_mois = df.groupby("mois")["montant_converti_gnf"].sum()
    total = frais_mois.sum()

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=frais_mois.index, y=frais_mois.values, name="Frais de retrait",
        marker=dict(color="#6B5B95", opacity=0.85),
        hovertemplate="<b>%{x|%b %Y}</b><br>Frais : %{y:,.0f} GNF<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=frais_mois.index, y=frais_mois.cumsum(),
        name="Cumul", mode="lines+markers",
        line=dict(color="#A2496B", width=2, dash="dot"),
        marker=dict(size=5),
        hovertemplate="<b>%{x|%b %Y}</b><br>Cumul : %{y:,.0f} GNF<extra></extra>",
        yaxis="y2",
    ))
    fig.update_layout(
        **_BASE,
        barmode="group",
        title=dict(
            text=f"Frais de retrait / mois — Total : {fmt_gnf(total)}",
            font=dict(size=12, color="#6B6155", weight=650), x=0, xref="paper",
        ),
        xaxis=_date_axis(frais_mois.index, "%b %Y"),
        yaxis=dict(**_AXIS_Y, title=None),
        yaxis2=dict(
            overlaying="y", side="right", showgrid=False, zeroline=False,
            tickfont=dict(size=9, color="#A2496B"), title=None,
        ),
        height=260,
        bargap=0.3,
    )
    return fig


def _empty(msg: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=msg, xref="paper", yref="paper", x=0.5, y=0.5,
        showarrow=False,
        font=dict(size=13, color="#7F7568", family=_FONT),
    )
    fig.update_layout(
        paper_bgcolor=_BG, plot_bgcolor=_BG,
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        height=220, margin=dict(l=8, r=8, t=30, b=8),
    )
    return fig
