"""CLI entrypoint.

  python -m nu_monitor init        # create data/nu.duckdb with the kpi_panel schema
  python -m nu_monitor ingest-nu   # fetch + parse NU 6-K releases into kpi_panel
"""

from __future__ import annotations

import argparse

from .config import DB_PATH, NU_CIK
from .db import init_db, upsert_rows
from .normalize.kpi_panel import ingest_nu


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="nu_monitor", description=__doc__)
    parser.add_argument(
        "command",
        nargs="?",
        default="init",
        choices=["init", "ingest-nu"],
        help="init (default): create the store; ingest-nu: load NU KPIs",
    )
    parser.add_argument("--max-quarters", type=int, default=12,
                        help="how many NU release docs to scan back (default 12)")
    args = parser.parse_args(argv)

    if args.command == "init":
        path = init_db()
        print(f"Initialized {path}")
    elif args.command == "ingest-nu":
        init_db()
        rows = ingest_nu(NU_CIK, max_quarters=args.max_quarters)
        n = upsert_rows(rows)
        quarters = sorted({r.period_end for r in rows})
        print(f"Ingested {n} NU rows across {len(quarters)} quarters into {DB_PATH}")
        if quarters:
            print(f"  quarters: {quarters[0]} .. {quarters[-1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
