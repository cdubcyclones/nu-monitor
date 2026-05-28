# NU Fundamentals & Signal Monitor

Brazil-first comparative fundamentals dashboard for **Nu Holdings (NYSE: NU)** and
digital-banking peers, plus one *validated* alternative-data signal. Single-file DuckDB
store, free official-first data sources, fully reproducible. Built as a portfolio piece.

> Why Brazil-first: NU is ~92% Brazilian by revenue and 100% of customers are in
> Brazil/Mexico/Colombia. Tooling instrumented for US bank-switching would measure the
> wrong country. See [docs/SCOPE.md](docs/SCOPE.md).

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"

# SEC blocks requests without a contact email. Copy and edit:
copy .env.example .env   # then set SEC_USER_AGENT to your email

python -m nu_monitor              # initializes data/nu.duckdb with the kpi_panel schema
python -m nu_monitor ingest-all   # load NU (6-K parse) + peers (XBRL) into the panel
pytest
```

## Status

- [x] Phase 0 — scaffold + schema
- [x] Phase 1 — EDGAR ingestion + KPI panel (NU 6-K parse + SoFi/Block/PayPal XBRL)
- [ ] Phase 2 — Brazil macro layer (BCB, IBGE)
- [ ] Phase 3 — signal + out-of-sample validation
- [ ] Phase 4 — Streamlit dashboard
- [ ] Phase 5 — docs & packaging
