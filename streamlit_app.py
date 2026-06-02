"""Streamlit Community Cloud entry point.

Why this file exists (and why the dashboard isn't pointed at directly):
  - The real dashboard lives at `src/nu_monitor/app/dashboard.py` and uses absolute
    imports (`from nu_monitor.config import ...`). Those imports require the
    `nu_monitor` package to be importable.
  - On Streamlit Cloud the build runs `pip install` against `requirements.txt`,
    which installs runtime dependencies but does NOT install this repo as a
    package -- there's no `pip install .` step. So `nu_monitor` is not on
    `sys.path` by default at runtime in the cloud build.
  - This shim inserts `src/` onto `sys.path` so absolute imports resolve, then
    delegates to the real dashboard via `runpy.run_path` with
    `run_name="__main__"` -- the exact load mode Streamlit uses for entry
    scripts, so the dashboard executes identically to a direct
    `streamlit run src\nu_monitor\app\dashboard.py` locally.
  - Bonus: with `nu_monitor.config` loaded from `src/`, `DB_PATH`
    (computed via `Path(__file__).resolve().parent.parent.parent`) resolves to
    the repo root, so the committed `data/nu.duckdb` is found correctly --
    regardless of where the CWD is set.

Local entry points still work unchanged:
  - `streamlit run src\nu_monitor\app\dashboard.py` (after `pip install -e .`)
  - `streamlit run streamlit_app.py` (no install required; this file handles it)
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

_DASHBOARD = _SRC / "nu_monitor" / "app" / "dashboard.py"
runpy.run_path(str(_DASHBOARD), run_name="__main__")
