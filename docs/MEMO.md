# NU comparative fundamentals — what the panel shows

**Lead finding.** At Q1'26, NU operates a customer deposit base of **$42.4 B**
against SoFi's **$40.2 B** — a near-parity **1.05×** ratio — while running
roughly **4.5× SoFi's quarterly revenue** ($4,968 M vs $1,100 M). Two
deposit-funded digital banks at near-identical balance-sheet scale generate
very different revenue per dollar of deposits. That observation organizes
the rest of this read.

## The comparative read

NU is the cohort's fastest grower over its window. Quarterly revenue CAGRs
over each company's full panel range: NU **62.3 %/yr** (Q4'21 → Q1'26, 4.25 y),
SoFi 48.1 %/yr (Q2'20 → Q1'26, 5.75 y), Block 31.5 %/yr (Q2'17 → Q1'26, 8.75 y),
PayPal 10.6 %/yr (Q1'19 → Q1'26, 7 y). NU overtook SoFi's quarterly revenue
at **Q1'22**, within one quarter of its IPO; at Q1'26 it sits at **~82 %** of
Block's revenue and **~59 %** of PayPal's. Block's headline scale is partly
definitional — its `Revenues` includes Bitcoin pass-through gross of cost — so
the gap to NU is narrower in net economics than the top line suggests.

On margin, NU posted the largest sustained expansion of the four:
**0.6 % at Q3'22 → 17.5 % at Q1'26, +16.9 pp** over 3.5 years, already in
PayPal's mature band. SoFi expanded about half as much (+8.4 pp over 5.75 y)
on a revenue base reported net of interest expense (the US-GAAP bank
convention). PayPal drifted from 16.2 % at Q1'19 to 13.3 % at Q1'26 — a
mature plateau slightly below where it started. Block is volatile around
zero: 13 of 34 panel quarters net-positive, 6 of the 7 most recent positive
before a Q1'26 GAAP loss driven by ~$908 M of identified one-time charges.

Chart 3 (the scale-vs-margin frontier) is the strongest visual: NU traces a
convex arc from low scale / loss to ~$5 B quarterly revenue and ~17.5 % margin;
SoFi a similar shape at one-fifth the scale; PayPal a tight mature cluster at
$7–8 B revenue / 13–16 % margin; Block oscillates around zero margin at
$5–6 B revenue. The cleanest like-for-like in the panel is **NU vs SoFi**
(Charts 1 and 4 together) — the deposit-parity / 4.5×-revenue finding rests
on that pairing of deposit-funded digital-only banks. The NU-vs-Block contrast
at similar revenue scale is *not* evidence of NU's distinctiveness, because
Block's depressed margin is partly a revenue-mix artifact.

## Why this is the right comparison set

A Brazilian digital bank, a US digital bank, a payments-and-fintech platform,
and a payments network are not strictly comparable institutions. They are
comparable as *business models at different lifecycle stages*: deposit-funded
digital banking (NU, SoFi) and broad payments / fintech (Block, PayPal). What
the cohort delivers is trajectory and slope, not level-on-level precision.
NU's position — fast-growing, recently profitable, at scale — is identifiable
against the others' shapes without claiming they are like-for-like institutions.

## What I cut and why

The project originally proposed validating a pt-BR Apple App Store
review-sentiment signal against NU's quarterly customer net-adds. The thesis
did not survive a data check: NU's customer series — given the image-only
earnings-release gap (≈Q4'22 – Q1'25) — supports only ~3 consecutive net-add
observations, and the Apple RSS feed exposes only the most recent ~500 reviews,
so the signal itself has no usable historical depth. The honest move was to
write up the infeasibility ([`docs/FINDINGS.md`](FINDINGS.md)) and recast the
deliverable as a descriptive comparative read backed by reproducible
ingestion. That decision is documented; it is the analytical discipline I
exercised here.

## Known limitations

- **Peer Q4 XBRL gap.** SoFi / Block / PayPal Q4 quarters are not captured by
  SEC calendar-quarter frames (Q4 is reported via the 10-K as the FY-minus-9M
  residual); peer panels skip 5–9 quarters each. NU is unaffected — its Q4
  figures derive from `FY − 9M` IFRS statements, cross-validated against the
  Q4'25 earnings release. See [`docs/DATA_SOURCES.md`](DATA_SOURCES.md).
- **`efficiency_ratio` and `npl_*` are comparison-unsafe.** NU redefined both
  at Q4'25; the centerpiece does not chart them across companies.
- **Q4'22 is the one unfillable NU quarter** — release was image-only and
  `nufs4q22` is not a financials exhibit. Audited FY22 figures are in the
  20-F, out of v1 scope.
- **Descriptive, not predictive.** No regression, no correlation claim, no
  out-of-sample test.

## Forward look

Refresh is a single command (`python -m nu_monitor ingest-all`); incoming
quarters update all four cohort charts and shift the frontier. Three
observations would change the centerpiece read: NU's net margin reversing
below ~15 % for two consecutive quarters; SoFi's revenue scale closing
materially against the deposit-parity / 4.5×-revenue gap; or Block stabilizing
GAAP margin above zero on a sustained basis through 2026. A Q4-peer backfill
— parsing each peer's 10-K income statement HTML directly — would close the
documented gap in Charts 1 and 2 and is the obvious next ingestion target.
