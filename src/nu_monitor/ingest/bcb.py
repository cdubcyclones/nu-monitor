"""Minimal Brazil macro layer (BCB SGS).

Scope is deliberately tight: TWO series only, both verified against the BCB SGS
catalog, both providing the macro context the project's geographic-judgment story needs
and nothing more.

  - SGS 432:    Meta para a taxa Selic (Copom-defined target rate, % p.a., DAILY)
                https://dadosabertos.bcb.gov.br/dataset/432-taxa-de-juros---meta-selic-definida-pelo-copom
  - SGS 21084:  Inadimplência da carteira de crédito - Pessoas físicas - Total
                (% of household credit portfolio >= 90 days delinquent, MONTHLY)
                https://dadosabertos.bcb.gov.br/dataset/21084-inadimplencia-da-carteira-de-credito---pessoas-fisicas---total

Quarterly alignment: end-of-quarter observation in both cases -- the last daily value
on or before the quarter end for Selic; the observation reported for the quarter's last
month (Mar / Jun / Sep / Dec) for the monthly default series. Documented in
docs/DATA_SOURCES.md.

NOT in scope (do not add without an explicit decision): IBGE, IPCA, unemployment,
real exchange rate, household credit balance, or any other series.
"""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass
from pathlib import Path

import httpx

from ..config import RAW_DIR
from ..normalize.schema import KpiRow

# BCB returns 406 when the response would be too large. Bounding with dataInicial of
# 2021-01-01 covers the entire NU-IPO-onwards window (NU's first quarter is Q4'21) and
# keeps the response within the SGS endpoint's size limit.
BCB_SGS_URL = ("https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados"
               "?formato=json&dataInicial=01/01/2021")


@dataclass(frozen=True)
class SgsSeries:
    code: int
    metric: str
    kind: str            # 'daily' or 'monthly'
    catalog_url: str
    label: str           # human-readable description for logs and docs


BR_MACRO_SERIES: tuple[SgsSeries, ...] = (
    SgsSeries(
        code=432, metric="selic_target", kind="daily",
        catalog_url="https://dadosabertos.bcb.gov.br/dataset/432-taxa-de-juros---meta-selic-definida-pelo-copom",
        label="Meta Selic (Copom-defined target, % p.a., daily)",
    ),
    SgsSeries(
        code=21084, metric="household_default", kind="monthly",
        catalog_url="https://dadosabertos.bcb.gov.br/dataset/21084-inadimplencia-da-carteira-de-credito---pessoas-fisicas---total",
        label="Inadimplência PF Total (% household credit portfolio 90+ days delinquent, monthly)",
    ),
)


def _cache_path(code: int) -> Path:
    d = RAW_DIR / "bcb"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"sgs_{code}.json"


def fetch_sgs(series: SgsSeries, *, force: bool = False) -> bytes:
    cached = _cache_path(series.code)
    if cached.exists() and not force:
        return cached.read_bytes()
    # No custom Accept header -- the SGS endpoint returns 406 if Accept: application/json
    # is sent explicitly, even though the response *is* JSON. (Surprising, but reproducible.)
    r = httpx.get(BCB_SGS_URL.format(code=series.code), timeout=60.0)
    r.raise_for_status()
    cached.write_bytes(r.content)
    return r.content


def parse_observations(raw: bytes) -> list[tuple[dt.date, float]]:
    """Each row is {'data': 'dd/MM/yyyy', 'valor': 'X.YY'} — return sorted (date, val)."""
    out: list[tuple[dt.date, float]] = []
    for row in json.loads(raw):
        dd, mm, yyyy = row["data"].split("/")
        out.append((dt.date(int(yyyy), int(mm), int(dd)), float(row["valor"])))
    out.sort()
    return out


def quarter_aligned(observations: list[tuple[dt.date, float]], period_end: dt.date,
                    kind: str) -> tuple[float, dt.date] | None:
    """Return (value, observation_date) for the period_end's quarter, or None if no data.

    daily   -> last observation on or before the period_end.
    monthly -> observation whose (year, month) matches the period_end (the last month of
               the quarter is the period_end month: Mar/Jun/Sep/Dec).
    """
    if kind == "daily":
        cand = [(d, v) for d, v in observations if d <= period_end]
        return (cand[-1][1], cand[-1][0]) if cand else None
    if kind == "monthly":
        cand = [(d, v) for d, v in observations
                if d.year == period_end.year and d.month == period_end.month]
        return (cand[-1][1], cand[-1][0]) if cand else None
    raise ValueError(f"unknown kind: {kind!r}")


def _calendar_quarter_ends(start: dt.date, until: dt.date) -> list[dt.date]:
    """Calendar quarter ends in [start, until], inclusive."""
    qends: list[dt.date] = []
    year = start.year
    while True:
        for month, day in ((3, 31), (6, 30), (9, 30), (12, 31)):
            pe = dt.date(year, month, day)
            if pe < start:
                continue
            if pe > until:
                return qends
            qends.append(pe)
        year += 1


# Sanity bounds: both series are percent rates; values outside fail loud.
_BOUNDS = {"selic_target": (0.0, 50.0), "household_default": (0.0, 30.0)}

# NU's first quarter in the panel; macro panel aligns to the same start.
_MACRO_START = dt.date(2021, 12, 31)


def ingest_br_macro(today: dt.date | None = None) -> list[KpiRow]:
    """Emit BR_MACRO rows for calendar quarter ends Q4'21 -> last completed quarter."""
    today = today or dt.date.today()
    rows: list[KpiRow] = []
    for series in BR_MACRO_SERIES:
        observations = parse_observations(fetch_sgs(series))
        qends = _calendar_quarter_ends(_MACRO_START, today)
        for pe in qends:
            res = quarter_aligned(observations, pe, series.kind)
            if res is None:
                continue  # series doesn't yet have data for this quarter end
            value, obs_date = res
            lo, hi = _BOUNDS[series.metric]
            if not (lo <= value <= hi):
                raise ValueError(
                    f"{series.metric}={value} for {pe} (obs {obs_date}) outside "
                    f"sane bounds [{lo},{hi}]. Source: {series.catalog_url}"
                )
            rows.append(KpiRow(
                company="BR_MACRO", period_end=pe, metric=series.metric,
                value=round(value, 2), unit="pct",
                source_url=series.catalog_url, fx_basis="n/a", definition_version="v1",
            ))
    return rows
