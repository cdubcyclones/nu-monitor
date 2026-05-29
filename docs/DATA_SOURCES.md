# Data sources, cadence, and gotchas

Every `kpi_panel` row carries a `source_url`. This file documents where each number comes
from, how often it refreshes, and the traps that bite anyone who trusts the data naively.

## Sources

| Source | Used for | Endpoint pattern | Cadence | Auth |
|---|---|---|---|---|
| SEC EDGAR submissions | NU 6-K filing index | `https://data.sec.gov/submissions/CIK{cik10}.json` | quarterly (earnings) | UA header |
| SEC EDGAR archives | NU 6-K release exhibits (HTML) | `https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{doc}` | quarterly | UA header |
| SEC EDGAR company-facts | Peer XBRL (SoFi/Block/PayPal) | `https://data.sec.gov/api/xbrl/companyfacts/CIK{cik10}.json` | quarterly (10-Q/10-K) | UA header |
| SEC company tickers | ticker → CIK resolution | `https://www.sec.gov/files/company_tickers.json` | rarely | UA header |
| BCB SGS *(Phase 2)* | Brazil macro (Selic, household credit/default) | `https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados?formato=json` | monthly | none |
| IBGE SIDRA *(Phase 2)* | unemployment (PNAD), inflation (IPCA) | `https://apisidra.ibge.gov.br/values/...` | monthly | none |
| Apple App Store RSS *(Phase 3)* | pt-BR review sentiment signal | `https://itunes.apple.com/br/rss/customerreviews/id={appId}/json` | continuous | none |

### SEC gotchas (all sources)
- **User-Agent header is mandatory.** SEC blocks requests without a contact email. Set
  `SEC_USER_AGENT` in `.env`. We also throttle (~0.15 s/request) and retry 429/503 with
  backoff — SEC returns 503 intermittently even within rate limits.
- CIKs are zero-padded to 10 digits for the data API, but the **Archives path uses the
  integer CIK** (no leading zeros). Accession numbers are dashless in the path.

## NU is a foreign private issuer — the hard part

NU files **6-K / 20-F**, not 10-K/10-Q, and does **not** expose its operating KPIs as
XBRL. Worse, the earnings release is rendered as **slide images (JPGs)**; the only
machine-readable copy is a **hidden paragraph** (white text, 0.1 pt font) that dumps the
release as one flat string. So:

- There is **no HTML `<table>`** to parse for KPIs. We parse the hidden flat-text block.
- We read **only the current-quarter column** (the value immediately after each metric
  label). See the next section for why.
- A handful of releases are **image-only with no hidden text** (e.g. `nupr1q25_6k.htm`:
  26 KB of `<img>` tags, ~1.3 KB of boilerplate text, zero "Customers"). Those quarters
  are **left as gaps**. We do **not** OCR or estimate them — a missing number is
  acceptable; a guessed one is not. This is why NU's series are non-contiguous
  (parseable: 2021–22 and Q2'25→present; image-only: ≈Q4'22–Q1'25).

## NU IFRS financial-statement backfill (`nufs*.htm`)

NU's interim and annual *financial-statement* exhibits (`nufs1q*` / `nufs2q*` / `nufs3q*` /
`nufs4q*`) DO render as real HTML tables, so they parse cleanly without OCR or guessing.
We use this path to extend NU's `revenue`, `net_income`, and `deposits` series to ~18
contiguous quarters (Q4'21 → Q1'26, with one documented hole at Q4'22). Operating metrics
(customers, ARPAC, NPL, cost-to-serve, efficiency) are NOT in the IFRS statements and are
never backfilled from anywhere — they stay gapped as the earnings releases left them.

Wrinkles encountered (and how the parser handles them):

- **Header label drift.** The "Three-month period ended" header text is present only in
  some quarters (Q2/Q3 interims, mid-period); Q1 interims and the newest Q1'26 just show
  bare dates above the value columns. We classify each value column by what its own
  header cells contain (period label + date + year), not by a fixed column index.
- **Bottom-line label drift.** The net-income / profit line varies across quarters:
  `Net income for the period`, `Net income for the year`, `Profit (loss) for the period`,
  `Profit for the period` (note: no "(loss)" in some 2024 docs), `Loss for the year`
  (FY2021), and `Profit (loss) for the three-month period` (Q1'23). Matched by regex.
- **Q4 exhibits are ANNUAL.** `nufs4q*` carries the full-year income statement, not a
  Q4-standalone column. We derive **Q4 = full-year − nine-month** (exact subtraction of
  two reported figures), pairing each `nufs4q{YY}` with the same year's `nufs3q{YY}`
  nine-month column. Cross-checked against the Q4'25 earnings-release net income — the
  derived value matched exactly (894.8 ✓), which validates the method.
  Q4'21 cannot be derived (no Q3'21 interim 6-K exists), so Q4'21 revenue/net_income come
  only from the earnings release; Q4'21 deposits come from the `nufs4q21` balance sheet.
- **Annual balance sheets use YEAR columns** (e.g. `2025`) rather than `MM/DD/YYYY`. The
  deposits-column selector accepts either, treating a year column as Dec 31 of that year.
- **`nufs4q22` is not actually a financial-statements exhibit** — it contains no revenue,
  net-income, or deposits lines. NU filed the audited FY2022 figures in the 20-F instead.
  Parsing the 20-F is out of scope for v1, so **Q4'22 is the one remaining hole** in the
  otherwise contiguous Q4'21→Q1'26 series. We skip docs that lack statement markers
  (silently); we still fail loud if a doc that HAS the markers is structurally unparseable.
- **Statements are in US$ thousands.** Converted to NU units: `revenue`/`net_income` →
  `usd_m` (÷1,000); `deposits` → `usd_b` (÷1,000,000).

### Managerial vs statutory revenue (Q4'25+) — comparison-safe choice

NU's new-format earnings release (Q4'25 onward) introduces a *"Managerial P&L"* whose
`Total Revenue` differs from the statutory IFRS `Total revenue` by ~+3.5 % (Q4'25:
managerial 4,857.3 vs statutory IFRS 4,685.9 $M). **Net income is identical** under both
presentations, so the difference is a reclassification (likely interest gross-up), not a
bottom-line change.

The pipeline runs `ingest-nu` (releases) → `ingest-nu-fin` (IFRS) → `ingest-peers` so
the IFRS statutory figures **overwrite** the release values for overlapping new-format
quarters. The stored `revenue` series is therefore uniformly statutory IFRS across all
quarters, which is also more comparable to peers' US-GAAP top lines.

## Known discontinuities — READ BEFORE COMPARING

NU changed its reporting format in **Q4'25** (filed 2026-02-25). Several metrics are not
comparable across that boundary. We encode this with a `definition_version` column:
`v1` = pre-Q4'25 definition, `v2` = Q4'25+ definition. **Rows with the same metric but
different versions are different series.** Do **not** chart them as one without a caveat.

### 1. Column layout changed (handled, not a data issue)
Through Q3'25 the metrics block columns were `[current Q, year-ago Q, prior Q]`. From
Q4'25 they became `[current Q, prior Q, %QoQ, year-ago, %YoY]`. Reading the wrong column
silently turns a percent into a "value." We defend by reading only column 0 (current
quarter), so each release contributes exactly one quarter and later-column drift cannot
corrupt anything. (Bonus: FX-neutral == reported for the current quarter, so there is no
FX ambiguity in what we store.)

### 2. Efficiency ratio — REDEFINED (comparison-unsafe)
- **v1** (≤Q3'25, prose): *"Nu's efficiency ratio slightly decreased to 27.7%"* (Q3'25).
- **v2** (Q4'25+, structured `Efficiency-Ratio`): **17.6%** (Q1'26), 19.9% (Q4'25).
- The ~10 pp drop is a **methodology change**, not improvement. Treat `efficiency_ratio`
  v1 and v2 as separate series. **No combined view** — a reviewer who wants one can union
  the versions themselves.

### 3. NPL 15-90 / NPL 90+ — geography likely changed (comparison-unsafe)
- **v1** (≤Q3'25, prose): *"the 15-90 NPL ratio for the Brazil Consumer Credit Portfolio,
  reached 4.2%"* with footnote **"Data for Brazil only."**
- **v2** (Q4'25+, structured): under *"Summary of Consolidated Other Performance Metrics"*,
  `NPL 15-90 5.0%` (Q1'26) — **no Brazil-only qualifier**.
- Evidence points to a shift from **Brazil-only → consolidated**, but NU did not state the
  change explicitly; the qualifier was simply dropped. We version-split conservatively.
  Treat as comparison-unsafe.

### 4. Cost-to-serve — sign flip (normalized)
NU prints monthly cost-to-serve **positive** in the old layout (0.9) and **negative** in
the new layout (-1.0, as an expense). We store the **magnitude** so the series is
consistent; the printed sign is presentation, not economics.

## Comparison-unsafe metrics (cross-company rule)
`efficiency_ratio` and `npl_*` must **not** be used in naive NU-vs-peer comparisons:
their definitions differ across NU's own history and certainly across companies (and peers
report neither in comparable form). Any chart touching them must carry an explicit caveat.

## Peer comparability (SEC XBRL)

Peers (SoFi `0001818874`, Block `0001512673`, PayPal `0001633917`) report **US-GAAP XBRL**;
NU reports **IFRS**. We ingest only metrics that are genuinely comparable at a high level,
using SEC calendar-quarter **frames** (`CY{yyyy}Q{q}`) for clean quarterly values:

| Metric | Included? | Notes |
|---|---|---|
| `revenue` | yes (all peers) | Top-line total revenue. **Not strictly like-for-like:** NU/Block/PayPal report gross-ish total revenue; SoFi reports total revenue *net of interest expense* (`RevenuesNetOfInterestExpense`). IFRS (NU) vs US-GAAP (peers). Use for scale/trend, not precise ratios. |
| `net_income` | yes (all peers) | US-GAAP `NetIncomeLoss`. IFRS vs US-GAAP caveat applies. |
| `deposits` | only where meaningful | SoFi is a bank (`Deposits`). Block/PayPal are not deposit-led; excluded if not a headline balance. |
| `customers` | **excluded for peers** | Not in XBRL, and definitions are incompatible (NU "customers" vs SoFi "members" vs Block MAUs vs PayPal "active accounts"). Forcing them into one metric would be a wrong number. |
| `arpac`, `npl_*`, `efficiency_ratio`, `cost_to_serve` | **excluded for peers** | NU-specific or comparison-unsafe; no comparable peer definition. |

Units are normalized to match NU: `revenue`/`net_income` in `usd_m`, `deposits` in `usd_b`.
