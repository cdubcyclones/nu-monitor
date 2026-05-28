"""CLI entrypoint.

  python -m nu_monitor init           # create data/nu.duckdb with the kpi_panel schema
  python -m nu_monitor ingest-nu      # fetch + parse NU 6-K releases into kpi_panel
  python -m nu_monitor ingest-peers   # fetch + normalize peer XBRL into kpi_panel
  python -m nu_monitor ingest-all     # NU + peers
"""

from __future__ import annotations

import argparse

from .config import DB_PATH, NU_CIK
from .db import init_db, upsert_rows
from .normalize.kpi_panel import ingest_nu, ingest_peers


def _load(rows, label: str) -> None:
    n = upsert_rows(rows)
    companies = sorted({r.company for r in rows})
    quarters = sorted({r.period_end for r in rows})
    print(f"Ingested {n} {label} rows ({', '.join(companies)}) into {DB_PATH}")
    if quarters:
        print(f"  quarters: {quarters[0]} .. {quarters[-1]}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="nu_monitor", description=__doc__)
    parser.add_argument(
        "command",
        nargs="?",
        default="init",
        choices=["init", "ingest-nu", "ingest-peers", "ingest-all"],
        help="init (default): create the store; ingest-*: load KPIs",
    )
    parser.add_argument("--max-quarters", type=int, default=12,
                        help="how many NU release docs to scan back (default 12)")
    args = parser.parse_args(argv)

    if args.command == "init":
        path = init_db()
        print(f"Initialized {path}")
        return 0

    init_db()
    if args.command in ("ingest-nu", "ingest-all"):
        _load(ingest_nu(NU_CIK, max_quarters=args.max_quarters), "NU")
    if args.command in ("ingest-peers", "ingest-all"):
        _load(ingest_peers(), "peer")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
