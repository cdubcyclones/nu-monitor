"""Parse Nu Holdings earnings-release 6-K exhibits into the KPI panel.

Why this is shaped the way it is (the interesting engineering):
  NU is a foreign private issuer. Its earnings KPIs are NOT published as XBRL or even
  as HTML <table> cells. The release is rendered as slide images, and the only
  machine-readable copy is a *hidden* paragraph (white, 0.1pt font) that dumps the whole
  release as one flat string, including a "Summary of Consolidated Operating/Financial
  Metrics" section.

  That section is laid out in columns, and the column layout CHANGED across quarters
  (through Q3'25: [current Q, year-ago Q, prior Q]; from Q4'25: [current Q, prior Q,
  % QoQ]). Reading the wrong column silently yields a wrong number (e.g. a percent read
  as a customer count).

  Defense: we read ONLY the first value after each metric label -- i.e. the current
  quarter, which is column 0 in every layout. Each release therefore contributes exactly
  one quarter, and cross-quarter format drift can never corrupt a value. (As a bonus,
  FX-neutral == reported for the current quarter by construction, so there is no
  FX ambiguity to resolve here.)

  A handful of credit metrics (NPL 15-90, NPL 90+, efficiency ratio) appear only in the
  narrative prose, never in the structured block. We extract those with strict patterns
  and ACCEPT GAPS: if the exact phrasing isn't found for a quarter, we emit nothing.
  A missing number is acceptable; a guessed one is not.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass

from ..ingest.edgar import Filing, fetch, list_filings
from .schema import KpiRow

OPERATING_MARKER = "Summary of Consolidated Operating Metrics"
QUARTER_RE = re.compile(r"Q([1-4])'(\d{2})")

# Quarter -> calendar period end (month, day).
_Q_END = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}


@dataclass(frozen=True)
class MetricSpec:
    metric: str
    label: str  # exact label text preceding the value in the flat block
    unit: str
    # sanity bounds for the current-quarter value (applied to abs() when abs_value);
    # a violation means our column alignment broke, so we fail loud rather than store
    # a wrong number.
    lo: float
    hi: float
    abs_value: bool = False  # NU flipped cost-to-serve to negative in the Q4'25 format
    definition_version: str = "v1"


# Structured metrics: read the first number after the label (current quarter, column 0).
# Some labels exist only in the old or only in the new layout; a missing label is a gap.
STRUCTURED_SPECS: tuple[MetricSpec, ...] = (
    MetricSpec("customers", "Number of Customers (in millions)", "count_m", 50, 500),
    MetricSpec("active_customers", "Active Customers (in millions)", "count_m", 30, 500),
    MetricSpec("activity_rate", "Activity Rate", "pct", 50, 100),
    MetricSpec("purchase_volume", "Purchase Volume (in $ billions)", "usd_b", 1, 500),
    MetricSpec("arpac", "Monthly Average Revenue per Active Customer (in $)", "usd", 3, 60),
    # Cost-to-serve: printed positive (old) or negative (new); store its magnitude.
    MetricSpec("cost_to_serve", "Monthly Average Cost to Serve per Active Customer (in $)", "usd", 0.1, 10, abs_value=True),
    MetricSpec("credit_portfolio", "Total portfolio - credit card and loan (in $ billions)", "usd_b", 1, 1000),
    MetricSpec("deposits", "Deposits (in $ billions)", "usd_b", 1, 1000),
    MetricSpec("interest_earning_portfolio", "Interest-Earning Portfolio (in $ billions)", "usd_b", 1, 1000),
    MetricSpec("revenue", "Revenue (in $ millions)", "usd_m", 100, 100000),
    MetricSpec("gross_profit", "Gross Profit (in $ millions)", "usd_m", 50, 100000),
    MetricSpec("net_income", "Net Income (in $ million", "usd_m", 1, 100000),
)

OTHER_PERF_MARKER = "Summary of Consolidated Other Performance Metrics"

# Credit / performance metrics: structured only in the Q4'25+ "Other Performance Metrics"
# block (old layout carries these in prose -- see PROSE_SPECS). Searched ONLY within that
# section so the "NPL 15-90" literal in old-format footnotes can't be misread.
# These are the REDEFINED versions (v2): NPL dropped its "Brazil only" footnote and sits
# under "Consolidated" metrics; the efficiency ratio was redefined (~27.7% -> ~17.6%).
OTHER_PERF_SPECS: tuple[MetricSpec, ...] = (
    MetricSpec("npl_15_90", "NPL 15-90", "pct", 0, 30, definition_version="v2"),
    MetricSpec("npl_90_plus", "NPL 90+", "pct", 0, 30, definition_version="v2"),
    MetricSpec("efficiency_ratio", "Efficiency-Ratio", "pct", 0, 100, definition_version="v2"),
)

# Prose-only metrics (OLD layout): strict patterns, gaps allowed; each value must be a
# decimal percent. These are the ORIGINAL (v1) definitions -- NPL here is Brazil-only and
# the efficiency ratio uses the pre-Q4'25 methodology.
PROSE_SPECS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("npl_15_90", (
        r"15-90\s+NPL\s+ratio[^.]{0,140}?reached\s+([0-9]+\.[0-9])\s*%",
        r"15-90\s+NPL\s+ratio[^.]{0,140}?\bto\s+([0-9]+\.[0-9])\s*%",
        r"15-90\s+NPL[^.]{0,80}?(?:was|of|at)\s+([0-9]+\.[0-9])\s*%",
    )),
    ("npl_90_plus", (
        r"90\+\s+NPL\s+ratio[^.]{0,140}?to\s+([0-9]+\.[0-9])\s*%",
        r"90\+\s+NPL\s+ratio[^.]{0,140}?reached\s+([0-9]+\.[0-9])\s*%",
        r"90\+\s+NPL[^.]{0,80}?(?:was|of|at)\s+([0-9]+\.[0-9])\s*%",
    )),
    ("efficiency_ratio", (
        r"efficiency\s+ratio[^.]{0,140}?to\s+([0-9]+\.[0-9])\s*%",
        r"efficiency\s+ratio\s+of\s+([0-9]+\.[0-9])\s*%",
    )),
)


def quarter_to_period_end(label: str) -> dt.date:
    m = QUARTER_RE.fullmatch(label)
    if not m:
        raise ValueError(f"not a quarter label: {label!r}")
    q, yy = int(m.group(1)), int(m.group(2))
    month, day = _Q_END[q]
    return dt.date(2000 + yy, month, day)


def plain_text(raw: bytes) -> str:
    """Strip tags + decode the handful of entities NU uses, collapse whitespace."""
    t = raw.decode("utf-8", errors="replace")
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"&#\d+;", " ", t)
    for a, b in (("&nbsp;", " "), ("&amp;", "&"), ("&rsquo;", "'"),
                 ("&ldquo;", '"'), ("&rdquo;", '"'), ("&ndash;", "-")):
        t = t.replace(a, b)
    return re.sub(r"\s+", " ", t)


def _to_float(token: str) -> float:
    return float(token.replace(",", ""))


def detect_current_quarter(plain: str) -> dt.date:
    """The first quarter label right after the operating-metrics marker is the
    quarter this release reports. Raise if absent (fail loud; never assume)."""
    i = plain.find(OPERATING_MARKER)
    if i < 0:
        raise ValueError(f"operating-metrics block not found ({OPERATING_MARKER!r})")
    tail = plain[i + len(OPERATING_MARKER): i + len(OPERATING_MARKER) + 30]
    m = QUARTER_RE.search(tail)
    if not m:
        raise ValueError(f"could not read current-quarter header; got {tail!r}")
    return quarter_to_period_end(m.group(0))


_MONEY_UNITS = {"usd_m", "usd_b", "brl_m", "brl_b", "usd", "brl"}


def _section(plain: str, start: str, ends: tuple[str, ...]) -> str | None:
    """Return text from `start` to the earliest of `ends` (or end of string)."""
    i = plain.find(start)
    if i < 0:
        return None
    j = len(plain)
    for e in ends:
        k = plain.find(e, i + len(start))
        if k != -1:
            j = min(j, k)
    return plain[i:j]


def _extract_specs(region: str, specs: tuple[MetricSpec, ...], period_end: dt.date,
                   source_url: str) -> list[KpiRow]:
    rows: list[KpiRow] = []
    for spec in specs:
        m = re.search(re.escape(spec.label) + r"[^0-9\-]*?(-?[\d,]+(?:\.\d+)?)", region)
        if not m:
            continue  # metric legitimately absent this quarter -> gap, not a guess
        value = _to_float(m.group(1))
        if spec.abs_value:
            value = abs(value)
        if not (spec.lo <= value <= spec.hi):
            raise ValueError(
                f"{spec.metric}={value} for {period_end} is outside sane bounds "
                f"[{spec.lo}, {spec.hi}] -- column alignment likely broke. "
                f"Refusing to store a possibly-wrong number. Source: {source_url}"
            )
        fx_basis = "reported" if spec.unit in _MONEY_UNITS else "n/a"
        rows.append(KpiRow(
            company="NU", period_end=period_end, metric=spec.metric,
            value=value, unit=spec.unit, source_url=source_url, fx_basis=fx_basis,
            definition_version=spec.definition_version,
        ))
    return rows


def _extract_structured(plain: str, period_end: dt.date, source_url: str) -> list[KpiRow]:
    # Main metrics live between the operating marker and the Other-Performance / P&L
    # sections. Scoping prevents same-label matches in the Managerial P&L tables.
    main = _section(plain, OPERATING_MARKER, (OTHER_PERF_MARKER, "Managerial P&L", "About Nu Holdings"))
    rows = _extract_specs(main or "", STRUCTURED_SPECS, period_end, source_url)
    # Credit/performance metrics only exist (structured) in the new Q4'25+ layout.
    other = _section(plain, OTHER_PERF_MARKER, ("Managerial P&L", "About Nu Holdings"))
    if other:
        rows += _extract_specs(other, OTHER_PERF_SPECS, period_end, source_url)
    return rows


def _extract_prose(plain: str, period_end: dt.date, source_url: str) -> list[KpiRow]:
    rows: list[KpiRow] = []
    for metric, patterns in PROSE_SPECS:
        for pat in patterns:
            m = re.search(pat, plain, flags=re.I)
            if m:
                rows.append(KpiRow(
                    company="NU", period_end=period_end, metric=metric,
                    value=float(m.group(1)), unit="pct",
                    source_url=source_url, fx_basis="n/a", definition_version="v1",
                ))
                break  # first matching phrasing wins; if none match -> gap
    return rows


def parse_release(raw: bytes, source_url: str) -> list[KpiRow]:
    """Parse one NU earnings release exhibit into KpiRows (current quarter only)."""
    plain = plain_text(raw)
    period_end = detect_current_quarter(plain)
    rows = _extract_structured(plain, period_end, source_url)
    # Prose credit metrics are the OLD-layout fallback only. When the new structured
    # "Other Performance Metrics" block exists, those (v2) values supersede prose, and
    # running prose too would double-emit a different (v1) definition for the same quarter.
    if OTHER_PERF_MARKER not in plain:
        rows += _extract_prose(plain, period_end, source_url)
    return rows


def find_nu_release_docs(cik: str, *, max_quarters: int = 12) -> list[tuple[Filing, str]]:
    """Find NU earnings-release exhibits containing the operating-metrics block.

    Earnings are filed in same-day clusters of 6-Ks; the release exhibit is the one
    carrying the structured metrics. Returns (filing, primary_document_url), newest first.
    """
    filings = list_filings(cik, forms=("6-K",))
    by_date: dict[str, list[Filing]] = {}
    for f in filings:
        by_date.setdefault(f.filing_date, []).append(f)

    out: list[tuple[Filing, str]] = []
    for date in sorted(by_date, reverse=True):
        cluster = by_date[date]
        if len(cluster) < 3:  # earnings clusters have several same-day 6-Ks
            continue
        for f in cluster:
            raw = fetch(f.primary_doc_url, cache_key=("docs", f.primary_document))
            if OPERATING_MARKER.encode() in raw or OPERATING_MARKER in plain_text(raw):
                out.append((f, f.primary_doc_url))
                break
        if len(out) >= max_quarters:
            break
    return out


def ingest_nu(cik: str, *, max_quarters: int = 12) -> list[KpiRow]:
    """Fetch + parse NU releases into KpiRows (does not write to DB)."""
    rows: list[KpiRow] = []
    seen: set[tuple[str, dt.date, str]] = set()  # (metric, period_end, version); newest wins
    for filing, url in find_nu_release_docs(cik, max_quarters=max_quarters):
        raw = fetch(url, cache_key=("docs", filing.primary_document))
        for row in parse_release(raw, url):
            key = (row.metric, row.period_end, row.definition_version)
            if key in seen:
                continue
            seen.add(key)
            rows.append(row)
    return rows
