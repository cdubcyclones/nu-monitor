# FINDINGS — Phase 3 recast (decision document)

This is a decision memo, not code. It records why the original Phase 3 plan is not
executable on the data we actually have, proposes three candidate analytical centerpieces
grounded strictly in data we possess or can cleanly acquire, and recommends one.

Hard constraint applied throughout: **every candidate must be falsifiable or verifiable
against real data.** No directional sentiment indicators, no composite scores without a
validation target.

---

## 1. What broke and why

The original Phase 3 target was **NU reported quarterly customer net-adds**, to be predicted
by a pt-BR Apple App Store review-sentiment signal. Neither side survives contact with the
data:

- **Target side — too few observations.** Net-adds needs *consecutive* quarters. NU's
  customer series has exactly two contiguous runs: `{Q4'21, Q1'22, Q2'22}` and
  `{Q2'25, Q3'25, Q4'25, Q1'26}`. That is **2 + 3 = 5 net-add differences**, in two disjoint
  windows. The gap between them (≈Q4'22–Q1'25) is the operating-metrics image-only gap
  documented in DATA_SOURCES.md; Q4'22 specifically is the one fully unfillable quarter
  ([DATA_SOURCES § Q4'22](DATA_SOURCES.md#q422--the-one-unfillable-hole)). Per project
  policy we do not OCR or estimate. So the gap is permanent with free data.

- **Signal side — no usable history (the real killer).** The Apple App Store RSS feed
  returns only the *most recent* reviews (~500, ~10 pages). For an app as busy as Nubank
  that is days-to-weeks of reviews — there is **no retrospective monthly series to build**.
  Even if the customer series were contiguous, the signal could not be reconstructed for
  past quarters.

**Honest finding (for the README):** the proposed alt-data signal cannot be validated
retrospectively with free data — the target has ~3 usable observations and the signal has
no history. This is a legitimate negative result, and it is the project's judgment artifact:
we tested whether the idea was even measurable before dressing it up as a model.

Note the inversion: in this project the **macro series are long and clean**, while the
**company KPIs are short and the alt-data signal is shallow.** Any centerpiece must respect
that the binding constraint is almost always NU's own observation count.

### Data we actually have (the menu every candidate must order from)

| Series | Depth | Notes |
|---|---|---|
| NU revenue, net_income, gross_profit | 8 quarters (text releases) | Cleanly extendable to ~16–20 *contiguous* quarters by parsing NU's IFRS financial-statement exhibits (`nufs*.htm`) — those ARE real HTML tables, not images. No OCR, no guessing. |
| NU customers, ARPAC, deposits, purchase_volume | 8 quarters, gappy (4 recent contiguous) | Operating metrics; only in the image/hidden-text releases, so the gap is permanent. |
| NU npl_15_90 / npl_90_plus | ~5, split v1/v2 | Brazil-only (v1) ≈3 pts; consolidated (v2) ≈2 pts. Definition break + tiny n. |
| NU efficiency_ratio | v1 ≈2, v2 ≈2 | Redefined at Q4'25. Comparison-unsafe. |
| Peer revenue, net_income (SoFi/Block/PayPal) | 20–48 quarters each | XBRL, contiguous, back to 2014–15. Deepest, cleanest series we have. |
| Peer extra fundamentals (gross profit, opex, assets, …) | similar depth | Cleanly acquirable — more us-gaap XBRL tags, same pipeline. |
| SoFi deposits | ~20 quarters | XBRL instant frames. |
| Brazil macro: Selic, household default/credit (BCB), unemployment/IPCA (IBGE) | decades, monthly | Long, clean, free. Requires Phase 2 to ingest. |
| Apple pt-BR reviews | snapshot only | No usable history. Prospective collection only. |

---

## 2. Candidate centerpieces

### Candidate A — Cross-company growth & profitability comparison *(no macro)*
- **Question it answers:** At comparable scale and over a comparable window, how does NU's
  revenue growth and profitability (net margin, path-to-profit) compare to digital-banking
  peers (SoFi, Block, PayPal)? Is NU's trajectory distinctive?
- **Observable target (in our data):** `revenue`, `net_income`, derived `net_margin =
  net_income/revenue`, and YoY/QoQ growth — all present for all four companies. Optional
  `gross_profit` margin (NU has it; peers expose it in XBRL) for a cleaner cross-GAAP margin.
- **Sample-size sanity:** peers 20–48 quarters each; NU 8 now, **~16–20 acquirable** from
  the IFRS statement tables. Binding constraint is NU, but ≥8 (and easily ≥16) is enough for
  a credible descriptive trajectory comparison.
- **Phase 2 data needed:** **none.** Purely SEC-sourced. (This candidate is the test of
  whether Phase 2 is load-bearing — it is not, for this one.)
- **Honest weakness / reviewer pushback:** revenue is not strictly like-for-like (IFRS vs
  US-GAAP; SoFi net-of-interest; Block's Bitcoin-inflated top line). Mitigated by leaning on
  **net margin and growth rates** (scale- and partly GAAP-robust) and documenting caveats;
  but a reviewer will correctly note this is *descriptive comparison*, not a predictive
  model. We don't claim otherwise.

### Candidate B — NU credit quality vs the Brazilian credit cycle *(requires macro)*
- **Question it answers:** Is NU's asset quality (NPL) and portfolio growth moving with the
  Brazilian household credit cycle — Selic, system household-default rate, unemployment —
  better, worse, or in line?
- **Observable target (in our data):** NU `npl_15_90` / `npl_90_plus` and `credit_portfolio`
  growth, aligned to NU's quarterly timeline, overlaid on BCB household-default + Selic and
  IBGE unemployment.
- **Sample-size sanity:** **this is the problem.** Same-definition NPL is ≈3 points (v1) or
  ≈2 (v2); the v1→v2 (Brazil-only→consolidated) break means you cannot even concatenate them.
  Macro is long, but the join is gated by NU's ~3 usable, definition-stable NPL observations.
- **Phase 2 data needed:** BCB SGS household default/credit + Selic; IBGE unemployment/IPCA.
  Load-bearing for this candidate.
- **Honest weakness / reviewer pushback:** you cannot establish a relationship — let alone a
  divergence claim — on ~3 observations across a definition break. At best this is a
  *contextual overlay* ("here is NU's NPL against the cycle"), explicitly not a finding.
  A reviewer would (rightly) reject any correlation/regression claim here.

### Candidate C — Independent reconstruction & comparability audit *(no macro)*
- **Question it answers:** Can NU's headline numbers be independently reconstructed from
  primary SEC filings and reconciled across NU's *two* internal sources (the hidden-text
  release vs the IFRS financial-statement exhibits), and where exactly do definitions break
  (within NU over time, and vs peers)?
- **Observable target (in our data):** the reconciliation itself — parsed-release
  `revenue`/`net_income` vs the same figures in NU's IFRS statement tables (two independent
  extractions from the same filings → a genuine cross-check), plus the catalogued definition
  breaks (efficiency v1/v2, NPL geography, cost-to-serve sign).
- **Sample-size sanity:** the cross-check runs on every parseable NU quarter (8 now, ~16–20
  with IFRS-table parsing). Decent n because it's a reconciliation, not a prediction.
- **Phase 2 data needed:** **none.** Mostly *already built* (parser + `DATA_SOURCES.md` +
  `definition_version` are the skeleton of this).
- **Honest weakness / reviewer pushback:** it's a data-engineering / governance story, not an
  "investment signal." A reviewer hunting for alpha will be unimpressed; a reviewer assessing
  engineering judgment will value it. Risk of reading as "infrastructure without a question."

---

## 3. Recommendation

**Primary centerpiece: Candidate A (cross-company growth & profitability), and it does NOT
require Phase 2.** I am saying that directly: for the strongest analytical deliverable the
data supports, the Brazil macro layer is **not load-bearing**, and we should not build it for
sunk-cost / narrative-symmetry reasons.

Reasoning:
- A is built on our **deepest, cleanest, most-verifiable** series (revenue/net_income), it
  delivers exactly what the project's title promises (a *comparative fundamentals* monitor),
  and every number ties to a filing. It degrades gracefully: even at NU's current 8 quarters
  it works, and it gets materially better with the clean IFRS-table backfill (no OCR).
- **B loses on sample size.** Its target (NU NPL) is ~3 usable, definition-split observations.
  No amount of long macro data fixes a 3-point dependent variable. B can survive only as a
  clearly-labeled *contextual overlay*, not the centerpiece — and that does not justify the
  cost of Phase 2 by itself.
- **C loses as a *standalone* centerpiece** because it lacks an analytical question, but it is
  nearly free (mostly built) and is the most defensible "judgment" content. So fold C in as a
  **supporting section** of A — the reconciliation + comparability audit is what lets a
  reviewer *trust* A's comparison.

Proposed shape: **A as the centerpiece, C as its credibility/back-matter, B demoted to an
optional one-panel "Brazil context" overlay only if we later decide the Brazil-first
narrative needs a visual** — and if so, a *minimal* Phase 2 (just Selic + household default),
not the full macro build.

Concretely, the highest-value next build is **not Phase 2** — it's parsing NU's IFRS
financial-statement exhibits to make NU's revenue/net_income/(deposits) a contiguous ~16–20
quarter series, which is what turns A from "suggestive" into "solid." That is a clean,
no-guessing extraction (real HTML tables) and it strengthens A, C, and even B's overlay.

**Decision requested:** approve A (+C) as the centerpiece and deprioritize Phase 2, or tell
me the Brazil narrative is non-negotiable and we keep a minimal macro overlay.
