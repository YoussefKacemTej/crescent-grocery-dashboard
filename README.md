# Crescent Grocery dashboard (DD-RET-002)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
      # dashboard (light/dark: ⋮ menu → Settings)
python verify.py            # checks all 40 Question-Book answers (40/40)
pytest -q                   # 40 question tests + measure unit tests + page smoke tests
```

Files:
- `app.py`: the entrypoint, covering navigation and the sidebar.
- `views/`: one file per page.
- `engine.py`: the data model and measures, with no Streamlit code.
- `filters.py`: the slicers and the cached filtered slice.
- `charts.py`: Plotly figures.
- `ui.py`: layout components.
- `data/`: the 8 CSVs.
- `DAX_GUIDE.md`: the Power BI equivalents.
