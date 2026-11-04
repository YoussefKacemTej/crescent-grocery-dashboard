"""
charts.py - Plotly figures for the dashboard. No business logic, no Streamlit layout.

Theme rule: the viewer can switch light/dark from the menu WITHOUT a script rerun, so nothing here may
depend on the theme at run time. Text, grid, axis and hover colours are left unset and filled in by
Streamlit's chart theme in the browser (theme="streamlit"); data colours are mid-tones / translucent
tints that read on both the light and the dark background.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

FONT = "Inter, -apple-system, 'Segoe UI', Roboto, sans-serif"
PLOTLY_CONFIG = {"displayModeBar": False}


@dataclass(frozen=True)
class Palette:
    green: str
    green_lt: str
    amber: str
    amber_lt: str
    red: str
    red_lt: str
    teal: str
    slate: str
    heat: tuple
    fill_alpha: str


PAL = Palette(green="#1F8A6E", green_lt="rgba(31,138,110,.38)", amber="#E3A02F", amber_lt="rgba(227,160,47,.38)",
              red="#E0566A", red_lt="rgba(224,86,106,.38)", teal="#3AA394", slate="#8A96A3",
              heat=("#FBE9EC", "#EE9AA7", "#C8324A"), fill_alpha="rgba(31,138,110,.18)")


def palette() -> Palette:
    return PAL


def register_templates() -> None:
    """Layout defaults only (fonts, margins, legend); colours come from the Streamlit theme."""
    t = go.layout.Template()
    t.layout = go.Layout(
        font=dict(family=FONT, size=12),
        colorway=[PAL.green, PAL.amber, PAL.teal, PAL.red, PAL.slate],
        margin=dict(l=6, r=6, t=10, b=6),
        xaxis=dict(showgrid=False, ticks="", title=None, automargin=True),
        yaxis=dict(zeroline=False, ticks="", title=None, automargin=True),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title=None, font=dict(size=12)),
        hoverlabel=dict(font=dict(family=FONT, size=12.5)),
        hovermode="x unified",
        bargap=0.28,
    )
    pio.templates["crescent"] = t


def _finish(fig: go.Figure, height: int) -> go.Figure:
    # transparent = the card's own surface shows through, in either theme
    fig.update_layout(template="crescent", height=height, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    if _is_text_axis(fig):
        # monthly axes (36 labels) get thinned; short category axes keep every label
        fig.update_xaxes(type="category", nticks=13 if len(fig.data[0].x) > 24 else 0)
    return fig


def show(fig: go.Figure) -> None:
    # theme='streamlit': text / grid / hover colours follow the viewer's theme live, even after a menu switch
    st.plotly_chart(fig, width="stretch", config=PLOTLY_CONFIG, theme="streamlit")


# ------------------------------------------------------------------ figure builders
def hbar(df: pd.DataFrame, x: str, y: str, fmt: str = ",.0f", tone: str = "green", height: int | None = None,
         suffix: str = "", highlight: bool = True) -> go.Figure:
    """Ranked horizontal bar: leader solid, rest tinted, value labels outside."""
    p = palette()
    solid, tint = _tone(p, tone)
    colors = [solid if (i == 0 or not highlight) else tint for i in range(len(df))]
    fig = go.Figure(go.Bar(x=df[x], y=df[y].astype(str), orientation="h", marker=dict(color=colors, cornerradius=4),
                           text=df[x], texttemplate=f"%{{text:{fmt}}}{suffix}", textposition="outside",
                           cliponaxis=False,
                           hovertemplate=f"%{{y}}<br><b>%{{x:{fmt}}}</b>{suffix}<extra></extra>"))
    fig.update_yaxes(autorange="reversed", showgrid=False, linecolor="rgba(0,0,0,0)")
    fig.update_xaxes(visible=False)
    fig.update_layout(hovermode="closest", margin=dict(l=6, r=52, t=6, b=6))
    return _finish(fig, height or max(250, 32 * len(df) + 40))


def vbar(df: pd.DataFrame, x: str, y: str, fmt: str = ".2f", tone: str = "green", height: int = 300,
         suffix: str = "", highlight_max: bool = True, ref: tuple[float, str] | None = None) -> go.Figure:
    """Column chart, peak highlighted. ref=(value, label) draws a dashed baseline (e.g. non-promoted margin)."""
    p = palette()
    solid, tint = _tone(p, tone)
    vals = list(df[y])
    peak = int(np.nanargmax(vals)) if vals else -1
    colors = [solid if (i == peak or not highlight_max) else tint for i in range(len(vals))]
    fig = go.Figure(go.Bar(x=df[x].astype(str), y=df[y], marker=dict(color=colors, cornerradius=4), text=df[y],
                           texttemplate=f"%{{text:{fmt}}}{suffix}", textposition="outside",
                           cliponaxis=False, hovertemplate=f"%{{x}}<br><b>%{{y:{fmt}}}</b>{suffix}<extra></extra>"))
    fig.update_yaxes(visible=False)
    fig.update_layout(hovermode="closest", margin=dict(l=6, r=6, t=24, b=6))
    if ref is not None:
        fig.add_hline(y=ref[0], line=dict(color=p.slate, width=1.5, dash="dash"),
                      annotation=dict(text=ref[1], font=dict(size=11.5)),
                      annotation_position="top right")
        fig.update_yaxes(range=[0, max(max(vals), ref[0]) * 1.18])
    return _finish(fig, height)


def bar_line(x, bars, line, bar_name: str, line_name: str, height: int = 340, line_range=None,
             tilt: bool = False) -> go.Figure:
    """Bars (SAR, left axis) + line (%, right axis): monthly sales & margin, Pareto."""
    p = palette()
    x = pd.Series(x).astype(str)
    fig = go.Figure()
    fig.add_bar(x=x, y=bars, name=bar_name, marker=dict(color=p.green_lt if not tilt else p.green, cornerradius=3),
                hovertemplate="%{y:,.0f}")
    fig.add_scatter(x=x, y=line, name=line_name, yaxis="y2", mode="lines+markers",
                    line=dict(color=p.amber, width=3), marker=dict(size=6), hovertemplate="%{y:.2f}%")
    fig.update_layout(yaxis2=dict(overlaying="y", side="right", showgrid=False, ticksuffix="%", range=line_range))
    if tilt:
        fig.update_xaxes(tickangle=-35)
    return _finish(fig, height)


def area(x, y, name: str, height: int = 340) -> go.Figure:
    p = palette()
    fig = go.Figure(go.Scatter(x=pd.Series(x).astype(str), y=y, fill="tozeroy", mode="lines", name=name,
                               line=dict(color=p.green, width=3), fillcolor=p.fill_alpha, hovertemplate="%{y:,.0f}"))
    return _finish(fig, height)


def columns(x, y, tone: str = "green", height: int = 280, labels=None, hide_y: bool = False) -> go.Figure:
    """Plain column chart (optional text labels above the bars)."""
    p = palette()
    solid, tint = _tone(p, tone)
    fig = go.Figure(go.Bar(x=pd.Series(x).astype(str), y=y, marker=dict(color=solid if labels is not None else tint,
                                                                      cornerradius=4),
                           text=labels, textposition="outside" if labels is not None else None,
                           cliponaxis=False, hovertemplate="%{y:,.0f}<extra></extra>"))
    if hide_y:
        fig.update_yaxes(visible=False)
    fig.update_layout(hovermode="closest", margin=dict(t=24))
    return _finish(fig, height)


def grouped(x, series: dict, height: int = 330) -> go.Figure:
    p = palette()
    colors = [p.green, p.amber, p.teal, p.red]
    fig = go.Figure()
    for (name, y), c in zip(series.items(), colors):
        fig.add_bar(x=pd.Series(x).astype(str), y=y, name=name, marker=dict(color=c, cornerradius=3),
                    hovertemplate="%{y:,.0f}")
    fig.update_layout(barmode="group", bargap=0.25, bargroupgap=0.06)
    return _finish(fig, height)


def heatmap(z: pd.DataFrame, height: int = 430) -> go.Figure:
    p = palette()
    fig = go.Figure(go.Heatmap(z=z.values, x=z.columns.astype(str), y=z.index.astype(str), xgap=3, ygap=3,
                               colorscale=[[0, p.heat[0]], [.5, p.heat[1]], [1, p.heat[2]]],
                               text=np.round(z.values, 1), texttemplate="%{text}", textfont=dict(size=10.5),
                               colorbar=dict(thickness=10, ticksuffix="%", outlinewidth=0),
                               hovertemplate="%{y} · %{x}<br><b>%{z:.2f}%</b><extra></extra>"))
    fig.update_yaxes(autorange="reversed", showgrid=False)
    fig.update_xaxes(tickangle=-35, side="bottom")
    fig.update_layout(hovermode="closest")
    return _finish(fig, height)


def _is_text_axis(fig: go.Figure) -> bool:
    """YearMonth labels like '2024-05' must stay categories, not be parsed as dates."""
    for tr in fig.data:
        x = getattr(tr, "x", None)
        if x is not None and len(x) and getattr(tr, "orientation", None) != "h" and isinstance(x[0], str):
            return True
    return False


def _tone(p: Palette, tone: str) -> tuple[str, str]:
    return {"green": (p.green, p.green_lt), "amber": (p.amber, p.amber_lt), "red": (p.red, p.red_lt),
            "red_amber": (p.red, p.amber_lt)}[tone]
