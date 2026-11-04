"""
Crescent Grocery - Inventory, Promotions & Product Profitability (DD-RET-002)
Run with:  streamlit run app.py

Entrypoint only: page config, sidebar slicers, navigation. Each page lives in views/ (not pages/: that name triggers Streamlit's legacy auto-discovery and breaks deep links),
business logic in engine.py (pure pandas), filtering + caching in filters.py.
"""
import streamlit as st

import charts
import filters
import ui

st.set_page_config(page_title="Crescent Grocery · Profitability", page_icon=":material/nightlight:",
                   layout="wide", initial_sidebar_state="expanded")
charts.register_templates()
ui.css()

PAGES = {
    "Analysis": [
        st.Page("views/executive.py", title="Executive", icon=":material/space_dashboard:", default=True),
        st.Page("views/stores.py", title="Stores & Channels", icon=":material/storefront:"),
        st.Page("views/products.py", title="Products & Suppliers", icon=":material/inventory_2:"),
        st.Page("views/promotions.py", title="Promotions & Returns", icon=":material/sell:"),
        st.Page("views/inventory.py", title="Inventory", icon=":material/warehouse:"),
    ],
    "Reference": [
        st.Page("views/method.py", title="Method & data model", icon=":material/schema:"),
        st.Page("views/data.py", title="Data", icon=":material/table_view:"),
        #st.Page("views/questions.py", title="Question check", icon=":material/fact_check:"),
        st.Page("views/powerbi_guide.py", title="Power BI guide", icon=":material/functions:"),
    ],
}
FILTER_FREE = {"Question check", "Power BI guide", "Method & data model"}   # always on the full dataset

pg = st.navigation(PAGES)
f = filters.render_sidebar()
ctx = filters.current()

total = len(filters.get_data()["sales"])
st.sidebar.caption(f"**{len(ctx.S):,}** of {total:,} sales lines selected")

p0, p1 = ctx.prior
st.session_state["header_ctx"] = {
    "period": f"{f.start} → {f.end}",
    "compare": f"vs {p0} → {p1}" if len(ctx.SP) else (ctx.cmp_label or "No comparison period"),
    "n_filters": f.active_count(),
}

if ctx.S.empty and pg.title not in FILTER_FREE:
    ui.page_header(pg.title)
    st.info("**No data for the current filters.** Widen the date range or clear a filter.", icon=":material/search_off:")
    st.button("Reset all filters", icon=":material/restart_alt:", on_click=filters.reset_filters, type="primary")
    st.stop()

pg.run()
