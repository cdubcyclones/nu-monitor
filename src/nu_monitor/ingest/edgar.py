"""SEC EDGAR ingestion.

Two ingestion paths converge later into one panel:
  - Foreign private issuers (NU) file 6-K / 20-F. KPI data lives in earnings-release
    *exhibits* (HTML), not clean XBRL. We fetch the filing's document list and pull the
    press-release exhibit.
  - Domestic peers expose XBRL company-facts (handled in a separate function).

All requests send the SEC-required User-Agent and are gently rate-limited. Responses are
cached under data/raw/ so re-runs and tests don't re-hit the API.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

from ..config import (
    EDGAR_COMPANY_FACTS_URL,
    EDGAR_SUBMISSIONS_URL,
    RAW_DIR,
    SEC_REQUEST_DELAY,
    SEC_USER_AGENT,
)

ARCHIVES_BASE = "https://www.sec.gov/Archives/edgar/data"

_last_request_ts = 0.0


def _headers() -> dict[str, str]:
    return {"User-Agent": SEC_USER_AGENT, "Accept-Encoding": "gzip, deflate"}


def _throttle() -> None:
    global _last_request_ts
    elapsed = time.monotonic() - _last_request_ts
    if elapsed < SEC_REQUEST_DELAY:
        time.sleep(SEC_REQUEST_DELAY - elapsed)
    _last_request_ts = time.monotonic()


def _cache_path(category: str, name: str) -> Path:
    d = RAW_DIR / category
    d.mkdir(parents=True, exist_ok=True)
    return d / name


def fetch(url: str, *, cache_key: tuple[str, str] | None = None, force: bool = False) -> bytes:
    """GET a URL with SEC headers + throttling. Optionally cache bytes to data/raw/.

    cache_key = (category, filename). If cached and not force, returns cached bytes.
    """
    cached: Path | None = None
    if cache_key is not None:
        cached = _cache_path(*cache_key)
        if cached.exists() and not force:
            return cached.read_bytes()

    _throttle()
    resp = httpx.get(url, headers=_headers(), timeout=30.0, follow_redirects=True)
    resp.raise_for_status()
    data = resp.content
    if cached is not None:
        cached.write_bytes(data)
    return data


def _accession_nodash(accession: str) -> str:
    return accession.replace("-", "")


# --- Submissions / filings -------------------------------------------------


def fetch_submissions(cik: str, *, force: bool = False) -> dict:
    cik10 = cik.zfill(10)
    url = EDGAR_SUBMISSIONS_URL.format(cik=cik10)
    raw = fetch(url, cache_key=("submissions", f"CIK{cik10}.json"), force=force)
    return json.loads(raw)


@dataclass(frozen=True)
class Filing:
    cik: str
    accession: str
    form: str
    filing_date: str  # YYYY-MM-DD
    primary_document: str
    primary_doc_description: str | None

    @property
    def accession_nodash(self) -> str:
        return _accession_nodash(self.accession)

    @property
    def folder_url(self) -> str:
        return f"{ARCHIVES_BASE}/{int(self.cik)}/{self.accession_nodash}"

    @property
    def index_json_url(self) -> str:
        return f"{self.folder_url}/index.json"

    @property
    def primary_doc_url(self) -> str:
        return f"{self.folder_url}/{self.primary_document}"


def list_filings(cik: str, *, forms: tuple[str, ...] = ("6-K",), force: bool = False) -> list[Filing]:
    """Return filings of the given form(s), newest first.

    Reads filings.recent from the submissions JSON. (Sufficient for the recent
    quarters we need; older overflow files are out of scope for v1.)
    """
    sub = fetch_submissions(cik, force=force)
    recent = sub["filings"]["recent"]
    out: list[Filing] = []
    for i, form in enumerate(recent["form"]):
        if form not in forms:
            continue
        out.append(
            Filing(
                cik=cik,
                accession=recent["accessionNumber"][i],
                form=form,
                filing_date=recent["filingDate"][i],
                primary_document=recent["primaryDocument"][i],
                primary_doc_description=(recent.get("primaryDocDescription") or [None] * len(recent["form"]))[i],
            )
        )
    out.sort(key=lambda f: f.filing_date, reverse=True)
    return out


@dataclass(frozen=True)
class FilingDoc:
    name: str
    doc_type: str  # SEC "type" e.g. "EX-99.1", "6-K"
    size: int
    url: str


def fetch_filing_docs(filing: Filing, *, force: bool = False) -> list[FilingDoc]:
    """List documents inside a filing via its index.json."""
    raw = fetch(
        filing.index_json_url,
        cache_key=("index", f"{filing.accession_nodash}.json"),
        force=force,
    )
    data = json.loads(raw)
    items = data.get("directory", {}).get("item", [])
    docs: list[FilingDoc] = []
    for it in items:
        name = it.get("name", "")
        docs.append(
            FilingDoc(
                name=name,
                doc_type=it.get("type", "") or "",
                size=int(it.get("size", 0) or 0),
                url=f"{filing.folder_url}/{name}",
            )
        )
    return docs


def download_doc(doc: FilingDoc, *, force: bool = False) -> bytes:
    return fetch(doc.url, cache_key=("docs", doc.name), force=force)


# --- XBRL company-facts (peers) -------------------------------------------


def fetch_company_facts(cik: str, *, force: bool = False) -> dict:
    cik10 = cik.zfill(10)
    url = EDGAR_COMPANY_FACTS_URL.format(cik=cik10)
    raw = fetch(url, cache_key=("companyfacts", f"CIK{cik10}.json"), force=force)
    return json.loads(raw)
