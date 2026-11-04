# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> Note: `~/Downloads/CLAUDE.md` (DIXMOUNT / GISCO website) is also loaded because this folder sits under `~/Downloads`. It is for a different project and does not apply here.

## What this is

A Streamlit dashboard for the **Crescent Grocery retail case study (DD-RET-002)**. It is built to answer the 40 questions in the Question Book and to act as a reference for rebuilding the same model in Power BI. The source brief is in the parent folder: `DD-RET-002_Question_Book.pdf`, `_Business_Introduction.pdf`, `_Relationship_Model.pdf`, `_Data_Dictionary.xlsx`, and the original CSVs. `data/` holds the same 8 CSVs without the `DD-RET-002_` prefix. All amounts are in SAR.

## Commands

Use the project virtualenv at `.venv/`. The system Python has no pandas.

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt   # one-time setup
.venv/bin/streamlit run app.py                    # dashboard
.venv/bin/python verify.py                        # 40 Question-Book answers; must print 40/40
.venv/bin/python -m pytest -q                     # full suite
.venv/bin/python -m pytest -q tests/test_engine.py -k "question_book and 37"   # one question
```

`tests/test_engine.py` runs one parametrized test per question plus unit tests for the measures. `tests/test_app.py` is an `AppTest` smoke test that renders every page, with and without filters. AppTest drops sidebar widgets when a `st.navigation` app reruns, so set filter state in `session_state` **before** the first `run()` (see `app()` in that file) rather than clicking widgets.

## Architecture

- **`engine.py`** contains no Streamlit code: just pandas. Its sections mirror Power BI's workflow:
  1. `load_data()` is the "Power Query + relationships" step.
     - It denormalises the star schema into `sales` and `inv`.
     - It maps the **inactive relationships** to extra columns: `ReturnYearMonth` and `SameDayFulfil`.
     - It adds `IsPromo`, where **`PromotionID == 1` means no promotion**.
     - Slicer and grouping text columns are cast to `category` with sorted categories (`Quarter` and `YearMonth` are *ordered*). Every groupby therefore passes `observed=True`.
  2. Measures:
     - `kpis(df)` returns the headline measures for any slice.
     - `group_kpis(df, by)` gives the same measures grouped, like SUMMARIZE.
     - `top()` applies the Question Book's tie rule (ties go to the lowest ID or key).
     - `action_matrix` (Q37), `working_capital` (Q40), and `plan_next_month` (Q39).
  3. `compute_answers()` plus `EXPECTED`, the values copied from the Question Book. `check()` compares them with a ±0.0101 tolerance, and `TOL_OVERRIDE` makes Q33 wider because the book rounds it.
- **`filters.py`** is the only place that filters data.
  - `render_sidebar()` draws the slicers (session keys `f_date`, `f_store`, `f_cat`, `f_chan`, `f_brand`, `f_promo`, `f_snap`) and stores a frozen, hashable `Filters` in `st.session_state["filters"]`.
  - `get_slice(filters)` is `st.cache_data`. It returns a `Slice` with:
    - `S`: the filtered sales
    - `SP`: the same filters for the same period last year
    - `dK`, `dKP` and `cmp_label`: what `Slice.delta()` compares. This is the same period last year when it exists. Otherwise it is the latest two full calendar years inside the selection (the default 2023–2025 view shows "2025 vs 2024", which matches Q19). Otherwise there is no delta.
    - `inv_f` and `INV`: the inventory and the selected snapshot
    - `wc_sales`, `K`, `KP`, `mon` and `spark`
  - Pages call `filters.current()`. They never filter the raw frames themselves.
- **`app.py`** is the entrypoint. It runs page config, `ui.css()`, `st.navigation` with "Analysis" and "Reference" sections, `render_sidebar()`, a shared empty-selection guard, and then `pg.run()`.
- **`views/*.py`** are thin pages: they read `filters.current()`, then call `ui` and `charts`.
  - `method.py` (the star-schema graphviz diagram and the working assumptions), `questions.py` and `powerbi_guide.py` always use the full dataset.
  - The empty-selection guard skips them.
- **`charts.py`** contains the Plotly builders (`hbar`, `vbar` with an optional dashed `ref` line, `bar_line`, `area`, `columns`, `grouped`, `heatmap`).
  - Always render through `charts.show(fig)`, which uses `theme="streamlit"`.
  - The data colours in `PAL` are mid-tones or translucent tints that read on both themes.
  - Month labels are forced to a category axis.
- **`ui.py`** contains:
  - `hero`: the branded banner, used on Executive only. Other pages use `page_header`.
  - `kpi`: a bordered `st.metric` with a sparkline and the comparison label. Set `inverse=True` for rates where a rise is bad.
  - `card`, `insight`, and `section`, which uses `st.subheader` with a coloured divider: green normally, orange for promotions, red for risk.
  - `status_column`: coloured chips in tables. Each cell value is a one-item list.
- **Theming rule.** The viewer switches light/dark from the ⋮ menu, which happens in the browser and **does not rerun the script**. So never choose a colour in Python from the current theme: `st.context.theme` stays stale, and `tests/test_app.py::test_no_server_side_theme_lookup` guards this.
  - `.streamlit/config.toml` defines `[theme.light]` and `[theme.dark]`.
  - Card and metric surfaces are computed in CSS from `currentColor` (see `ui._CSS`).
  - Plotly text, grid and hover colours come from Streamlit's chart theme.
  - Everything else (the banner, data colours, the heatmap scale, the graphviz diagram) uses colours that work on both backgrounds.
- **Pages live in `views/`, never `pages/`.** Streamlit still auto-discovers a `pages/` folder. A deep link such as `/stores` on a freshly started server then runs that file without `app.py`, and crashes with `KeyError: 'filters'`.
- **`DAX_GUIDE.md`** contains the Power BI equivalent of every engine measure. Leave it unchanged unless you add or change a business measure in `engine.py`; then add the matching DAX. UI-only calculations, such as sparkline series, don't count as measures.
