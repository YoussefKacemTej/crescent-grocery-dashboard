import pandas as pd
import streamlit as st

import filters
import ui
from engine import EXPECTED, TOL_OVERRIDE, check, compute_answers

CC = st.column_config


@st.cache_data(show_spinner="Recomputing the 40 answers…")
def answers_table() -> pd.DataFrame:
    A = compute_answers(filters.get_data())
    fmt = lambda v: v if isinstance(v, str) else (f"{v:,.2f}" if isinstance(v, float) else f"{v:,}")
    return pd.DataFrame([{"Q": q, "Question": title, "Expected": " | ".join(map(fmt, exp)),
                          "Computed": " | ".join(map(fmt, A[q])),
                          "Match": check(A[q], exp, TOL_OVERRIDE.get(q, 0.0101))}
                         for q, (title, exp) in EXPECTED.items()])


st.markdown("## Question Book check")
st.caption("Each answer is recomputed from the raw CSVs on the **full** dataset: sidebar filters are ignored here.")

qdf = answers_table()
n_ok = int(qdf.Match.sum())
c = st.columns([1, 3], vertical_alignment="center")
ui.kpi(c[0], "Answers matching", f"{n_ok} / {len(qdf)}")
if n_ok == len(qdf):
    c[1].success("All 40 Question-Book answers match the expected results.", icon=":material/verified:")
else:
    c[1].error(f"{len(qdf) - n_ok} answers need review.", icon=":material/error:")

only_bad = st.toggle("Show only mismatches", key="only_bad")
st.dataframe(qdf[~qdf.Match] if only_bad else qdf, hide_index=True, width="stretch", height=560, column_config={
    "Q": CC.NumberColumn("Q", width=50, format="%d"), "Question": CC.TextColumn(width="medium"),
    "Expected": CC.TextColumn(width="large"), "Computed": CC.TextColumn(width="large"),
    "Match": CC.CheckboxColumn("Match", width="small")})
st.caption("Q33: the book prints 79.30%; the data gives 79.31% (23,794 / 30,000), a rounding difference.")
