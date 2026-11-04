"""
engine.py - data loading + business logic for the DD-RET-002 retail dashboard.
No Streamlit code here, so every number can be unit-checked (see verify.py)
and re-implemented 1:1 as DAX measures in Power BI (see DAX_GUIDE.md).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).parent / "data"

# Low-cardinality text columns used as slicers / group keys -> categorical (less memory,
# faster isin/groupby). Categories are sorted so ordering matches plain-string sorting.
CATEGORICAL = ["Quarter", "YearMonth", "StoreName", "City", "RegionName", "StoreFormat", "CategoryName",
               "BrandType", "SupplierName", "PromotionName", "PromotionType", "ChannelName"]
ORDERED = {"Quarter", "YearMonth"}   # chronological -> allow <, <= comparisons


def _categorize(df: pd.DataFrame) -> pd.DataFrame:
    for c in CATEGORICAL:
        if c in df:
            df[c] = pd.Categorical(df[c], categories=sorted(df[c].dropna().unique()), ordered=c in ORDERED)
    return df


# ----------------------------------------------------------------------------
# 1. LOAD + MODEL  (the Power BI "Power Query + relationships" step)
# ----------------------------------------------------------------------------
def load_data(data_dir: Path = DATA_DIR) -> dict:
    rd = lambda n: pd.read_csv(Path(data_dir) / f"{n}.csv")
    dim_date, dim_store, dim_prod = rd("DimDate"), rd("DimStore"), rd("DimProduct")
    dim_sup, dim_chan, dim_promo = rd("DimSupplier"), rd("DimChannel"), rd("DimPromotion")
    sales, inv = rd("FactSalesTransactions"), rd("FactInventorySnapshot")

    dim_date["Date"] = pd.to_datetime(dim_date["Date"])

    # --- denormalised sales (active relationships: Date, Store, Product, Promotion, Channel)
    sx = (sales
          .merge(dim_date[["DateKey", "Date", "Year", "Quarter", "YearMonth"]],
                 left_on="TransactionDateKey", right_on="DateKey", how="left").drop(columns="DateKey")
          .merge(dim_store[["StoreID", "StoreName", "City", "RegionName", "StoreFormat"]], on="StoreID", how="left")
          .merge(dim_prod[["ProductID", "ProductName", "CategoryName", "BrandType", "SupplierID"]], on="ProductID", how="left")
          .merge(dim_sup[["SupplierID", "SupplierName"]], on="SupplierID", how="left")
          .merge(dim_promo[["PromotionID", "PromotionName", "PromotionType"]], on="PromotionID", how="left")
          .merge(dim_chan[["ChannelID", "ChannelName"]], on="ChannelID", how="left"))

    # --- INACTIVE relationships (USERELATIONSHIP in DAX): return month / fulfilment date
    ym = dim_date.set_index("DateKey")["YearMonth"]
    sx["ReturnYearMonth"] = sx["ReturnDateKey"].map(ym)
    sx["SameDayFulfil"] = sx["FulfillmentDateKey"] == sx["TransactionDateKey"]
    sx["IsPromo"] = sx["PromotionID"] != 1          # PromotionID 1 = no promotion

    # --- denormalised inventory
    ix = (inv
          .merge(dim_date[["DateKey", "Date", "YearMonth"]], left_on="SnapshotDateKey", right_on="DateKey", how="left")
          .drop(columns="DateKey")
          .merge(dim_store[["StoreID", "StoreName"]], on="StoreID", how="left")
          .merge(dim_prod[["ProductID", "ProductName", "CategoryName", "BrandType"]], on="ProductID", how="left"))

    return dict(sales=_categorize(sx), inv=_categorize(ix), date=dim_date, store=dim_store, product=dim_prod,
                supplier=dim_sup, channel=dim_chan, promo=dim_promo)


# ----------------------------------------------------------------------------
# 2. MEASURES  (the Power BI "DAX measures" step)
# ----------------------------------------------------------------------------
def safe_div(a, b) -> float:
    """DIVIDE(): NaN instead of an error on a zero / missing denominator."""
    return np.nan if b is None or pd.isna(b) or b == 0 else float(a) / float(b)


def kpis(df: pd.DataFrame) -> dict:
    """All headline measures for any slice of the sales fact."""
    n = len(df)
    net, gross, disc = df.NetSalesSAR.sum(), df.GrossSalesSAR.sum(), df.DiscountSAR.sum()
    gm = df.GrossMarginSAR.sum()
    return dict(
        net=net, gross=gross, discount=disc, cost=df.CostSAR.sum(), gm=gm,
        gm_pct=safe_div(gm, net) * 100, disc_rate=safe_div(disc, gross) * 100,
        units=df.QuantitySold.sum(), lines=n,
        returns=int(df.ReturnFlag.sum()), return_rate=safe_div(df.ReturnFlag.sum(), n) * 100,
        stockout_rate=safe_div(df.StockoutFlag.sum(), n) * 100,
        avg_basket=safe_div(net, n),
        promo_share=safe_div(df.loc[df.IsPromo, "NetSalesSAR"].sum(), net) * 100,
        same_day=safe_div(df.SameDayFulfil.sum(), n) * 100,
    )


def group_kpis(df: pd.DataFrame, by) -> pd.DataFrame:
    """Same measures, grouped (SUMMARIZE). Ties sorted by key ascending."""
    g = df.groupby(by, observed=True).agg(
        NetSales=("NetSalesSAR", "sum"), GrossSales=("GrossSalesSAR", "sum"),
        Discount=("DiscountSAR", "sum"), GrossMargin=("GrossMarginSAR", "sum"),
        Units=("QuantitySold", "sum"), Lines=("TransactionID", "count"),
        Returns=("ReturnFlag", "sum"), Stockouts=("StockoutFlag", "sum")).reset_index()
    g["MarginPct"] = g.GrossMargin / g.NetSales * 100
    g["DiscountRate"] = g.Discount / g.GrossSales.replace(0, np.nan) * 100
    g["ReturnRate"] = g.Returns / g.Lines * 100
    g["StockoutRate"] = g.Stockouts / g.Lines * 100
    return g


def top(df: pd.DataFrame, col: str, n: int = 1, asc: bool = False, key: str | None = None) -> pd.DataFrame:
    """Rank with the book's tie rule: ties -> lowest ID first."""
    key = key or df.columns[0]
    return df.sort_values([col, key], ascending=[asc, True]).head(n)


def latest_snapshot(inv: pd.DataFrame, asof: int | None = None) -> pd.DataFrame:
    key = inv.SnapshotDateKey.max() if asof is None else asof
    return inv[inv.SnapshotDateKey == key]


def action_matrix(sales: pd.DataFrame, inv_latest: pd.DataFrame) -> pd.DataFrame:
    """Q37 - category score = sum of 4 ranks (1 = worst). Lowest score = act first.
    worst = high stockout, high lines-below-reorder, low margin %, low days of supply."""
    s = group_kpis(sales, "CategoryName")[["CategoryName", "StockoutRate", "MarginPct"]]
    i = inv_latest.groupby("CategoryName", observed=True).agg(
        BelowReorder=("BelowReorderFlag", "sum"), AvgDaysOfSupply=("DaysOfSupply", "mean")).reset_index()
    m = s.merge(i, on="CategoryName")
    m["R_Stockout"] = m.StockoutRate.rank(ascending=False)
    m["R_Below"] = m.BelowReorder.rank(ascending=False)
    m["R_Margin"] = m.MarginPct.rank(ascending=True)
    m["R_Days"] = m.AvgDaysOfSupply.rank(ascending=True)
    m["Score"] = m[["R_Stockout", "R_Below", "R_Margin", "R_Days"]].sum(axis=1)
    return m.sort_values(["Score", "CategoryName"]).reset_index(drop=True)


def working_capital(sales: pd.DataFrame, inv_latest: pd.DataFrame, last_months: list) -> tuple[float, pd.DataFrame]:
    """Q40 - latest inventory cost vs net sales of the last 3 months (a 'quarter')."""
    q = sales[sales.YearMonth.isin(last_months)]
    total = safe_div(inv_latest.InventoryCostSAR.sum(), q.NetSalesSAR.sum()) * 100
    cat = (inv_latest.groupby("CategoryName", observed=True).InventoryCostSAR.sum()
           / q.groupby("CategoryName", observed=True).NetSalesSAR.sum() * 100).rename("InvToQtrSales%").reset_index()
    return total, cat.sort_values("InvToQtrSales%", ascending=False)


def plan_next_month(sales: pd.DataFrame, uplift: float = 0.08) -> float:
    """Q39 - average of last 3 months' net sales x (1 + 8%)."""
    m = sales.groupby("YearMonth", observed=True).NetSalesSAR.sum().sort_index()
    return m.tail(3).mean() * (1 + uplift)


# ----------------------------------------------------------------------------
# 3. THE 40 QUESTIONS  -> computed vs expected (self-check tab / verify.py)
# ----------------------------------------------------------------------------
def compute_answers(D: dict) -> dict[int, list]:
    s, inv = D["sales"], D["inv"]
    k = kpis(s)
    L = latest_snapshot(inv)
    A = {}
    A[1] = [k["net"]]; A[2] = [k["gross"]]; A[3] = [k["discount"]]; A[4] = [k["cost"]]
    A[5] = [k["gm"]]; A[6] = [k["gm_pct"]]; A[7] = [k["units"]]; A[8] = [k["disc_rate"]]
    A[9] = [D["store"].StoreID.nunique()]; A[10] = [D["product"].ProductID.nunique()]

    st = group_kpis(s, ["StoreID", "StoreName"]); t = top(st, "NetSales", key="StoreID").iloc[0]
    A[11] = [t.StoreName, t.NetSales]
    cat = group_kpis(s, "CategoryName"); t = top(cat, "NetSales").iloc[0]
    A[12] = [t.CategoryName, t.NetSales]
    pr = group_kpis(s, ["ProductID", "ProductName"]); t = top(pr, "Units", key="ProductID").iloc[0]
    A[13] = [t.ProductName, t.Units]
    A[14] = [k["stockout_rate"]]; A[15] = [k["returns"], k["return_rate"]]; A[16] = [k["avg_basket"]]

    mo = group_kpis(s, "YearMonth")
    t = top(mo, "NetSales", key="YearMonth").iloc[0]; A[17] = [t.YearMonth, t.NetSales]
    t = top(mo, "NetSales", asc=True, key="YearMonth").iloc[0]; A[18] = [t.YearMonth, t.NetSales]
    yr = s.groupby("Year").NetSalesSAR.sum()
    A[19] = [(yr[2025] / yr[2024] - 1) * 100, yr[2025], yr[2024]]
    t = top(mo, "MarginPct", key="YearMonth").iloc[0]; A[20] = [t.YearMonth, t.MarginPct]
    t = top(mo, "StockoutRate", key="YearMonth").iloc[0]; A[21] = [t.YearMonth, t.StockoutRate]
    q = group_kpis(s, "Quarter"); t = top(q, "NetSales", key="Quarter").iloc[0]; A[22] = [t.Quarter, t.NetSales]
    A[23] = [mo.sort_values("YearMonth").NetSales.cumsum().iloc[-1]]
    t = top(st, "MarginPct", key="StoreID").iloc[0]; A[24] = [t.StoreName, t.MarginPct]
    t = top(st, "StockoutRate", key="StoreID").iloc[0]; A[25] = [t.StoreName, t.StockoutRate]
    t = top(cat, "MarginPct", asc=True).iloc[0]; A[26] = [t.CategoryName, t.MarginPct]
    t5 = top(pr, "NetSales", n=5, key="ProductID"); A[27] = [t5.NetSales.sum() / k["net"] * 100, t5.NetSales.sum()]
    p, n = kpis(s[s.IsPromo]), kpis(s[~s.IsPromo])
    A[28] = [p["gm_pct"], n["gm_pct"], n["gm_pct"] - p["gm_pct"]]
    br = group_kpis(s, "BrandType").set_index("BrandType").MarginPct
    A[29] = [br["Private Label"], br["National Brand"]]
    ch = group_kpis(s, "ChannelName"); t = top(ch, "ReturnRate", key="ChannelName").iloc[0]; A[30] = [t.ChannelName, t.ReturnRate]
    su = group_kpis(s, ["SupplierID", "SupplierName"]); t = top(su, "NetSales", key="SupplierID").iloc[0]; A[31] = [t.SupplierName, t.NetSales]
    rm = s[s.ReturnFlag].groupby("ReturnYearMonth").size().rename("n").reset_index()
    t = top(rm, "n", key="ReturnYearMonth").iloc[0]; A[32] = [t.ReturnYearMonth, t.n]
    A[33] = [k["same_day"]]
    A[34] = [int(L.SnapshotDateKey.iloc[0]), L.InventoryCostSAR.sum()]
    A[35] = [int((L.OnHandUnits <= L.ReorderPointUnits).sum()), len(L)]
    ds = L.groupby(["StoreID", "StoreName"], observed=True).DaysOfSupply.mean().rename("d").reset_index()
    t = top(ds, "d", asc=True, key="StoreID").iloc[0]; A[36] = [t.StoreName, t.d]
    am = action_matrix(s, L).iloc[0]; A[37] = [am.CategoryName, am.BelowReorder, am.AvgDaysOfSupply, am.MarginPct]
    chain = k["return_rate"]; above = cat[cat.ReturnRate > chain]
    w = top(cat, "ReturnRate").iloc[0]; A[38] = [w.CategoryName, w.ReturnRate, chain, len(above)]
    top_store, top_cat = A[11][0], A[12][0]
    A[39] = [k["net"], k["gm_pct"], k["disc_rate"], k["return_rate"], k["stockout_rate"],
             top_store, top_cat, k["promo_share"], plan_next_month(s)]
    last3 = sorted(s.YearMonth.unique().tolist())[-3:]
    tot, cc = working_capital(s, L, last3); A[40] = [tot, cc.iloc[0].CategoryName]
    return A


# (title, expected values) - copied from the Question Book
EXPECTED = {
    1: ("Total net sales", [3342923.31]), 2: ("Gross sales", [3545365.95]),
    3: ("Total discount", [202441.87]), 4: ("Cost of goods sold", [2285624.26]),
    5: ("Gross margin SAR", [1057299.15]), 6: ("Gross margin %", [31.63]),
    7: ("Units sold", [68193]), 8: ("Discount rate %", [5.71]),
    9: ("Stores", [15]), 10: ("Products", [500]),
    11: ("Top store (net sales)", ["Crescent Grocery 003", 237422.44]),
    12: ("Top category (net sales)", ["Snacks", 306754.38]),
    13: ("Fastest product (units)", ["Grocery SKU 00226", 237]),
    14: ("Stockout rate %", [4.42]), 15: ("Returns | rate %", [983, 3.28]),
    16: ("Avg basket SAR", [111.43]),
    17: ("Peak month", ["2025-12", 126276.20]), 18: ("Weakest month", ["2023-07", 65300.04]),
    19: ("YoY growth 25 vs 24 | 2025 | 2024", [6.41, 1184008.94, 1112682.84]),
    20: ("Best margin month", ["2024-04", 32.49]), 21: ("Highest stockout month", ["2025-10", 6.67]),
    22: ("Strongest quarter", ["Q1", 971080.62]), 23: ("Cumulative net sales", [3342923.31]),
    24: ("Best-margin store", ["Crescent Grocery 013", 32.20]),
    25: ("Worst stockout store", ["Crescent Grocery 010", 5.21]),
    26: ("Weakest-margin category", ["Household", 28.32]),
    27: ("Top-5 products share % | SAR", [2.58, 86360.69]),
    28: ("Promoted % | Non-promoted % | gap pts", [22.86, 35.40, 12.55]),
    29: ("Private label % | National brand %", [32.41, 31.03]),
    30: ("Highest return-rate channel", ["Click and Collect", 5.80]),
    31: ("Top supplier", ["Supplier 030", 111959.51]),
    32: ("Peak return month (inactive rel.)", ["2025-12", 57]),
    33: ("Same-day fulfilment %", [79.30]),
    34: ("Latest snapshot | inventory cost", [20251201, 6304915.32]),
    35: ("Lines below reorder | population", [144, 1125]),
    36: ("Store lowest days of supply", ["Crescent Grocery 013", 29.80]),
    37: ("Action-first category | below | DoS | margin %", ["Bakery", 17, 31.89, 30.66]),
    38: ("Worst return category | rate | chain | #above", ["Beverages", 3.70, 3.28, 7]),
    39: ("Scorecard", [3342923.31, 31.63, 5.71, 3.28, 4.42, "Crescent Grocery 003", "Snacks", 30.09, 117955.85]),
    40: ("Inventory / qtr sales % | most over-stocked", [1924.25, "Dairy"]),
}


# Book value for Q33 is printed to 1 decimal (79.30) while the data gives 79.3133 -> wider tolerance
TOL_OVERRIDE = {33: 0.02}


def check(computed: list, expected: list, tol: float = 0.0101) -> bool:
    """True if every element matches (numbers within tolerance, text exactly)."""
    if len(computed) != len(expected):
        return False
    for c, e in zip(computed, expected):
        if isinstance(e, str):
            if c != e:
                return False
        elif abs(float(c) - float(e)) > tol:
            return False
    return True
