"""
ui.py - small layout components built on native Streamlit elements.
Colours come from .streamlit/config.toml (light + dark), so nothing here hard-codes a theme.
"""
from __future__ import annotations

import re
from contextlib import contextmanager
from pathlib import Path

import pandas as pd
import streamlit as st

# Only what config.toml cannot express: a raised "surface" colour for cards and metrics.
# Switching theme in the menu does NOT rerun the script, so the surface cannot be chosen in Python
# (the theme reported to Python would be stale). It is derived in the browser from the current text colour:
# dark text (light theme) -> white, light text (dark theme) -> a deep green a step above the page.
_CSS = """
<style>
.block-container { max-width: 1480px; padding-top: 3.6rem; }
div[class*="st-key-card-"], [data-testid="stMetric"] {
  background: transparent;
  background: oklch(from currentColor calc(1.27 - 1.08 * l) 0.014 170);
}
[data-testid="stMetricValue"] { font-weight: 800; letter-spacing: -.02em; font-variant-numeric: tabular-nums;
  font-size: 2rem; }
[data-testid="stMetricLabel"] p { font-size: .75rem; font-weight: 700; letter-spacing: .06em; text-transform: uppercase;
  opacity: .8; }
</style>
"""
_LOGO = Path(__file__).parent / "assets" / "logo.svg"


def css() -> None:
    st.html(_CSS)
    st.logo(str(_LOGO), size="large")


def compact(v: float | None, dec: int = 2) -> str:
    """3342923 -> '3.34M'."""
    if v is None or pd.isna(v):
        return "–"
    a = abs(v)
    for lim, s in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if a >= lim:
            return f"{v / lim:,.{dec}f}{s}"
    return f"{v:,.0f}"


def page_header(title: str, subtitle: str = "") -> None:
    """Page title + context badges (period, comparison, filters) shared by every page."""
    ctx = st.session_state.get("header_ctx", {})
    st.markdown(f"## {title}")
    if subtitle:
        st.caption(subtitle)
    with st.container(horizontal=True, gap="small"):
        if ctx:
            st.badge(ctx["period"], icon=":material/calendar_month:", color="green")
            st.badge(ctx["compare"], icon=":material/compare_arrows:", color="gray")
            n = ctx["n_filters"]
            st.badge(f"{n} filter{'s' if n != 1 else ''} active" if n else "No filters",
                     icon=":material/filter_alt:", color="orange" if n else "gray")
        st.badge("Amounts in SAR", icon=":material/payments:", color="gray")


def kpi(col, label: str, value: str, delta: str | None = None, *, inverse: bool = False, chart=None,
        help: str | None = None, compare: str | None = None) -> None:
    """Bordered st.metric. inverse=True: a rise is bad (rates like returns / stockouts).
    compare: what the delta is measured against, shown next to it (e.g. '2025 vs 2024')."""
    data = None
    if chart is not None:
        data = [float(v) for v in chart if pd.notna(v)]
        data = data if len(data) >= 2 else None
    col.metric(label, value, delta, delta_color="inverse" if inverse else "normal", border=True,
               chart_data=data, chart_type="area", help=help, delta_description=compare if delta else None)


def section(title: str, sub: str = "", color: str = "green") -> None:
    st.space("small")
    st.subheader(title, divider=color)
    if sub:
        st.caption(sub)


_HERO_BG = "linear-gradient(120deg,#0A3F34 0%,#0F5E4D 58%,#1B8A72 100%)"   # same in light and dark


def hero(title: str, subtitle: str) -> None:
    """Branded banner for the landing page (other pages use page_header)."""
    ctx = st.session_state.get("header_ctx", {})
    bg, accent, soft = _HERO_BG, "#F4D9A4", "rgba(255,255,255,.8)"
    n = ctx.get("n_filters", 0)
    chips = [ctx.get("period", ""), ctx.get("compare", ""),
             f"{n} filter{'s' if n != 1 else ''} active" if n else "No filters", "Amounts in SAR"]
    chip_html = "".join(f'<span class="hc">{c}</span>' for c in chips if c)
    st.html(f"""
<style>
.hero {{ position:relative; overflow:hidden; border-radius:20px; padding:26px 30px; color:#fff; background:{bg};
  box-shadow:0 10px 30px rgba(10,63,52,.18); font-family:inherit; }}
.hero::after {{ content:""; position:absolute; right:-60px; top:-80px; width:240px; height:240px; border-radius:50%;
  box-shadow:30px 14px 0 0 rgba(255,255,255,.08); }}
.hero .eb {{ font-size:11.5px; font-weight:700; letter-spacing:.14em; text-transform:uppercase; color:{accent}; }}
.hero h1 {{ font-size:30px; font-weight:800; letter-spacing:-.02em; margin:6px 0 4px; color:#fff; padding:0; line-height:1.15; }}
.hero p {{ margin:0; color:{soft}; font-size:14px; }}
.hero .chips {{ display:flex; flex-wrap:wrap; gap:8px; margin-top:16px; }}
.hero .hc {{ font-size:12px; font-weight:600; padding:5px 11px; border-radius:999px; background:rgba(255,255,255,.13);
  border:1px solid rgba(255,255,255,.2); color:#fff; }}
</style>
<div class="hero"><div class="eb">DD-RET-002 · Retail analytics · Level 2</div>
<h1>{title}</h1><p>{subtitle}</p><div class="chips">{chip_html}</div></div>""")


def status_column(label: str, options: list[str], colors: list[str]):
    """Read-only coloured chip column; cell values must be one-item lists, e.g. ['Act first']."""
    return st.column_config.MultiselectColumn(label, options=options, color=colors, disabled=True)


@contextmanager
def card(title: str, sub: str = ""):
    """Bordered container with a title; use as `with ui.card("..."):`."""
    with st.container(border=True, key=f"card-{re.sub(r'[^a-z0-9]+', '-', title.lower())}"):
        st.markdown(f"**{title}**")
        if sub:
            st.caption(sub)
        yield


def insight(col, icon: str, title: str, body: str) -> None:
    """icon: a material icon name such as 'trending_up'."""
    with col.container(border=True, height="stretch", key=f"card-insight-{re.sub(r'[^a-z0-9]+', '-', title.lower())}"):
        st.markdown(f":material/{icon}: **{title}**")
        st.markdown(body)
