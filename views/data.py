import streamlit as st

import filters
import ui

CC = st.column_config
ctx = filters.current()
S, INV = ctx.S, ctx.INV

COLS = ["TransactionID", "Date", "StoreName", "CategoryName", "ProductName", "BrandType", "ChannelName",
        "PromotionName", "QuantitySold", "GrossSalesSAR", "DiscountSAR", "NetSalesSAR", "CostSAR",
        "GrossMarginSAR", "ReturnFlag", "StockoutFlag"]


@st.cache_data(show_spinner=False)
def to_csv(df) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


ui.page_header("Data", f"{len(S):,} transaction lines match the current filters")

with st.container(horizontal=True, gap="small"):
    st.download_button("Sales (CSV)", to_csv(S[COLS]), "filtered_sales.csv", "text/csv",
                       icon=":material/download:", on_click="ignore")
    st.download_button("Inventory snapshot (CSV)", to_csv(INV), "filtered_inventory.csv", "text/csv",
                       icon=":material/download:", on_click="ignore", disabled=INV.empty)

st.dataframe(S[COLS], width="stretch", hide_index=True, height=600, column_config={
    "Date": CC.DateColumn("Date", format="YYYY-MM-DD"),
    "QuantitySold": CC.NumberColumn("Qty", format="localized"),
    "GrossSalesSAR": CC.NumberColumn("Gross", format="%.2f"), "DiscountSAR": CC.NumberColumn("Discount", format="%.2f"),
    "NetSalesSAR": CC.NumberColumn("Net", format="%.2f"), "CostSAR": CC.NumberColumn("Cost", format="%.2f"),
    "GrossMarginSAR": CC.NumberColumn("Margin", format="%.2f"),
    "ReturnFlag": CC.CheckboxColumn("Returned"), "StockoutFlag": CC.CheckboxColumn("Stockout")})
