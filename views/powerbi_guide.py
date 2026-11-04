from pathlib import Path

import streamlit as st

GUIDE = Path(__file__).resolve().parent.parent / "DAX_GUIDE.md"

with st.container(border=True):
    st.markdown(GUIDE.read_text(encoding="utf-8") if GUIDE.exists() else "DAX_GUIDE.md not found.")
