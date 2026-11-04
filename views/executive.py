import pandas as pd
import streamlit as st

import charts
import filters
import ui
from engine import group_kpis, plan_next_month

ctx = filters.current()
S, K, mon = ctx.S, ctx.K, ctx.mon.copy()

ui.hero("Crescent Grocery", "Inventory, promotions & product profitability · executive overview")


def metric(col, label, key, value, *, pts=False, inverse=False, help=None):
    ui.kpi(col, label, value, ctx.delta(key, pts), inverse=inverse, chart=ctx.spark.get(key), help=help,
           compare=ctx.cmp_label)


c = st.columns(4)
metric(c[0], "Net sales (SAR)", "net", ui.compact(K["net"]), help=f"{K['net']:,.2f} SAR")
metric(c[1], "Gross margin", "gm_pct", f"{K['gm_pct']:.2f}%", pts=True)
metric(c[2], "Discount rate", "disc_rate", f"{K['disc_rate']:.2f}%", pts=True, inverse=True)
metric(c[3], "Units sold", "units", f"{K['units']:,.0f}")
c = st.columns(4)
metric(c[0], "Return rate", "return_rate", f"{K['return_rate']:.2f}%", pts=True, inverse=True)
metric(c[1], "Stockout rate", "stockout_rate", f"{K['stockout_rate']:.2f}%", pts=True, inverse=True)
metric(c[2], "Avg basket (SAR)", "avg_basket", f"{K['avg_basket']:,.2f}")
metric(c[3], "Promo share", "promo_share", f"{K['promo_share']:.2f}%", pts=True)
st.caption("Values cover the whole selection. Deltas compare with the same period last year or, when the "
           "selection starts in the first year, the latest full year with the one before · sparklines = monthly trend.")

# ---- auto insights
cat_k = group_kpis(S, "CategoryName")
st_k = group_kpis(S, "StoreName")
best_m = mon.loc[mon.NetSales.idxmax()]
low_c = cat_k.sort_values("MarginPct").iloc[0]
top_s = st_k.sort_values("NetSales", ascending=False).iloc[0]
ui.section("What stands out", "Generated from the current selection")
c = st.columns(3)
ui.insight(c[0], "trending_up", "Peak month",
           f"**{best_m.YearMonth}** led with **{ui.compact(best_m.NetSales)}** SAR net sales.")
ui.insight(c[1], "storefront", "Top store",
           f"**{top_s.StoreName}** drives **{top_s.NetSales / K['net'] * 100:.1f}%** of net sales.")
ui.insight(c[2], "warning", "Margin watch",
           f"**{low_c.CategoryName}** has the lowest margin at **{low_c.MarginPct:.2f}%**.")

# ---- trends
ui.section("Trends")
l, r = st.columns(2)
with l, ui.card("Monthly net sales & margin %", "Bars = net sales (SAR) · line = gross margin %"):
    charts.show(charts.bar_line(mon.YearMonth, mon.NetSales, mon.MarginPct, "Net sales", "Margin %"))
with r, ui.card("Cumulative net sales", "Running total across the selected period"):
    charts.show(charts.area(mon.YearMonth, mon.NetSales.cumsum(), "Cumulative"))

l, r = st.columns(2)
q = group_kpis(S, "Quarter").sort_values("Quarter")
with l, ui.card("Net sales by quarter", "All years combined · strongest highlighted"):
    charts.show(charts.vbar(q, "Quarter", "NetSales", fmt=",.3s"))
y = group_kpis(S, "Year")
y["YoY"] = y.NetSales.pct_change() * 100
with r, ui.card("Net sales by year", "Label = year-on-year growth"):
    labels = [f"{v:+.2f}% YoY" if pd.notna(v) else "" for v in y.YoY]
    charts.show(charts.columns(y.Year, y.NetSales, height=300, labels=labels, hide_y=True))

# ---- one-page scorecard (Q39)
ui.section("Executive scorecard", color="orange", sub="Q39 · next-month plan = average of the last 3 months × 1.08")
tc = cat_k.sort_values("NetSales", ascending=False).iloc[0]
c = st.columns(4)
ui.kpi(c[0], "Top store", top_s.StoreName.replace("Crescent Grocery", "Store"),
       help=f"{top_s.StoreName} · {top_s.NetSales:,.0f} SAR net sales")
ui.kpi(c[1], "Top category", tc.CategoryName, help=f"{tc.NetSales:,.0f} SAR net sales")
ui.kpi(c[2], "Next-month plan (SAR)", f"{plan_next_month(S):,.0f}")
ui.kpi(c[3], "Lines / returns", f"{K['lines']:,} / {K['returns']:,}")
