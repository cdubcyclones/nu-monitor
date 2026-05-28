import datetime as dt

import duckdb
import pytest

from nu_monitor.db import init_db, upsert_rows
from nu_monitor.normalize.schema import KpiRow


def test_init_db_creates_kpi_panel(tmp_path):
    db = tmp_path / "test.duckdb"
    init_db(db)

    con = duckdb.connect(str(db), read_only=True)
    try:
        cols = con.execute("PRAGMA table_info('kpi_panel')").fetchall()
    finally:
        con.close()

    names = {c[1] for c in cols}
    assert names == {
        "company",
        "period_end",
        "metric",
        "value",
        "unit",
        "source_url",
        "fx_basis",
        "definition_version",
    }


def test_kpi_row_requires_source_url():
    with pytest.raises(Exception):
        KpiRow(
            company="NU",
            period_end=dt.date(2025, 9, 30),
            metric="customers",
            value=127_000_000,
            unit="count",
        )  # type: ignore[call-arg]


def test_upsert_is_idempotent(tmp_path):
    db = tmp_path / "test.duckdb"
    row = KpiRow(
        company="NU",
        period_end=dt.date(2025, 9, 30),
        metric="customers",
        value=127_000_000,
        unit="count",
        source_url="https://example.com/filing",
        fx_basis="reported",
    )
    assert upsert_rows([row], db) == 1
    assert upsert_rows([row], db) == 1  # replace, not duplicate

    con = duckdb.connect(str(db), read_only=True)
    try:
        (n,) = con.execute("SELECT COUNT(*) FROM kpi_panel").fetchone()
    finally:
        con.close()
    assert n == 1


def test_definition_versions_coexist(tmp_path):
    """Same metric/quarter under two definition versions are distinct rows."""
    db = tmp_path / "test.duckdb"
    common = dict(
        company="NU", period_end=dt.date(2025, 9, 30), metric="efficiency_ratio",
        unit="pct", source_url="https://example.com/f", fx_basis="n/a",
    )
    rows = [
        KpiRow(value=27.7, definition_version="v1", **common),
        KpiRow(value=17.6, definition_version="v2", **common),
    ]
    assert upsert_rows(rows, db) == 2

    con = duckdb.connect(str(db), read_only=True)
    try:
        (n,) = con.execute("SELECT COUNT(*) FROM kpi_panel").fetchone()
    finally:
        con.close()
    assert n == 2
