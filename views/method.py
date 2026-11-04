import streamlit as st

import charts
import filters
import ui

D = filters.get_data()
p = charts.palette()

st.markdown("## Method & data model")
st.caption("How the numbers are built: the star schema, the relationships used, and the working assumptions.")

# ------------------------------------------------------------------ data model (rows from the loaded CSVs)
ROWS = {"FactSalesTransactions": len(D["sales"]), "FactInventorySnapshot": len(D["inv"]),
        "DimDate": len(D["date"]), "DimStore": len(D["store"]), "DimProduct": len(D["product"]),
        "DimSupplier": len(D["supplier"]), "DimPromotion": len(D["promo"]), "DimChannel": len(D["channel"])}


def node(name: str, fact: bool) -> str:
    fill, font = (p.green, "#FFFFFF") if fact else ("transparent", p.teal)   # reads on light and dark
    return (f'"{name}" [label=<<b>{name}</b><br/><font point-size="10">{ROWS[name]:,} rows</font>>, '
            f'fillcolor="{fill}", fontcolor="{font}", color="{p.green if not fact else fill}"];')


ACTIVE = [("FactSalesTransactions", "DimDate", "TransactionDateKey"),
          ("FactSalesTransactions", "DimStore", "StoreID"),
          ("FactSalesTransactions", "DimProduct", "ProductID"),
          ("FactSalesTransactions", "DimPromotion", "PromotionID"),
          ("FactSalesTransactions", "DimChannel", "ChannelID"),
          ("FactInventorySnapshot", "DimDate", "SnapshotDateKey"),
          ("FactInventorySnapshot", "DimStore", "StoreID"),
          ("FactInventorySnapshot", "DimProduct", "ProductID"),
          ("DimProduct", "DimSupplier", "SupplierID")]
INACTIVE = [("FactSalesTransactions", "DimDate", "FulfillmentDateKey"),
            ("FactSalesTransactions", "DimDate", "ReturnDateKey")]

edge = lambda a, b, lbl, style: (f'"{a}" -> "{b}" [label=" {lbl} ", style={style}, '
                                 f'color="{p.slate if style == "solid" else p.amber}", fontcolor="{p.slate}"];')
dot = "\n".join([
    "digraph G {",
    f'rankdir=LR; bgcolor="transparent"; nodesep=0.35; ranksep=1.1;',
    f'node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=12, margin="0.18,0.08"];',
    f'edge [fontname="Helvetica", fontsize=9, arrowsize=0.6];',
    *[node(n, n.startswith("Fact")) for n in ROWS],
    *[edge(a, b, l, "solid") for a, b, l in ACTIVE],
    *[edge(a, b, l, "dashed") for a, b, l in INACTIVE],
    "}",
])

ui.section("Star schema")
with ui.card("Relationships", "Solid = active (many-to-one, single direction) · dashed = inactive, "
                              "used only where a question asks for it (USERELATIONSHIP)"):
    st.graphviz_chart(dot, width="stretch")

# ------------------------------------------------------------------ assumptions + pipeline
l, r = st.columns(2)
with l:
    ui.section("Working assumptions", "From the Question Book")
    st.markdown("""
- **Reporting period:** 2023-01-01 → 2025-12-31 (synthetic data).
- **PromotionID 1 = no promotion.** Every other ID counts as a promoted line.
- **Ties:** when two rows rank equal, the lowest ID (or key) wins.
- **Zero denominators** are excluded: rates return blank, never an error.
- **Inactive dates:** returns by month use `ReturnDateKey`; same-day fulfilment compares
  `FulfillmentDateKey` with `TransactionDateKey`.
- **Latest inventory** = the most recent month-end snapshot (`20251201`).
- **Q33 rounding:** the book prints 79.30%; the data gives 79.31% (23,794 / 30,000).
""")
with r:
    ui.section("How the app computes", "Same logic as the Power BI model")
    st.markdown("""
1. **Load & model:** the 8 CSVs are joined into one sales table and one inventory table
   (the Power Query + relationships step).
2. **Measures:** one function per measure family (`kpis`, `group_kpis`, `action_matrix`,
   `working_capital`, `plan_next_month`), mirroring DAX measures.
3. **Slicers:** the sidebar filters a cached slice. KPI deltas compare with the same period last year;
   when the selection starts in the first year they compare the latest two full years (e.g. 2025 vs 2024).
4. **Verification:** all 40 answers are recomputed on the full dataset and checked against the book
   (see *Question check*); the Power BI equivalents are in the *Power BI guide*.
""")
