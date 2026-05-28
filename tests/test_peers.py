"""Offline tests for peer XBRL frame extraction."""

import datetime as dt

import pytest

from nu_monitor.normalize.kpi_panel import PeerFact, extract_peer_facts

# Minimal company-facts shaped like SEC's, with both calendar-quarter frames and
# noise that must be ignored (non-frame entries, YTD durations, wrong unit).
FACTS = {
    "facts": {
        "us-gaap": {
            "Revenues": {
                "units": {
                    "USD": [
                        {"end": "2025-09-30", "val": 6_114_952_000, "frame": "CY2025Q3", "accn": "0001-25-000123"},
                        {"end": "2025-06-30", "val": 6_054_457_000, "frame": "CY2025Q2", "accn": "0001-25-000100"},
                        {"end": "2025-09-30", "val": 17_000_000_000, "frame": "CY2025Q3YTD", "accn": "x"},  # YTD: ignore
                        {"end": "2025-09-30", "val": 999, "accn": "y"},  # no frame: ignore
                    ],
                    "EUR": [
                        {"end": "2025-09-30", "val": 42, "frame": "CY2025Q3", "accn": "eur"},  # wrong unit: ignore
                    ],
                }
            },
            "Deposits": {
                "units": {
                    "USD": [
                        {"end": "2025-09-30", "val": 32_946_399_000, "frame": "CY2025Q3I", "accn": "0001-25-000123"},
                        {"end": "2025-09-30", "val": 5, "frame": "CY2025Q3", "accn": "dur"},  # duration frame: ignore for instant
                    ]
                }
            },
        }
    }
}


def test_duration_frames_only_quarterly():
    spec = PeerFact("revenue", "Revenues", "usd_m", instant=False, divisor=1e6)
    rows = {r.period_end: r for r in extract_peer_facts(FACTS, "0001512673", "SQ", spec)}
    assert set(rows) == {dt.date(2025, 6, 30), dt.date(2025, 9, 30)}
    assert rows[dt.date(2025, 9, 30)].value == pytest.approx(6114.95, abs=0.1)
    assert rows[dt.date(2025, 9, 30)].unit == "usd_m"
    assert rows[dt.date(2025, 9, 30)].fx_basis == "reported"
    # provenance points at the reporting filing's folder (dashless accession)
    assert "000125000123" in rows[dt.date(2025, 9, 30)].source_url


def test_instant_frame_for_balance_items():
    spec = PeerFact("deposits", "Deposits", "usd_b", instant=True, divisor=1e9)
    rows = extract_peer_facts(FACTS, "0001818874", "SOFI", spec)
    assert len(rows) == 1
    assert rows[0].period_end == dt.date(2025, 9, 30)
    assert rows[0].value == pytest.approx(32.9, abs=0.05)
    assert rows[0].unit == "usd_b"


def test_missing_tag_returns_nothing():
    spec = PeerFact("revenue", "NotARealTag", "usd_m", instant=False, divisor=1e6)
    assert extract_peer_facts(FACTS, "0001818874", "SOFI", spec) == []
