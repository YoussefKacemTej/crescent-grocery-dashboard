"""
filters.py - sidebar slicers (= Power BI slicers) and the cached, filtered data slice every page reads.

Flow: app.py calls render_sidebar() once per run -> Filters (hashable) is stored in session_state ->
pages call current() -> get_slice(filters) is computed once per filter combination and cached.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pandas as pd
import streamlit as st

from engine import group_kpis, kpis, load_data

PROMO_MODES = ("All lines", "Promoted only", "Non-promoted only")


# ------------------------------------------------------------------ cached data
@st.cache_data(show_spinner="Loading data…")
def get_data() -> dict:
    return load_data()


def date_bounds() -> tuple[date, date]:
    s = get_data()["sales"]
    return s.Date.min().date(), s.Date.max().date()


# ------------------------------------------------------------------ filter state
@dataclass(frozen=True)
class Filters:
    start: date
    end: date
    stores: tuple = ()
    cats: tuple = ()
    chans: tuple = ()
    brands: tuple = ()
    promo: str = PROMO_MODES[0]
    snap: int | None = None

    def active_count(self) -> int:
        dmin, dmax = date_bounds()
        return (sum(bool(v) for v in (self.stores, self.cats, self.chans, self.brands))
                + (self.promo != PROMO_MODES[0]) + ((self.start, self.end) != (dmin, dmax)))


def _dim_filter(df: pd.DataFrame, f: Filters) -> pd.DataFrame:
    """Slicers that exist on both facts (store / category / brand)."""
    if f.stores:
        df = df[df.StoreName.isin(f.stores)]
    if f.cats:
        df = df[df.CategoryName.isin(f.cats)]
    if f.brands:
        df = df[df.BrandType.isin(f.brands)]
    return df


def filter_sales(df: pd.DataFrame, f: Filters, start: date, end: date) -> pd.DataFrame:
    df = _dim_filter(df, f)
    df = df[df.Date.between(pd.Timestamp(start), pd.Timestamp(end))]
    if f.chans:
        df = df[df.ChannelName.isin(f.chans)]
    if f.promo == PROMO_MODES[1]:
        df = df[df.IsPromo]
    elif f.promo == PROMO_MODES[2]:
        df = df[~df.IsPromo]
    return df


def _prior_year(d0: date, d1: date) -> tuple[date, date]:
    """Same period one year earlier (SAMEPERIODLASTYEAR); 29 Feb -> 28 Feb."""
    shift = lambda d: d.replace(year=d.year - 1, day=min(d.day, 28) if (d.month, d.day) == (2, 29) else d.day)
    return shift(d0), shift(d1)


@st.cache_data(show_spinner=False)
def snapshot_keys(stores: tuple, cats: tuple, brands: tuple, end: date) -> list[int]:
    inv = _dim_filter(get_data()["inv"], Filters(end, end, stores, cats, (), brands))
    return sorted(inv.loc[inv.Date <= pd.Timestamp(end), "SnapshotDateKey"].unique().tolist())


# ------------------------------------------------------------------ the slice
@dataclass(frozen=True)
class Slice:
    f: Filters
    S: pd.DataFrame            # filtered sales
    SP: pd.DataFrame           # same filters, same period last year
    inv_f: pd.DataFrame        # inventory, dim filters + snapshots up to the end date
    INV: pd.DataFrame          # selected snapshot
    wc_sales: pd.DataFrame     # sales from the first date to the end date (working capital)
    K: dict
    KP: dict | None
    mon: pd.DataFrame          # group_kpis by YearMonth, chronological
    prior: tuple[date, date]
    spark: dict = field(default_factory=dict)
    # what the KPI deltas compare: same period last year, or (fallback) the latest two full years
    dK: dict | None = None
    dKP: dict | None = None
    cmp_label: str | None = None

    def delta(self, key: str, pts: bool = False) -> str | None:
        """Change vs the comparison base: relative % for amounts, points for rates."""
        cur, base = self.dK, self.dKP
        if not cur or not base or not base[key] or pd.isna(base[key]) or pd.isna(cur[key]):
            return None
        diff = cur[key] - base[key]
        return f"{diff:+.2f} pts" if pts else f"{(cur[key] / base[key] - 1) * 100:+.1f}%"


@st.cache_data(show_spinner=False, max_entries=64)
def get_slice(f: Filters) -> Slice:
    D = get_data()
    sales, inv = D["sales"], D["inv"]
    dmin, _ = date_bounds()

    S = filter_sales(sales, f, f.start, f.end)
    p0, p1 = _prior_year(f.start, f.end)
    SP = filter_sales(sales, f, p0, p1) if p0 >= dmin else sales.iloc[0:0]

    inv_f = _dim_filter(inv, f)
    inv_f = inv_f[inv_f.Date <= pd.Timestamp(f.end)]
    INV = inv_f[inv_f.SnapshotDateKey == f.snap] if f.snap else inv_f.iloc[0:0]

    mon = group_kpis(S, "YearMonth").sort_values("YearMonth") if len(S) else pd.DataFrame()
    spark = {}
    if len(S):
        promo_m = (S.NetSalesSAR.where(S.IsPromo, 0).groupby(S.YearMonth, observed=True).sum()
                   / S.groupby("YearMonth", observed=True).NetSalesSAR.sum()).sort_index() * 100
        spark = {"net": mon.NetSales, "gm_pct": mon.MarginPct, "disc_rate": mon.DiscountRate, "units": mon.Units,
                 "return_rate": mon.ReturnRate, "stockout_rate": mon.StockoutRate,
                 "avg_basket": mon.NetSales / mon.Lines, "promo_share": promo_m}

    K = kpis(S) if len(S) else {}
    KP = kpis(SP) if len(SP) else None
    dK, dKP, label = _comparison(S, K, KP, f)
    return Slice(f=f, S=S, SP=SP, inv_f=inv_f, INV=INV, wc_sales=filter_sales(sales, f, dmin, f.end),
                 K=K, KP=KP, mon=mon, prior=(p0, p1), spark=spark, dK=dK, dKP=dKP, cmp_label=label)


def _comparison(S: pd.DataFrame, K: dict, KP: dict | None, f: Filters):
    """Same period last year when it exists; otherwise the latest full year vs the one before,
    if the selection covers two full calendar years (e.g. the default 2023-2025 view -> 2025 vs 2024)."""
    if KP:
        return K, KP, "vs same period last year"
    full = [y for y in sorted(S.Year.unique()) if f.start <= date(y, 1, 1) and date(y, 12, 31) <= f.end]
    if len(full) >= 2 and full[-2] == full[-1] - 1:
        y = full[-1]
        return kpis(S[S.Year == y]), kpis(S[S.Year == y - 1]), f"{y} vs {y - 1}"
    return None, None, None


def current() -> Slice:
    """The slice for the filters chosen in the sidebar on this run."""
    return get_slice(st.session_state["filters"])


# ------------------------------------------------------------------ sidebar
_KEYS = ("f_date", "f_store", "f_cat", "f_chan", "f_brand", "f_promo", "f_snap")


def reset_filters() -> None:
    for k in _KEYS:
        st.session_state.pop(k, None)


def _side_label(text: str) -> None:
    st.sidebar.caption(f"**{text.upper()}**")


def render_sidebar() -> Filters:
    sales = get_data()["sales"]
    dmin, dmax = date_bounds()
    opts = lambda col: list(sales[col].cat.categories)

    st.session_state.setdefault("f_date", (dmin, dmax))
    st.session_state.setdefault("f_promo", PROMO_MODES[0])

    sb = st.sidebar
    sb.caption("Inventory, promotions & product profitability · DD-RET-002")

    _side_label("Period")
    rng = sb.date_input("Date range", min_value=dmin, max_value=dmax, key="f_date")
    d0, d1 = rng if isinstance(rng, (tuple, list)) and len(rng) == 2 else (dmin, dmax)

    promo = sb.segmented_control("Promotion", PROMO_MODES, key="f_promo", required=True,
                                 format_func={"All lines": "All", "Promoted only": "Promo", "Non-promoted only": "No promo"}.get,
                                 width="stretch") or PROMO_MODES[0]

    n_dim = sum(bool(st.session_state.get(k)) for k in ("f_store", "f_cat", "f_chan", "f_brand"))
    with sb.expander(f"More slicers · {n_dim} active" if n_dim else "More slicers", expanded=bool(n_dim),
                     icon=":material/tune:"):
        stores = st.multiselect("Store", opts("StoreName"), key="f_store", placeholder="All stores")
        cats = st.multiselect("Category", opts("CategoryName"), key="f_cat", placeholder="All categories")
        chans = st.multiselect("Channel", opts("ChannelName"), key="f_chan", placeholder="All channels")
        brands = st.multiselect("Brand type", opts("BrandType"), key="f_brand", placeholder="All brands")

    _side_label("Inventory")
    keys = snapshot_keys(tuple(stores), tuple(cats), tuple(brands), d1)
    if st.session_state.get("f_snap") not in keys:
        st.session_state.pop("f_snap", None)
    snap = sb.selectbox("Snapshot (month-end)", keys, index=len(keys) - 1 if keys else None, key="f_snap",
                        format_func=lambda k: f"{str(k)[:4]}-{str(k)[4:6]}-{str(k)[6:]}",
                        disabled=not keys, placeholder="No snapshot in range")

    sb.button("Reset all filters", icon=":material/restart_alt:", on_click=reset_filters, width="stretch")

    f = Filters(d0, d1, tuple(stores), tuple(cats), tuple(chans), tuple(brands), promo, snap)
    st.session_state["filters"] = f
    return f
