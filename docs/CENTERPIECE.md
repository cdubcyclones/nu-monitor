# CENTERPIECE — scoping (decision document, not implementation)

This locks the centerpiece before any analysis or dashboard code is written. Charts and
their messages are fixed here; if a chart proposed later isn't in this doc, it doesn't
ship.

Framing recap (from [FINDINGS.md](FINDINGS.md)): the project ships **Centerpiece A**
(cross-company growth & profitability), with **C** as credibility back-matter and **B**
as one labeled contextual overlay. Phase 3's original "validated alt-data signal" is
permanently retired as infeasible with free data ([FINDINGS § 1](FINDINGS.md#1-what-broke-and-why)).

---

## 1. The one analytical question

### Candidate framings considered

- **A1. NU vs the full digital-banking cohort (SoFi, Block, PayPal)** on revenue and
  profitability over time. **Loses on coherence.** Block's top line is half-Bitcoin
  pass-through and PayPal is a mature payments business at a totally different stage —
  drawing four parallel revenue lines invites the reviewer to push back that the
  comparison isn't really like-for-like, and the per-line caveat surface is large.
- **A2. NU vs SoFi as the single sharpest pairwise comparison** — both deposit-funded
  digital-only banks. **Loses on scope.** It throws away two of the three peers we
  spent the engineering effort to ingest, and "a comparison of two companies" is thin
  for a portfolio piece titled *comparative fundamentals*. SoFi as a *pairwise emphasis
  inside* a broader cohort view is the right size; SoFi as the whole answer is too small.
- **A3. The cohort's revenue/profitability frontier, with NU's trajectory through it.**
  *(Recommended.)* Treat the four companies as four points on a stage-and-scale frontier
  in (revenue, net margin) space; trace each one's quarterly path through that space.
  This framing **absorbs the definitional differences as the point, not the bug** —
  Block volatile, PayPal mature plateau, SoFi small-and-emerging, NU steep-and-distinctive
  — and answers a sharper question than "are they the same."

### Locked question

> **Where does NU sit on the digital-banking cohort's growth-vs-profitability frontier,
> and what does its trajectory through that space look like relative to its peers?**

The deliverable is a *descriptive comparative read*, not a tested relationship. Any
"directional" or "predictive" language is out — see [FINDINGS § 1](FINDINGS.md#1-what-broke-and-why)
for why.

### What would falsify the centerpiece thesis (descriptive analogue of an out-of-sample test)

The thesis is "NU traces a distinct arc through (scale, margin) space relative to peers."
The boring/null version of Chart 3 — the result that would *not* support the thesis and
that the README narrative would have to acknowledge — is: **NU's path overlaps a peer's
path at the same revenue scale rather than tracing a separately-shaped arc**, e.g. NU's
recent points sit in the same neighborhood that SoFi (or early-stage PayPal / Block)
occupied at NU's current scale. If Chart 3 looks like that, the analytical narrative
becomes "NU is on a path the cohort has already traveled," not "NU is distinctive."

---

## 2. The charts that answer it (4)

Each chart is fixed below. Metrics referenced are exact `kpi_panel.metric` values.

### Chart 1 — Revenue scale & trajectory (line)

- **Shows:** quarterly revenue (`metric='revenue'`, `unit='usd_m'`) for NU, SOFI, SQ, PYPL,
  Q4'21 → Q1'26. Log y-axis so the four-companies-at-different-scales fit on one panel.
  Q4'22 hole in NU's line annotated, not interpolated.
- **From:** `kpi_panel` rows `metric='revenue'`, `definition_version='v1'`.
- **The chart asks (do not pre-bake the answer):** does NU's revenue growth rate exceed
  peers' and by how much (compute CAGRs from the panel); has NU's quarterly revenue
  crossed SoFi's during the window, and when; how far is NU from Block/PayPal's
  order of magnitude at the last reported quarter. Compute the answers and put them
  in the README narrative with values; the chart shows the lines, the README states the
  numbers.
- **Required caveat in caption:** "Revenue definitions are not strictly identical — IFRS
  (NU) vs US-GAAP (peers); SoFi reports net of interest expense; Block includes Bitcoin
  pass-through. Read for scale and slope, not precise levels."

### Chart 2 — Net margin trajectory (line)

- **Shows:** `net_income / revenue × 100` per quarter, four lines. Same window.
- **From:** `kpi_panel` rows `metric IN ('revenue','net_income')`, `definition_version='v1'`,
  joined per `(company, period_end)`.
- **The chart asks (do not pre-bake the answer):** when each company crossed into
  positive net margin; the slope of margin expansion for each (compute the
  first-to-last-quarter margin delta per company and put the numbers in the README);
  where each company sits on Q1'26 closing margin.
- **Required caveat:** "Cross-GAAP and cross-presentation differences in the numerator
  and denominator persist (see Chart 1); a margin level is not strictly comparable
  across companies, but the *trajectory* and *direction* are robust."

### Chart 3 — The frontier (revenue-vs-margin scatter with paths)

- **Shows:** each company's quarterly observations plotted as points in `(revenue_$M,
  net_margin_%)` space; consecutive quarters within a company connected to form a
  "path through the frontier"; each company's most-recent quarter marked as a larger
  dot.
- **From:** same data as Charts 1+2; one row per `(company, period_end)`.
- **Visual-feasibility plan (decided here, not at the easel):** the cohort spans roughly
  $0.6B → $8B+ in quarterly revenue and roughly −50 % → +25 % in net margin, so NU's
  arc will be long and the mature peers' paths will be small clusters.
  - **Primary rendering:** single chart with **log-scale x-axis** (revenue, $M) and
    **linear y-axis** (net margin, %), four colored paths with arrow-marked direction
    of travel and the most-recent quarter shown as a larger labeled dot per company.
    Log-x is what compresses NU's range and lets all four paths share one panel.
  - **Fallback (used only if the single panel doesn't read clearly at the end of the
    build):** small-multiples — one panel per company on shared log-x and shared linear-y
    axes so the four paths can be compared side-by-side at identical scales without
    overlapping. The decision to fall back is recorded in the README if it happens.
- **The chart asks (do not pre-bake the answer):** does NU's path through (scale, margin)
  space have a distinct shape from peers' paths, or do paths overlap at the same revenue
  scale (the falsification case stated in § 1). The reader should be able to look and
  say yes/no; the README narrative will say which.

### Chart 4 — Deposits: NU vs SoFi (the cohort's only deposit-funded peers)

- **Shows:** quarterly deposits (`metric='deposits'`, `unit='usd_b'`) for NU and SoFi
  only, on a linear y-axis. Block and PayPal omitted — they have no comparable
  customer-deposit balance ([DATA_SOURCES](DATA_SOURCES.md)).
- **From:** `kpi_panel` rows `metric='deposits'`, `company IN ('NU','SOFI')`,
  `definition_version='v1'`.
- **The chart asks (do not pre-bake the answer):** what is the actual deposit-scale
  ratio between NU and SoFi at Q1'26 (compute it; my earlier off-the-cuff "~5×" turned
  out to be the *revenue* ratio, not deposits — a small but instructive reminder not to
  pattern-match here); how do the two deposit-growth rates compare. README states the
  values.
- **Required caveat:** "Deposits are a directly comparable balance-sheet line; Block
  and PayPal lack a meaningful customer-deposit equivalent and are correctly excluded."

---

## 3. C — credibility back-matter

A clearly-labeled "Methodology & data integrity" section accompanying the charts.
**Prose only — no charts here.** Each bullet is a brief paragraph that links to the
authoritative doc rather than restating it.

1. **Heterogeneous ingestion in one schema** — three different parser paths reconciled
   into one `kpi_panel`: NU 6-K hidden-text releases (foreign-issuer KPI exhibits, no
   XBRL); NU IFRS financial-statement HTML tables (backfill); peer XBRL company-facts
   (calendar-quarter `frames`); BCB SGS REST. Pointer: [DATA_SOURCES](DATA_SOURCES.md).
2. **The Q4'25 column-format change in NU releases**, and the "current-quarter-column-0
   only" defense that makes layout drift a non-event. Pointer: DATA_SOURCES § known
   discontinuities.
3. **`definition_version` versioning** — `efficiency_ratio` v1↔v2 and `npl_15_90` /
   `npl_90_plus` v1 (Brazil-only) ↔ v2 (consolidated). Why we never collapse these into
   one series.
4. **Managerial vs statutory revenue at Q4'25+** — why we make IFRS statutory the
   canonical `revenue` (~3.5% gap; net income identical under both) and how the ingest
   order enforces it.
5. **IFRS Q4 derivation (full year − nine month)** — exact arithmetic on two reported
   IFRS figures, cross-validated against the Q4'25 earnings release's net income
   ($894.8M match) to prove the method.
6. **Per-filer XBRL choices** — SoFi's `RevenuesNetOfInterestExpense` vs Block / PayPal's
   `Revenues`; deposits only for SoFi (Block / PayPal correctly excluded).
7. **The Q4'22 hole** — both the release and the financial-statements exhibit fail; the
   single unfillable quarter and why. Pointer: [DATA_SOURCES § Q4'22](DATA_SOURCES.md#q422--the-one-unfillable-hole).
8. **Why this is descriptive, not predictive** — pointer to [FINDINGS § 1](FINDINGS.md#1-what-broke-and-why)
   explaining the validation target/signal infeasibility and the deliberate Phase-3 recast.
9. **BCB API quirks** — 406 on bare URL and on explicit `Accept: application/json`;
   `dataInicial=01/01/2021` is documented as the working bound.

---

## 4. B — the single Brazil-context overlay panel

### Chart 5 — NU credit quality in the Brazilian household credit cycle (CONTEXTUAL ONLY)

- **Shows:** NU `npl_15_90` `definition_version='v1'` (Brazilian Consumer Credit Portfolio
  scope only — three same-definition observations: Q3'24, Q2'25, Q3'25), overlaid on
  BCB `household_default` (`company='BR_MACRO'`, monthly-derived quarterly aligned), with
  `selic_target` on a **secondary y-axis**. Time x-axis 2022 → Q1'26. The NU v2 NPL
  series is **deliberately NOT shown** — its scope (consolidated, not Brazil-only) is not
  the same measure.
- **From:** `kpi_panel` rows
  `(company='NU' AND metric='npl_15_90' AND definition_version='v1')` ∪
  `(company='BR_MACRO' AND metric IN ('household_default','selic_target'))`.
- **Caption (hard-coded, must appear verbatim under the panel):**

  > Contextual only. NU's NPL series shown here is the original (v1) "Brazilian Consumer
  > Credit Portfolio" definition; only three same-definition observations are available
  > (Q3'24, Q2'25, Q3'25). No statistical relationship between NU's credit metric and
  > Brazilian system-wide indicators is claimed — three points cannot establish one.
  > This panel exists to make explicit *where* NU operates, not to test a claim about
  > how NU tracks the cycle.

- **Reader concludes:** the geographic context is on the page; nothing more.

---

## 5. Out of scope (explicit — apply the Phase-2 discipline)

The following are **NOT** part of this centerpiece. Any future request to add one needs
an explicit decision and a reason that survives "what observable target would actually
use it?":

- **No predictive model, regression, correlation coefficient, or hypothesis test**
  anywhere in the analysis. Descriptive only. (Reason: sample size on every NU-side
  series; see FINDINGS.)
- **No cross-company `efficiency_ratio` or `npl_*` comparison** — both are comparison-
  unsafe per DATA_SOURCES. Permitted use: NU-only, with the definition break shown.
  The NU-only credit/efficiency views are *back-matter* (Section 3), not centerpiece
  charts.
- **No customer counts for peers** — definitions are incompatible (NU customers vs
  SoFi members vs Block MAUs vs PayPal active accounts). Excluded for peers in the
  ingest; not magically re-includable in the centerpiece.
- **No additional macro series** — no IBGE, IPCA, unemployment, FX, household credit
  balance, segment GDP, anything. The Brazil overlay is one panel with two macro series
  and that is the entire macro footprint.
- **No incumbent-bank reference set** (JPM, Wells, Itaú, Bradesco). Not ingested; not in
  scope.
- **No segment / line-item breakouts** — no interest-vs-fee revenue split, no per-product
  margins, no FX-neutral toggling.
- **No projections, forecasts, or guidance overlays.** The dashboard ends at the last
  reported quarter.
- **No composite "score", "rank", "recommendation", or qualitative rating.**
- **No alt-data signal of any kind.** The signal track is retired (FINDINGS § 1).
- **No live / streaming / scheduled refresh.** Refresh is on-demand via
  `python -m nu_monitor ingest-all`; the dashboard reads the local DuckDB file.
- **No dashboard interactivity beyond company selection and date range.** No drill-downs,
  no exports, no filtering by metric definition version (the version is encoded in the
  chart, not a UI knob).

If during build I find myself wanting to add anything in this list, the rule is the same
as Phase 2: stop and ask.
