"""DuckDB connection + store initialization."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import duckdb

from .config import DB_PATH
from .normalize.schema import KPI_PANEL_DDL, KpiRow


def connect(db_path: Path | str | None = None, *, read_only: bool = False) -> duckdb.DuckDBPyConnection:
    path = Path(db_path) if db_path is not None else DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path), read_only=read_only)


def init_db(db_path: Path | str | None = None) -> Path:
    """Create the store and the kpi_panel table if absent. Returns the db path."""
    path = Path(db_path) if db_path is not None else DB_PATH
    con = connect(path)
    try:
        con.execute(KPI_PANEL_DDL)
    finally:
        con.close()
    return path


def upsert_rows(rows: Iterable[KpiRow], db_path: Path | str | None = None) -> int:
    """Insert/replace validated rows into kpi_panel. Returns count written."""
    rows = list(rows)
    if not rows:
        return 0
    con = connect(db_path)
    try:
        con.execute(KPI_PANEL_DDL)
        con.executemany(
            """
            INSERT OR REPLACE INTO kpi_panel
                (company, period_end, metric, value, unit, source_url, fx_basis, definition_version)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (r.company, r.period_end, r.metric, r.value, r.unit, r.source_url,
                 r.fx_basis, r.definition_version)
                for r in rows
            ],
        )
    finally:
        con.close()
    return len(rows)
