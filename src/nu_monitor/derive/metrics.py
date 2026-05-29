"""Numerical claims for the centerpiece — computed from kpi_panel, never pattern-matched.

Everything the README narrative asserts (CAGRs, margin deltas, scale ratios, first-profit
quarters) is produced here so the conclusions are defensible.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Iterable

import duckdb

from ..config import DB_PATH


def _con() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(DB_PATH), read_only=True)


@dataclass(frozen=True)
class CompanySnapshot:
    company: str
    first_period: dt.date
    last_period: dt.date
    revenue_first_m: float          # USD millions
    revenue_last_m: float
    revenue_cagr_pct: float          # % per year (compound annual)
    margin_first_pct: float | None   # at first quarter with BOTH revenue and net_income
    margin_first_period: dt.date | None
    margin_last_pct: float | None
    margin_delta_pp: float | None    # percentage points, last minus first
    first_profit_quarter: dt.date | None
    quarters: int
    years: float


def _company_rev_ni_series(company: str) -> list[tuple[dt.date, float | None, float | None]]:
    with _con() as con:
        return con.execute(
            """
            SELECT period_end,
                   MAX(CASE WHEN metric='revenue'    THEN value END) AS rev,
                   MAX(CASE WHEN metric='net_income' THEN value END) AS ni
            FROM kpi_panel
            WHERE company = ?
              AND definition_version = 'v1'
              AND metric IN ('revenue','net_income')
            GROUP BY period_end
            HAVING MAX(CASE WHEN metric='revenue' THEN value END) IS NOT NULL
            ORDER BY period_end
            """,
            [company],
        ).fetchall()


def company_snapshot(company: str) -> CompanySnapshot | None:
    rows = _company_rev_ni_series(company)
    if not rows:
        return None
    first, last = rows[0], rows[-1]
    years = (last[0] - first[0]).days / 365.25
    cagr = (((last[1] / first[1]) ** (1 / years) - 1) * 100) if first[1] > 0 and years > 0 else float("nan")

    def margin(rev, ni):
        return None if (rev is None or ni is None) else (ni / rev) * 100

    # margin_first uses the first quarter where BOTH revenue and net_income exist (early
    # NU quarters in panel have revenue but no NI; using rows[0]'s missing NI would
    # silently make the delta None for NU and exclude the most interesting trajectory).
    first_full = next((r for r in rows if r[1] is not None and r[2] is not None), None)
    margin_first = margin(first_full[1], first_full[2]) if first_full else None
    margin_last = margin(last[1], last[2])
    delta = (margin_last - margin_first) if (margin_first is not None and margin_last is not None) else None

    fp = next((r[0] for r in rows if r[2] is not None and r[2] > 0), None)

    return CompanySnapshot(
        company=company,
        first_period=first[0], last_period=last[0],
        revenue_first_m=first[1], revenue_last_m=last[1],
        revenue_cagr_pct=cagr,
        margin_first_pct=margin_first,
        margin_first_period=first_full[0] if first_full else None,
        margin_last_pct=margin_last,
        margin_delta_pp=delta,
        first_profit_quarter=fp,
        quarters=len(rows), years=years,
    )


def cohort_snapshots(companies: Iterable[str] = ("NU", "SOFI", "SQ", "PYPL")) -> list[CompanySnapshot]:
    return [s for c in companies if (s := company_snapshot(c)) is not None]


@dataclass(frozen=True)
class DepositsPair:
    quarter: dt.date
    nu_deposits_b: float
    sofi_deposits_b: float
    ratio_nu_over_sofi: float


def latest_deposits_pair() -> DepositsPair | None:
    """NU vs SoFi deposits at the most recent quarter both report."""
    with _con() as con:
        rows = con.execute(
            """
            SELECT company, period_end, value
            FROM kpi_panel
            WHERE company IN ('NU','SOFI') AND metric='deposits'
              AND definition_version='v1'
            """
        ).fetchall()
    by_co: dict[str, dict[dt.date, float]] = {"NU": {}, "SOFI": {}}
    for c, pe, v in rows:
        by_co[c][pe] = v
    common = sorted(set(by_co["NU"]) & set(by_co["SOFI"]))
    if not common:
        return None
    q = common[-1]
    nu, sofi = by_co["NU"][q], by_co["SOFI"][q]
    return DepositsPair(q, nu, sofi, nu / sofi)


def revenue_crossover(a: str, b: str) -> dt.date | None:
    """First quarter where `a`'s revenue >= `b`'s revenue. None if `a` never overtakes `b`."""
    with _con() as con:
        rows = con.execute(
            """
            SELECT period_end,
                   MAX(CASE WHEN company=? THEN value END) AS a_rev,
                   MAX(CASE WHEN company=? THEN value END) AS b_rev
            FROM kpi_panel
            WHERE metric='revenue' AND definition_version='v1' AND company IN (?,?)
            GROUP BY period_end
            HAVING a_rev IS NOT NULL AND b_rev IS NOT NULL
            ORDER BY period_end
            """,
            [a, b, a, b],
        ).fetchall()
    for pe, a_rev, b_rev in rows:
        if a_rev >= b_rev:
            return pe
    return None
