"""Question-Book regression (all 40 answers) + unit tests for the measures in engine.py."""
import numpy as np
import pandas as pd
import pytest

from engine import EXPECTED, TOL_OVERRIDE, check, compute_answers, kpis, load_data, safe_div, top


@pytest.fixture(scope="module")
def data():
    return load_data()


@pytest.fixture(scope="module")
def answers(data):
    return compute_answers(data)


@pytest.mark.parametrize("q", sorted(EXPECTED))
def test_question_book(answers, q):
    title, expected = EXPECTED[q]
    assert check(answers[q], expected, TOL_OVERRIDE.get(q, 0.0101)), f"Q{q} {title}: got {answers[q]}, expected {expected}"


def test_safe_div_zero_and_missing():
    assert np.isnan(safe_div(1, 0))
    assert np.isnan(safe_div(1, None))
    assert np.isnan(safe_div(1, np.nan))
    assert safe_div(3, 4) == 0.75


def test_top_breaks_ties_on_lowest_key():
    df = pd.DataFrame({"ID": [3, 1, 2], "v": [10, 10, 5]})
    assert top(df, "v", key="ID").ID.item() == 1
    assert top(df, "v", asc=True, key="ID").ID.item() == 2


def test_kpis_on_empty_slice_does_not_raise(data):
    k = kpis(data["sales"].iloc[0:0])
    assert k["net"] == 0 and k["lines"] == 0 and np.isnan(k["gm_pct"])


def test_categorical_dims_keep_string_order(data):
    s = data["sales"]
    assert isinstance(s.StoreName.dtype, pd.CategoricalDtype)
    assert list(s.StoreName.cat.categories) == sorted(s.StoreName.astype(str).unique())
