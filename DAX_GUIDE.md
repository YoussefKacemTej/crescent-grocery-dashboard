# Rebuilding this dashboard in Power BI

## 1. Model (Model view)
Import the 8 CSVs. Create relationships (**many-to-one, single direction**):

| From (many) | To (one) | Active |
|---|---|---|
| FactSalesTransactions[TransactionDateKey] | DimDate[DateKey] | ✅ |
| FactSalesTransactions[FulfillmentDateKey] | DimDate[DateKey] | ❌ inactive |
| FactSalesTransactions[ReturnDateKey] | DimDate[DateKey] | ❌ inactive |
| FactSalesTransactions[StoreID / ProductID / PromotionID / ChannelID] | Dim*[ID] | ✅ |
| FactInventorySnapshot[SnapshotDateKey / StoreID / ProductID] | DimDate / DimStore / DimProduct | ✅ |
| DimProduct[SupplierID] | DimSupplier[SupplierID] | ✅ |

Mark DimDate as a date table (column `Date`). Sort `YearMonth` by itself (it sorts alphabetically = chronologically).
Power Query: set `DateKey` columns to Whole Number, `ReturnFlag/StockoutFlag/BelowReorderFlag` to True/False.

## 2. Base measures (create a `_Measures` table)
```DAX
Net Sales      = SUM ( FactSalesTransactions[NetSalesSAR] )
Gross Sales    = SUM ( FactSalesTransactions[GrossSalesSAR] )
Discount       = SUM ( FactSalesTransactions[DiscountSAR] )
COGS           = SUM ( FactSalesTransactions[CostSAR] )
Gross Margin   = SUM ( FactSalesTransactions[GrossMarginSAR] )
Units Sold     = SUM ( FactSalesTransactions[QuantitySold] )
Lines          = COUNTROWS ( FactSalesTransactions )

Margin %       = DIVIDE ( [Gross Margin], [Net Sales] )
Discount Rate  = DIVIDE ( [Discount], [Gross Sales] )
Avg Basket     = DIVIDE ( [Net Sales], [Lines] )

Returns        = CALCULATE ( [Lines], FactSalesTransactions[ReturnFlag] = TRUE () )
Return Rate    = DIVIDE ( [Returns], [Lines] )
Stockout Lines = CALCULATE ( [Lines], FactSalesTransactions[StockoutFlag] = TRUE () )
Stockout Rate  = DIVIDE ( [Stockout Lines], [Lines] )

Promo Net Sales = CALCULATE ( [Net Sales], FactSalesTransactions[PromotionID] <> 1 )
Promo Share     = DIVIDE ( [Promo Net Sales], [Net Sales] )
Promo Margin %  = CALCULATE ( [Margin %], FactSalesTransactions[PromotionID] <> 1 )
NonPromo Margin % = CALCULATE ( [Margin %], FactSalesTransactions[PromotionID] = 1 )
Margin Dilution (pts) = ( [NonPromo Margin %] - [Promo Margin %] ) * 100
```

## 3. Time intelligence (KPI deltas on cards)
```DAX
Net Sales LY   = CALCULATE ( [Net Sales], SAMEPERIODLASTYEAR ( DimDate[Date] ) )
Net Sales YoY% = DIVIDE ( [Net Sales] - [Net Sales LY], [Net Sales LY] )
Cumulative Net Sales = CALCULATE ( [Net Sales], FILTER ( ALL ( DimDate ), DimDate[Date] <= MAX ( DimDate[Date] ) ) )
Plan Next Month = AVERAGEX ( TOPN ( 3, VALUES ( DimDate[YearMonth] ), DimDate[YearMonth], DESC ), [Net Sales] ) * 1.08
```
Use `Net Sales` + `Net Sales LY` in a **Card (new)** / KPI visual for the "delta" effect.

## 4. Inactive relationships (USERELATIONSHIP)
```DAX
Returns by Return Date =
CALCULATE ( [Returns], USERELATIONSHIP ( FactSalesTransactions[ReturnDateKey], DimDate[DateKey] ) )

Same-day Fulfilment % =
DIVIDE (
    COUNTROWS ( FILTER ( FactSalesTransactions,
        FactSalesTransactions[FulfillmentDateKey] = FactSalesTransactions[TransactionDateKey] ) ),
    [Lines] )
```

## 5. Inventory (aggregate at its own grain - latest snapshot)
```DAX
Latest Snapshot = MAX ( FactInventorySnapshot[SnapshotDateKey] )
-- [Latest Snapshot] is read into a VAR first: a measure can't be used directly inside a
-- CALCULATE boolean filter ("CALCULATE has been used in a True/False expression ...").
Inventory Value =
VAR _latest = [Latest Snapshot]
RETURN CALCULATE ( SUM ( FactInventorySnapshot[InventoryCostSAR] ),
                   FactInventorySnapshot[SnapshotDateKey] = _latest )
Lines Below Reorder =
VAR _latest = [Latest Snapshot]
RETURN CALCULATE ( COUNTROWS ( FactInventorySnapshot ),
                   FactInventorySnapshot[SnapshotDateKey] = _latest,
                   FactInventorySnapshot[BelowReorderFlag] = TRUE () )
Avg Days of Supply =
VAR _latest = [Latest Snapshot]
RETURN CALCULATE ( AVERAGE ( FactInventorySnapshot[DaysOfSupply] ),
                   FactInventorySnapshot[SnapshotDateKey] = _latest )

Net Sales Last 3M = CALCULATE ( [Net Sales],
        DATESINPERIOD ( DimDate[Date], MAX ( DimDate[Date] ), -3, MONTH ) )     -- evaluate at 2025-12-31
Inventory / Qtr Sales = DIVIDE ( [Inventory Value], [Net Sales Last 3M] )        -- 19.24x = 1,924.25 %
```
Tip: for Q40 by category, `Net Sales Last 3M` must ignore the page date filter: wrap with
`CALCULATE ( ..., REMOVEFILTERS ( DimDate ), DATESINPERIOD ( DimDate[Date], DATE(2025,12,31), -3, MONTH ) )`.

## 6. Category action matrix (Q37)
```DAX
Rank Stockout = RANKX ( ALL ( DimProduct[CategoryName] ), [Stockout Rate], , DESC )
Rank Below    = RANKX ( ALL ( DimProduct[CategoryName] ), [Lines Below Reorder], , DESC )
Rank Margin   = RANKX ( ALL ( DimProduct[CategoryName] ), [Margin %], , ASC )
Rank Days     = RANKX ( ALL ( DimProduct[CategoryName] ), [Avg Days of Supply], , ASC )
Action Score  = [Rank Stockout] + [Rank Below] + [Rank Margin] + [Rank Days]   -- lowest = act first (Bakery = 13)
```
Matrix visual: rows = CategoryName, values = the 4 metrics + `Action Score`; conditional-format `Action Score` (green→red).

## 7. Report layout (maps 1:1 to the Streamlit tabs)
| Page | Visuals |
|---|---|
| Executive | 8 cards (Net Sales, Margin %, Discount Rate, Units, Return Rate, Stockout Rate, Avg Basket, Promo Share) · combo chart (column Net Sales + line Margin % by YearMonth) · area chart cumulative · column by Quarter |
| Stores & Channels | bar Net Sales by Store · bar Margin % by Store · matrix heat-map Store × Category (Stockout Rate, background colour) · bar Return Rate by Channel |
| Products & Suppliers | bar by Category · Pareto (Top N filter on ProductName by Net Sales, line = cumulative %) · clustered bar Margin % by BrandType · Top 10 Supplier |
| Promotions & Returns | clustered bar Promo vs Non-promo margin · PromotionType table · Category exception table (conditional format when Return Rate > chain) · column Returns by Return Date |
| Inventory | 4 cards · line Inventory Value by YearMonth · bar Days of Supply by Store · action matrix · ratio table |

**Slicers (sidebar):** Date (between), Store, Category, Channel, BrandType, Promotion (PromotionID = 1 or not). Sync slicers across pages.

## 8. Reconciliation checklist
Net Sales 3,342,923.31 · Gross 3,545,365.95 · Discount 202,441.87 · Margin % 31.63 · Stockout 4.42 % · Return 3.28 % (983) · Avg basket 111.43 · Inventory 6,304,915.32 (snapshot 20251201).
The *Question check* tab in the Streamlit app lists all 40 expected results.
