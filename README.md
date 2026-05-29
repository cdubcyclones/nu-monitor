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

## Known discontinuities — read before comparing

A few things would silently mislead a reviewer who didn't know them. Full details and
source quotes live in [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md); the short version:

- **Revenue definition (Q4'25+): managerial vs statutory.** NU's new-format earnings
  release introduces a "Managerial P&L" whose `Total Revenue` differs from the statutory
  IFRS `Total revenue` by ~+3.5 % (Q4'25: managerial 4,857.3 vs IFRS 4,685.9 $M). Net
  income is identical under both. **We use statutory IFRS** as the canonical `revenue`
  so the series is uniform across all quarters and more peer-comparable.
- **Efficiency ratio — redefined at Q4'25** (~27.7 % → 17.6 %; a methodology change, not
  improvement). Stored as separate `v1`/`v2` series via the `definition_version` column.
  **Never chart `efficiency_ratio` v1 and v2 as one line** without an explicit caveat.
  Same versioning applied to `npl_15_90` / `npl_90_plus` (Brazil-only → consolidated).
- **One quarter is genuinely unfillable: Q4'22.** Both the earnings release and the
  financial-statements exhibit fail for Q4'22 (the release was published as slide images
  with no machine-readable text; `nufs4q22` is not actually a financial-statements doc).
  FY2022 audited figures live in the 20-F, out of v1 scope. Documented in
  [docs/DATA_SOURCES.md § Q4'22](docs/DATA_SOURCES.md#q422--the-one-unfillable-hole).

## Status

- [x] Phase 0 — scaffold + schema
- [x] Phase 1 — EDGAR ingestion + KPI panel (NU 6-K parse + IFRS backfill + peer XBRL)
- [ ] Phase 2 — Brazil macro layer (Selic + household default, BCB SGS only — minimal)
- [ ] Phase 3 — centerpiece analysis (TBD; see [docs/FINDINGS.md](docs/FINDINGS.md))
- [ ] Phase 4 — Streamlit dashboard
- [ ] Phase 5 — docs & packaging
