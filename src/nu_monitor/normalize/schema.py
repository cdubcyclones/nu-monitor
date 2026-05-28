"""Typed schema for the single normalized store.

One long table, ``kpi_panel``, keyed by (company, period_end, metric, fx_basis).
fx_basis is part of the key so we can hold both a reported and an FX-neutral value
for the same metric and quarter without collision.
"""

from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict

Unit = Literal["usd_m", "brl_m", "usd", "brl", "count", "pct", "ratio"]
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
    """One observation in the panel. ``source_url`` is mandatory provenance."""

    model_config = ConfigDict(extra="forbid")

    company: str
    period_end: dt.date
    metric: str
    value: float
    unit: Unit
    source_url: str
    fx_basis: FxBasis = "n/a"


KPI_PANEL_DDL = """
CREATE TABLE IF NOT EXISTS kpi_panel (
    company    TEXT    NOT NULL,
    period_end DATE    NOT NULL,
    metric     TEXT    NOT NULL,
    value      DOUBLE  NOT NULL,
    unit       TEXT    NOT NULL,
    source_url TEXT    NOT NULL,
    fx_basis   TEXT    NOT NULL DEFAULT 'n/a',
    PRIMARY KEY (company, period_end, metric, fx_basis)
);
"""
