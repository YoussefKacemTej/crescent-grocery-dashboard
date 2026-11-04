import streamlit as st

import charts
import filters
import ui
from engine import group_kpis

CC = st.column_config
ctx = filters.current()
S, K = ctx.S, ctx.K

ui.page_header("Products & suppliers", "Category mix, product concentration and supplier contribution")

cat = group_kpis(S, "CategoryName").sort_values("NetSales", ascending=False)
l, r = st.columns(2)
with l, ui.card("Net sales by category"):
    charts.show(charts.hbar(cat, "NetSales", "CategoryName", fmt=",.3s"))
with r, ui.card("Gross margin % by category", "Weakest first: these need attention"):
    charts.show(charts.hbar(cat.sort_values("MarginPct"), "MarginPct", "CategoryName", fmt=".2f", suffix="%",
                            tone="red_amber"))

ui.section("Pareto: product concentration", "How much of net sales the top products generate")
top_n = st.slider("Top N products", 5, 50, 10, key="top_n")
pr = group_kpis(S, ["ProductID", "ProductName"]).sort_values(["NetSales", "ProductID"], ascending=[False, True])
tn = pr.head(top_n)
cum = tn.NetSales.cumsum() / K["net"] * 100
with ui.card(f"Top {top_n} products = {tn.NetSales.sum() / K['net'] * 100:.2f}% of net sales",
             "Bars = net sales · line = cumulative share"):
    charts.show(charts.bar_line(tn.ProductName, tn.NetSales, cum, "Net sales", "Cumulative share", height=400,
                                line_range=[0, max(100, float(cum.max()))], tilt=True))

l, r = st.columns(2)
br = group_kpis(S, "BrandType")
with l, ui.card("Margin %: private label vs national brand"):
    charts.show(charts.vbar(br, "BrandType", "MarginPct", suffix="%", tone="amber", height=340))
su = group_kpis(S, "SupplierName").sort_values("NetSales", ascending=False).head(10)
with r, ui.card("Top 10 suppliers by net sales"):
    charts.show(charts.hbar(su, "NetSales", "SupplierName", fmt=",.3s", height=340))

ui.section("Fastest-moving products", "Top 10 by units sold")
fm = pr.sort_values(["Units", "ProductID"], ascending=[False, True]).head(10)[["ProductName", "Units", "NetSales", "MarginPct"]]
st.dataframe(fm, hide_index=True, width="stretch", column_config={
    "ProductName": CC.TextColumn("Product"),
    "Units": CC.ProgressColumn("Units", format="localized", min_value=0, max_value=float(fm.Units.max()), color="green"),
    "NetSales": CC.NumberColumn("Net sales (SAR)", format="localized"),
    "MarginPct": CC.NumberColumn("Margin %", format="%.2f")})
