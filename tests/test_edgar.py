"""Offline tests for EDGAR URL/path construction (no network)."""

from nu_monitor.ingest.edgar import Filing, _accession_nodash


def _filing(accession="0001292814-25-003948", cik="0001691493", doc="nupr3q25_6k.htm"):
    return Filing(
        cik=cik,
        accession=accession,
        form="6-K",
        filing_date="2025-11-13",
        primary_document=doc,
        primary_doc_description="6-K",
    )


def test_accession_nodash():
    assert _accession_nodash("0001292814-25-003948") == "000129281425003948"


def test_filing_urls_drop_leading_zeros_in_cik():
    f = _filing()
    # SEC Archives path uses the integer CIK (no leading zeros) + dashless accession.
    assert f.folder_url == (
        "https://www.sec.gov/Archives/edgar/data/1691493/000129281425003948"
    )
    assert f.index_json_url.endswith("/index.json")
    assert f.primary_doc_url.endswith("/nupr3q25_6k.htm")
