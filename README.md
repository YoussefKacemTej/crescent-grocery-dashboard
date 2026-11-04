Crescent Grocery: Inventory, Promotions & Product Profitability

An interactive retail analytics dashboard built with Streamlit, pandas and Plotly. It answers a 40-question business brief for a fictional Saudi grocery chain, and every number is validated against the expected answers.

Live demo

Executive overview

<!-- Add a screenshot of the Executive page at assets/screenshot.png, or delete the line above. -->
What it does

Crescent Grocery sells through 15 stores and several channels, running dozens of promotions on about 500 products from 40 suppliers. The dashboard helps a retail manager see:

How the business is performing: net sales, gross margin, discount rate, units, return rate, stockout rate, average basket and promo share, each compared with the same period last year.
Where margin is made or lost: by store, channel, category, brand type and supplier.
Whether promotions pay off: promo vs non-promo margin, discount depth, and the return rates that follow.
What is happening with stock: below-reorder items, days of supply, and over-stocked lines at any month-end snapshot.
Pages
Section	Page	What you get
Analysis	Executive	8 KPI cards with deltas and sparklines, auto-generated insights, monthly and quarterly trends
Analysis	Stores & Channels	Store and channel performance and comparison
Analysis	Products & Suppliers	Category, brand and supplier profitability
Analysis	Promotions & Returns	Promotion effectiveness and return behaviour
Analysis	Inventory	Stock position, reorder risk and days of supply
Reference	Method & data model	Star-schema diagram, relationships and working assumptions
Reference	Data	Browse the underlying tables
Reference	Question check	All 40 brief answers computed live
Reference	Power BI guide	The same measures as DAX

The sidebar slicers (date range, store, category, channel, brand type, inventory snapshot) filter every analysis page, and all pages support light and dark mode.

Data model

A star schema of 2 fact tables and 6 dimensions, all synthetic data covering 2023-01-01 to 2025-12-31.

Table	Rows	Role
FactSalesTransactions	30,000	Sales lines with price, discount, cost, margin, return and stockout flags
FactInventorySnapshot	40,500	Month-end stock by store and product
DimDate	1,096	Calendar
DimProduct	500	Products, categories, brand type, cost and price
DimStore	15	Stores, cities, regions, formats
DimSupplier	40	Suppliers, lead times, payment terms
DimPromotion	24	Promotions and discount depth
DimChannel	3	Sales channels

Key modelling choices:

Relationships are many-to-one, single direction.
FulfillmentDateKey and ReturnDateKey are inactive relationships to DimDate, used only where a question needs them. This is USERELATIONSHIP in DAX and a separate mapping in pandas.
PromotionID = 1 means no promotion.
Rates with a zero denominator return blank, never an error.

Full details are on the Method & data model page inside the app.

Run it locally

Requires Python 3.10 or newer.

bash
git clone https://github.com/YoussefKacemTej/crescent-grocery-dashboard.git
cd crescent-grocery-dashboard

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

streamlit run app.py

The app opens at http://localhost:8501. Switch between light and dark mode from the ⋮ menu → Settings.

Verify the numbers
bash
python verify.py    # checks all 40 brief answers -> 40/40 match
pytest -q           # question tests, measure unit tests and page smoke tests
Project structure
app.py              Entrypoint: page config, navigation, sidebar
views/              One file per page
engine.py           Data loading, model and measures (pure pandas, no Streamlit)
filters.py          Slicers and the cached filtered slice
charts.py           Plotly figures and theme templates
ui.py               Layout components (cards, KPIs, headers)
data/               The 8 CSV files
assets/             Logo
tests/              Engine and app tests
verify.py           Checks the 40 answers
DAX_GUIDE.md        Power BI equivalents of every measure
.streamlit/         Theme and app config

The business logic in engine.py has no Streamlit code in it. That keeps every number unit-testable and makes it a one-to-one translation to DAX.

Rebuild it in Power BI

DAX_GUIDE.md covers the model setup, relationships and every measure (Net Sales, Margin %, Discount Rate, Return Rate, Stockout Rate, Promo Share and more), so you can reproduce the dashboard in Power BI.

Deploy

This app deploys on Streamlit Community Cloud with no extra configuration.

Push the repo to GitHub with app.py at the root.
Create a new app at share.streamlit.io and select the repo, branch main and app.py.
Deploy. No secrets are required.
Tech stack

Python · Streamlit · pandas · NumPy · Plotly · Jinja2 · Matplotlib · pytest

Notes

All data is synthetic and was generated for this exercise. It does not represent a real company.
