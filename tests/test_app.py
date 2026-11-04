"""Smoke tests: every page renders without an exception; filters and the empty state work.

Note: AppTest drops sidebar widgets on reruns of st.navigation apps, so filter state is
seeded through session_state *before* the first run instead of clicking widgets.
"""
from datetime import date
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")
PAGES = ["views/executive.py", "views/stores.py", "views/products.py", "views/promotions.py",
         "views/inventory.py", "views/method.py", "views/data.py", "views/questions.py", "views/powerbi_guide.py"]


def app(**state) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=60)
    for k, v in state.items():
        at.session_state[k] = v
    return at


@pytest.mark.parametrize("page", PAGES)
def test_page_renders(page):
    at = app().run()
    at.switch_page(page).run()
    assert not at.exception, at.exception


@pytest.mark.parametrize("page", PAGES)
def test_page_renders_with_filters(page):
    at = app(f_store=["Crescent Grocery 003"], f_promo="Promoted only",
             f_date=(date(2024, 3, 1), date(2025, 6, 30))).run()
    at.switch_page(page).run()
    assert not at.exception, at.exception


def test_store_filter_matches_question_book():
    at = app(f_store=["Crescent Grocery 003"]).run()
    assert not at.exception
    assert at.metric[0].value == "237.42K"          # Q11: Crescent Grocery 003 = 237,422.44


def test_prior_year_delta_shown():
    at = app(f_date=(date(2025, 1, 1), date(2025, 12, 31))).run()
    assert at.metric[0].delta == "+6.4%"           # Q19: 2025 vs 2024 = +6.41%


def test_empty_selection_shows_info():
    at = app(f_date=(date(2023, 1, 1), date(2023, 1, 1)), f_store=["Crescent Grocery 001"],
             f_cat=["Bakery"], f_chan=["Click and Collect"]).run()
    assert not at.exception
    assert at.info and "No data" in at.info[0].value


def test_default_view_falls_back_to_latest_full_years():
    at = app().run()                                # 2023-2025: no same period last year
    net = at.metric[0]
    assert net.delta == "+6.4%"                     # Q19: 2025 vs 2024 = +6.41%
    assert net.proto.delta_description == "2025 vs 2024"


def test_partial_first_year_has_no_delta():
    at = app(f_date=(date(2023, 3, 1), date(2023, 9, 30))).run()
    assert not at.exception and not at.metric[0].delta


def test_promotions_page_with_non_promoted_only():
    at = app(f_promo="Non-promoted only").run()
    at.switch_page("views/promotions.py").run()
    assert not at.exception
    assert any("No promoted lines" in i.value for i in at.info)


def test_no_server_side_theme_lookup():
    """Switching theme in the menu does not rerun the script, so any colour chosen in Python from
    st.context.theme goes stale (unreadable cards after a light<->dark switch). Keep it client-side."""
    root = Path(APP).parent
    for f in ["ui.py", "charts.py", *map(str, (root / "views").glob("*.py"))]:
        assert "context.theme" not in (root / f).read_text(), f
