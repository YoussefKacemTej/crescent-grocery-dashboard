import streamlit as st

import charts
import filters
import ui
from engine import group_kpis

CC = st.column_config
S = filters.current().S

ui.page_header("Stores & channels", "Where sales, margin and stockouts concentrate across the network")

st_g = group_kpis(S, ["StoreID", "StoreName"]).sort_values("NetSales", ascending=False)
l, r = st.columns(2)
with l, ui.card("Net sales by store", "Leader highlighted"):
    charts.show(charts.hbar(st_g, "NetSales", "StoreName", fmt=",.3s"))
with r, ui.card("Gross margin % by store", "Highest margin first"):
    charts.show(charts.hbar(st_g.sort_values("MarginPct", ascending=False), "MarginPct", "StoreName",
                            fmt=".2f", suffix="%", tone="amber"))

l, r = st.columns([3, 2])
with l, ui.card("Stockout rate %, store × category", "Darker = more stockouts"):
    heat = S.groupby(["StoreName", "CategoryName"], observed=True).StockoutFlag.mean().mul(100).unstack()
    charts.show(charts.heatmap(heat))
ch = group_kpis(S, "ChannelName").sort_values("ReturnRate", ascending=False)
with r, ui.card("Return rate % by channel", "Highest channel highlighted"):
    charts.show(charts.vbar(ch, "ChannelName", "ReturnRate", suffix="%", tone="red", height=430))

ui.section("Store scorecard")
tbl = st_g[["StoreName", "NetSales", "MarginPct", "StockoutRate", "ReturnRate", "Units"]]
st.dataframe(tbl, hide_index=True, width="stretch", column_config={
    "StoreName": CC.TextColumn("Store"),
    "NetSales": CC.ProgressColumn("Net sales (SAR)", format="localized", min_value=0,
                                  max_value=float(tbl.NetSales.max()), color="green"),
    "MarginPct": CC.NumberColumn("Margin %", format="%.2f"),
    "StockoutRate": CC.NumberColumn("Stockout %", format="%.2f"),
    "ReturnRate": CC.NumberColumn("Return %", format="%.2f"),
    "Units": CC.NumberColumn("Units", format="localized")})
