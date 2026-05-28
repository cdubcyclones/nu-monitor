"""Typed schema for the single normalized store.

One long table, ``kpi_panel``, keyed by (company, period_end, metric, fx_basis).
fx_basis is part of the key so we can hold both a reported and an FX-neutral value
for the same metric and quarter without collision.
"""

from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict

# Units keep stored values faithful to the figure printed in the filing, so a value
# can be hand-checked against the source without mental rescaling. e.g. "127.0" customers
# is stored as 127.0 with unit count_m (millions), not 127_000_000.
Unit = Literal[
    "usd_m",    # US$ millions
    "usd_b",    # US$ billions
    "brl_m",    # R$ millions
    "brl_b",    # R$ billions
    "usd",      # US$ (per-customer figures)
    "brl",      # R$
    "count",    # absolute count
    "count_m",  # millions of units (e.g. customers)
    "pct",      # percent, stored as the printed number (4.2 means 4.2%)
    "ratio",    # dimensionless ratio
]
FxBasis = Literal["reported", "fx_neutral", "n/a"]

# Canonical metric names used across companies.
METRICS = (
    "customers",
    "arpac",
    "npl_15_90",
    "npl_90_plus",
    "deposits",
    "efficiency_ratio",
    "revenue",
    "net_income",
    "cost_to_serve",
)


class KpiRow(BaseModel):
    """One observation in the panel. ``source_url`` is mandatory provenance.

    ``definition_version`` distinguishes metrics whose definition changed over time
    (e.g. NU's efficiency ratio and NPL were redefined in the Q4'25 reporting format).
    Rows with the same (company, period_end, metric) but different versions are NOT the
    same series and must not be charted together without a caveat.
    """

    model_config = ConfigDict(extra="forbid")

    company: str
    period_end: dt.date
    metric: str
    value: float
    unit: Unit
    source_url: str
    fx_basis: FxBasis = "n/a"
    definition_version: str = "v1"


KPI_PANEL_DDL = """
CREATE TABLE IF NOT EXISTS kpi_panel (
    company            TEXT    NOT NULL,
    period_end         DATE    NOT NULL,
    metric             TEXT    NOT NULL,
    value              DOUBLE  NOT NULL,
    unit               TEXT    NOT NULL,
    source_url         TEXT    NOT NULL,
    fx_basis           TEXT    NOT NULL DEFAULT 'n/a',
    definition_version TEXT    NOT NULL DEFAULT 'v1',
    PRIMARY KEY (company, period_end, metric, definition_version)
);
"""
