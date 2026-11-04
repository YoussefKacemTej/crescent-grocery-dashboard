import streamlit as st

import charts
import filters
import ui
from engine import group_kpis, kpis

CC = st.column_config
ctx = filters.current()
S, K = ctx.S, ctx.K

ui.page_header("Promotions & returns", "Margin cost of promotions and where returns run above the chain")

if S.IsPromo.any() and (~S.IsPromo).any():
    pr_k, np_k = kpis(S[S.IsPromo]), kpis(S[~S.IsPromo])
    c = st.columns(3)
    ui.kpi(c[0], "Promoted margin", f"{pr_k['gm_pct']:.2f}%")
    ui.kpi(c[1], "Non-promoted margin", f"{np_k['gm_pct']:.2f}%")
    ui.kpi(c[2], "Margin dilution", f"{np_k['gm_pct'] - pr_k['gm_pct']:.2f} pts",
           help="Non-promoted margin % minus promoted margin %")
else:
    st.caption("Promoted vs non-promoted comparison needs both kinds of lines in the selection.")

ui.section("Promotion performance", color="orange")
pt = group_kpis(S[S.IsPromo], "PromotionType")
base = kpis(S[~S.IsPromo]) if (~S.IsPromo).any() else None
if pt.empty:
    st.info("No promoted lines in the current selection.", icon=":material/sell:")
else:
    l, r = st.columns(2)
    with l, ui.card("Net sales & discount by promotion type",
                    f"Promoted lines only · non-promoted lines: {ui.compact(base['net'])} SAR net sales"
                    if base else "Promoted lines only"):
        charts.show(charts.grouped(pt.PromotionType, {"Net sales": pt.NetSales, "Discount": pt.Discount}))
    with r, ui.card("Margin % by promotion type",
                    "Dashed line = margin on non-promoted lines" if base else "Highest highlighted"):
        ref = (base["gm_pct"], f"No promotion {base['gm_pct']:.2f}%") if base else None
        charts.show(charts.vbar(pt, "PromotionType", "MarginPct", suffix="%", tone="amber", height=330, ref=ref))

ui.section("Return-rate exceptions by category", "Categories above the chain average need a closer look", color="red")
rc = group_kpis(S, "CategoryName").sort_values("ReturnRate", ascending=False)
rc["Status"] = [["Above chain avg"] if v > K["return_rate"] else ["Within avg"] for v in rc.ReturnRate]
l, r = st.columns([3, 2])
with l:
    st.dataframe(rc[["CategoryName", "ReturnRate", "Status", "Returns", "Lines"]], hide_index=True, width="stretch",
                 column_config={"CategoryName": CC.TextColumn("Category"),
                                "Status": ui.status_column("Status", ["Above chain avg", "Within avg"], ["red", "green"]),
                                "ReturnRate": CC.ProgressColumn("Return rate %", format="%.2f", min_value=0,
                                                                max_value=float(rc.ReturnRate.max()) * 1.1, color="red"),
                                "Returns": CC.NumberColumn(format="localized"),
                                "Lines": CC.NumberColumn(format="localized")})
with r:
    n_above = int((rc.ReturnRate > K["return_rate"]).sum())
    ui.kpi(st, "Chain return rate", f"{K['return_rate']:.2f}%")
    st.caption(f"**{n_above} of {len(rc)}** categories are above the chain average.")
    ui.kpi(st, "Same-day fulfilment", f"{K['same_day']:.2f}%",
           help="Fulfilment date = transaction date (inactive FulfillmentDateKey relationship)")

# returns by RETURN month = inactive relationship (USERELATIONSHIP)
rm = S[S.ReturnFlag].groupby("ReturnYearMonth").size().rename("Returns").reset_index().sort_values("ReturnYearMonth")
with ui.card("Returned transactions by return month", "Uses the inactive return-date relationship (USERELATIONSHIP)"):
    charts.show(charts.columns(rm.ReturnYearMonth, rm.Returns, tone="red"))
