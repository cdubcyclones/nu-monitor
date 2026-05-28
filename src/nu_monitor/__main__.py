"""CLI entrypoint: ``python -m nu_monitor [init]`` initializes the store."""

from __future__ import annotations

import argparse

from .db import init_db


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="nu_monitor", description=__doc__)
    parser.add_argument(
        "command",
        nargs="?",
        default="init",
        choices=["init"],
        help="init: create data/nu.duckdb with the kpi_panel schema (default)",
    )
    args = parser.parse_args(argv)

    if args.command == "init":
        path = init_db()
        print(f"Initialized {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
