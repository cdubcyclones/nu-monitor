"""Central configuration: paths, endpoints, identifiers.

Data-source identifiers that affect *which numbers we ingest* (e.g. BCB SGS series
codes, IBGE SIDRA tables) are intentionally left unset until verified in their phase.
Per project policy we do not hardcode unverified codes — a wrong code yields a wrong
series, which is worse than a missing one.
"""

from __future__ import annotations

import os
from pathlib import Path

# --- Paths -----------------------------------------------------------------
PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
DB_PATH = DATA_DIR / "nu.duckdb"


def _load_dotenv() -> None:
    """Load KEY=VALUE pairs from a .env at the project root into os.environ.

    Intentionally tiny (no python-dotenv dependency). Existing env vars win.
    """
    env_file = PROJECT_ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_dotenv()

# --- SEC EDGAR -------------------------------------------------------------
# SEC blocks requests without a contact email in the User-Agent header.
SEC_USER_AGENT = os.environ.get(
    "SEC_USER_AGENT", "nu-monitor (set SEC_USER_AGENT in .env)"
)
EDGAR_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
EDGAR_COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_REQUEST_DELAY = 0.15  # seconds between requests; SEC asks for <10 req/s

# Nu Holdings is a foreign private issuer: files 6-K / 20-F, not 10-K/10-Q.
NU_CIK = "0001691493"
NU_COMPANY = "NU"

# Domestic peers expose XBRL company-facts. Block changed its ticker SQ -> XYZ
# in 2025; we keep the panel code "SQ" for continuity but resolve by current ticker.
PEERS: dict[str, str] = {
    "SOFI": "SOFI",  # SoFi Technologies
    "SQ": "XYZ",     # Block, Inc. (ticker SQ -> XYZ, 2025)
    "PYPL": "PYPL",  # PayPal Holdings
}

# --- Banco Central do Brasil (BCB) SGS -- Phase 2 --------------------------
BCB_SGS_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados?formato=json"
# VERIFY each code in the SGS catalog before use (Phase 2). Left empty on purpose.
BCB_SERIES: dict[str, int] = {}

# --- IBGE SIDRA -- Phase 2 -------------------------------------------------
IBGE_SIDRA_URL = "https://apisidra.ibge.gov.br/values/{query}"
# VERIFY each table id before use (Phase 2). Left empty on purpose.
IBGE_TABLES: dict[str, str] = {}

# --- Apple App Store RSS (optional signal) -- Phase 3 ----------------------
APPLE_REVIEWS_URL = "https://itunes.apple.com/br/rss/customerreviews/id={app_id}/json"
# VERIFY Nubank's BR App Store id before use (Phase 3). Left unset on purpose.
NUBANK_BR_APP_ID: str | None = None
