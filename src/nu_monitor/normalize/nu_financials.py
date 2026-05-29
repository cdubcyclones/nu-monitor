"""Backfill NU revenue / net_income / deposits from the IFRS financial-statement
exhibits (nufs*.htm), to make those three series contiguous across ~18 quarters.

Unlike the earnings releases (slide images + hidden text), the financial statements are
REAL HTML tables, so they parse cleanly with pandas. But they carry their own wrinkles,
documented in docs/DATA_SOURCES.md and handled here:

  - The "Three-month period ended" header text is present only in some quarters; older and
    newest docs show bare dates. We classify each value column by its header (period label
    + date/year) rather than trusting a fixed column index or label text.
  - The bottom-line label drifts: "Net income for the period" / "...for the year" /
    "Profit (loss) for the period" / "Profit for the period" / "Loss for the year" /
    "Profit (loss) for the three-month period". Matched by regex.
  - Q4 exhibits (nufs4q*) carry the ANNUAL income statement, not a Q4-standalone column.
    We derive Q4 = full-year minus nine-month (both reported figures; exact subtraction),
    using the same year's nufs3q nine-month column. Q4'21 has no nine-month source, so its
    revenue/net_income is left to the earnings release / gapped (deposits still load).

We read ONLY revenue, net_income, deposits here. Operating metrics (customers, ARPAC,
NPL, cost-to-serve, efficiency) are NOT in these statements and are never backfilled.
Statements are in US$ thousands; we convert to NU's units (usd_m, usd_b).
"""

from __future__ import annotations

import datetime as dt
import io
import re
from dataclasses import dataclass

import pandas as pd

from ..ingest.edgar import Filing, fetch, list_filings
from .schema import KpiRow

_DATE = re.compile(r"(\d{2})/(\d{2})/(\d{4})")
_YEAR = re.compile(r"\b(20\d{2})\b")
# bottom-line net-income / profit row (NOT "...before income taxes", NOT "...attributable")
_NET_INCOME = re.compile(
    r"^(net income|net loss|net income \(loss\)|profit|loss|profit \(loss\)) "
    r"for the (three-month )?(period|year)$",
    re.I,
)
_REVENUE = "total revenue"


def _num(x) -> float | None:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return None
    s = str(x).strip().replace(",", "")
    if s in ("-", "", "nan", "—", "–", "None"):
        return None
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    try:
        v = float(s)
    except ValueError:
        return None
    return -v if neg else v


def _income_table(tables: list[pd.DataFrame]) -> pd.DataFrame | None:
    for t in tables:
        labels = [str(x).strip() for x in t.iloc[:, 0].tolist()]
        has_rev = any(l.lower() == _REVENUE for l in labels)
        has_ni = any(_NET_INCOME.match(l) for l in labels)
        if has_rev and has_ni:
            return t
    return None


def _balance_table(tables: list[pd.DataFrame]) -> pd.DataFrame | None:
    for t in tables:
        labels = [str(x).strip() for x in t.iloc[:, 0].tolist()]
        if any(l == "Deposits" for l in labels) and any(l == "Total liabilities" for l in labels):
            return t
    return None


@dataclass(frozen=True)
class _ValueCol:
    col: int
    period: str | None  # '3m' | '6m' | '9m' | None
    date: dt.date | None
    year: int | None


def _value_columns(t: pd.DataFrame, header_rows: int = 3) -> list[_ValueCol]:
    out: list[_ValueCol] = []
    n = min(header_rows, len(t))
    for c in range(t.shape[1]):
        text = " ".join(str(t.iloc[r, c]) for r in range(n))
        low = text.lower()
        period = "3m" if "three-month" in low else "6m" if "six-month" in low else "9m" if "nine-month" in low else None
        dm = _DATE.search(text)
        if dm:
            out.append(_ValueCol(c, period, dt.date(int(dm.group(3)), int(dm.group(1)), int(dm.group(2))), None))
            continue
        ym = _YEAR.search(text)
        if ym:
            out.append(_ValueCol(c, period, None, int(ym.group(1))))
    return out


def _row_value(t: pd.DataFrame, predicate, col: int, what: str, source_url: str) -> float:
    labels = [str(x).strip() for x in t.iloc[:, 0].tolist()]
    idx = [i for i, l in enumerate(labels) if predicate(l)]
    if len(idx) != 1:
        raise ValueError(f"{what}: matched {len(idx)} rows (need exactly 1). Source: {source_url}")
    val = _num(t.iloc[idx[0], col])
    if val is None:
        raise ValueError(f"{what}: empty value at col {col}. Source: {source_url}")
    return val


@dataclass(frozen=True)
class Financials:
    period_end: dt.date
    kind: str  # 'quarter' | 'annual'
    revenue: float          # US$ thousands (period or full-year per kind)
    net_income: float
    deposits: float | None  # US$ thousands, balance at period_end
    nine_month_revenue: float | None
    nine_month_net_income: float | None


def parse_financials(raw: bytes, source_url: str) -> Financials:
    tables = pd.read_html(io.StringIO(raw.decode("utf-8", errors="replace")))
    inc = _income_table(tables)
    if inc is None:
        raise ValueError(f"income statement not found. Source: {source_url}")

    cols = _value_columns(inc)
    three = [v for v in cols if v.period == "3m" and v.date]
    nine = [v for v in cols if v.period == "9m" and v.date]
    bare_dates = [v for v in cols if v.period is None and v.date]
    years = [v for v in cols if v.date is None and v.year]

    if three:  # Q2/Q3 interim: pick current three-month column
        cur = max(three, key=lambda v: v.date)
        period_end, kind = cur.date, "quarter"
    elif bare_dates:  # Q1 interim: single (three-month) period, just dated
        cur = max(bare_dates, key=lambda v: v.date)
        period_end, kind = cur.date, "quarter"
    elif years:  # Q4 exhibit: ANNUAL statement, no quarterly column
        cur = max(years, key=lambda v: v.year)
        period_end, kind = dt.date(cur.year, 12, 31), "annual"
    else:
        raise ValueError(f"could not identify a current period column. Source: {source_url}")

    revenue = _row_value(inc, lambda l: l.lower() == _REVENUE, cur.col, "Total revenue", source_url)
    net_income = _row_value(inc, lambda l: bool(_NET_INCOME.match(l)), cur.col, "net income line", source_url)

    nine_rev = nine_ni = None
    if nine:
        ncur = max(nine, key=lambda v: v.date)
        nine_rev = _row_value(inc, lambda l: l.lower() == _REVENUE, ncur.col, "Total revenue (9M)", source_url)
        nine_ni = _row_value(inc, lambda l: bool(_NET_INCOME.match(l)), ncur.col, "net income (9M)", source_url)

    deposits = None
    bs = _balance_table(tables)
    if bs is not None:
        # Interim balance sheets are dated (09/30/2025); annual ones are year-labeled
        # (2025). Pick the most recent column either way -> the current quarter-end.
        dated = [(v, v.date or dt.date(v.year, 12, 31)) for v in _value_columns(bs) if v.date or v.year]
        if dated:
            bcur = max(dated, key=lambda x: x[1])[0]
            deposits = _row_value(bs, lambda l: l == "Deposits", bcur.col, "Deposits", source_url)

    return Financials(period_end, kind, revenue, net_income, deposits, nine_rev, nine_ni)


# Sanity bounds on converted (NU-unit) values; violations fail loud.
_BOUNDS = {"revenue": (100, 100_000), "net_income": (-50_000, 50_000), "deposits": (1, 3_000)}


def _row(metric: str, period_end: dt.date, value: float, unit: str, url: str) -> KpiRow:
    lo, hi = _BOUNDS[metric]
    if not (lo <= value <= hi):
        raise ValueError(f"{metric}={value} ({period_end}) outside sane bounds [{lo},{hi}]. Source: {url}")
    return KpiRow(company="NU", period_end=period_end, metric=metric, value=round(value, 1),
                  unit=unit, source_url=url, fx_basis="reported", definition_version="v1")


def find_nufs_filings(cik: str) -> list[Filing]:
    return [f for f in list_filings(cik, forms=("6-K",)) if f.primary_document.startswith("nufs")]


def ingest_nu_financials(cik: str) -> list[KpiRow]:
    """Parse all nufs exhibits; emit revenue/net_income/deposits, deriving Q4 = FY - 9M."""
    rows: list[KpiRow] = []
    annual: dict[int, tuple[float, float, str]] = {}        # year -> (fy_rev, fy_ni, url)
    nine_month: dict[int, tuple[float, float]] = {}          # year -> (rev9m, ni9m)

    for f in find_nufs_filings(cik):
        url = f.primary_doc_url
        raw = fetch(url, cache_key=("docs", f.primary_document))
        # Some "nufs" exhibits are not the financial statements (e.g. nufs4q22 carries no
        # income/balance lines; FY2022 audited figures are in the 20-F, out of v1 scope).
        # Skip a doc that has no statement markers at all; still fail loud on a doc that has
        # markers but whose structure we can't parse.
        if not any(m in raw for m in (b"Total revenue", b"Total Revenue", b"Deposits")):
            continue
        fin = parse_financials(raw, url)

        if fin.deposits is not None:  # balance is always a real quarter-end
            rows.append(_row("deposits", fin.period_end, fin.deposits / 1e6, "usd_b", url))

        if fin.kind == "quarter":
            rows.append(_row("revenue", fin.period_end, fin.revenue / 1e3, "usd_m", url))
            rows.append(_row("net_income", fin.period_end, fin.net_income / 1e3, "usd_m", url))
            if fin.nine_month_revenue is not None:
                nine_month[fin.period_end.year] = (fin.nine_month_revenue, fin.nine_month_net_income)
        else:  # annual: hold for Q4 derivation
            annual[fin.period_end.year] = (fin.revenue, fin.net_income, url)

    # Derive Q4 standalone = full-year minus nine-month (exact; both reported).
    for year, (fy_rev, fy_ni, url) in annual.items():
        if year in nine_month:
            q4 = dt.date(year, 12, 31)
            rows.append(_row("revenue", q4, (fy_rev - nine_month[year][0]) / 1e3, "usd_m", url))
            rows.append(_row("net_income", q4, (fy_ni - nine_month[year][1]) / 1e3, "usd_m", url))
    return rows
