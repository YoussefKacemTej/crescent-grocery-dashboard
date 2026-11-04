import streamlit as st

import charts
import filters
import ui
from engine import action_matrix, working_capital

CC = st.column_config
ctx = filters.current()
S, INV, inv_f = ctx.S, ctx.INV, ctx.inv_f

ui.page_header("Inventory", "Stock position, reorder risk and working capital at the selected month-end")

if INV.empty:
    st.info("No inventory snapshot for the current filters.", icon=":material/inventory:")
    st.stop()

snap = str(ctx.f.snap)
st.badge(f"Snapshot {snap[:4]}-{snap[4:6]}-{snap[6:]}", icon=":material/event:", color="blue")

inv_val = INV.InventoryCostSAR.sum()
below, pop = int((INV.OnHandUnits <= INV.ReorderPointUnits).sum()), len(INV)
snap_ym = INV.YearMonth.iloc[0]
months = sorted(ctx.wc_sales.loc[ctx.wc_sales.YearMonth <= snap_ym, "YearMonth"].unique().tolist())
tot, wc = working_capital(ctx.wc_sales, INV, months[-3:])

c = st.columns(4)
ui.kpi(c[0], "Inventory value (SAR)", ui.compact(inv_val), help=f"{inv_val:,.2f} SAR at cost")
ui.kpi(c[1], "Below reorder", f"{below:,} / {pop:,}", help=f"{below / pop * 100:.1f}% of store-product lines at or below the reorder point")
ui.kpi(c[2], "Avg days of supply", f"{INV.DaysOfSupply.mean():.2f}")
ui.kpi(c[3], "Inventory / 3-mo sales", f"{tot:,.0f}%", help=f"{tot:,.2f}% · inventory cost vs net sales of the last 3 months")

ui.section("Stock position")
l, r = st.columns(2)
trend = inv_f.groupby("YearMonth", observed=True).InventoryCostSAR.sum().reset_index()
with l, ui.card("Month-end inventory value (cost)"):
    charts.show(charts.area(trend.YearMonth, trend.InventoryCostSAR, "Inventory"))
ds = INV.groupby("StoreName", observed=True).DaysOfSupply.mean().sort_values().reset_index()
with r, ui.card("Avg days of supply by store", "Lowest first: lowest = highest stockout risk"):
    charts.show(charts.hbar(ds, "DaysOfSupply", "StoreName", fmt=".2f", tone="red_amber", height=340))

ui.section("Category inventory-profit action matrix", color="red", sub=
           "Score = sum of 4 ranks (1 = worst): stockout rate ↓, lines below reorder ↓, margin % ↑, "
           "days of supply ↑. Lowest score = act first.")
am = action_matrix(S, INV)
am["Priority"] = [["Act first"] if i < 3 else (["Watch"] if i < 6 else ["Healthy"]) for i in range(len(am))]
st.dataframe(am[["CategoryName", "Priority", "StockoutRate", "BelowReorder", "AvgDaysOfSupply", "MarginPct", "Score"]],
             hide_index=True, width="stretch", column_config={
                 "CategoryName": CC.TextColumn("Category"),
                 "Priority": ui.status_column("Priority", ["Act first", "Watch", "Healthy"], ["red", "orange", "green"]),
                 "StockoutRate": CC.NumberColumn("Stockout %", format="%.2f"),
                 "BelowReorder": CC.NumberColumn("Below reorder", format="localized"),
                 "AvgDaysOfSupply": CC.NumberColumn("Avg days of supply", format="%.2f"),
                 "MarginPct": CC.NumberColumn("Margin %", format="%.2f"),
                 "Score": CC.ProgressColumn("Score", format="%.1f", min_value=0, max_value=float(am.Score.max()),
                                            color="orange")})

ui.section("Working capital", "Inventory vs net sales of the 3 months to the snapshot")
st.dataframe(wc, hide_index=True, width="stretch", column_config={
    "CategoryName": CC.TextColumn("Category"),
    "InvToQtrSales%": CC.ProgressColumn("Inventory / quarter sales %", format="%.2f", min_value=0,
                                        max_value=float(wc["InvToQtrSales%"].max()), color="green")})
