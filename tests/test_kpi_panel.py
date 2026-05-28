"""Tests for the NU KPI parser, against committed fixtures (offline, no network).

Fixtures are two real NU 6-K release exhibits chosen to exercise BOTH layouts:
  - nu_q3_2025_oldfmt.htm: pre-Q4'25 layout; credit metrics in prose.
  - nu_q1_2026_newfmt.htm: Q4'25+ layout; credit metrics structured, cost-to-serve negative.
"""

import datetime as dt
from pathlib import Path

import pytest

from nu_monitor.normalize.kpi_panel import (
    detect_current_quarter,
    parse_release,
    plain_text,
    quarter_to_period_end,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _rows_by_metric(docname: str, url: str = "https://example.com/filing"):
    raw = (FIXTURES / docname).read_bytes()
    return {r.metric: r for r in parse_release(raw, url)}


def test_quarter_to_period_end():
    assert quarter_to_period_end("Q3'25") == dt.date(2025, 9, 30)
    assert quarter_to_period_end("Q4'21") == dt.date(2021, 12, 31)
    assert quarter_to_period_end("Q1'26") == dt.date(2026, 3, 31)


def test_q3_2025_old_format_matches_anchors():
    rows = _rows_by_metric("nu_q3_2025_oldfmt.htm")
    assert rows["customers"].period_end == dt.date(2025, 9, 30)
    # User-provided anchors, hand-checked against the filing.
    assert rows["customers"].value == pytest.approx(127.0)
    assert rows["customers"].unit == "count_m"
    assert rows["arpac"].value == pytest.approx(13.4)
    assert rows["net_income"].value == pytest.approx(782.7)
    assert rows["deposits"].value == pytest.approx(38.8)
    # Credit metrics come from prose in the old format -> original (v1) definition.
    assert rows["npl_15_90"].value == pytest.approx(4.2)
    assert rows["npl_15_90"].unit == "pct"
    assert rows["npl_15_90"].definition_version == "v1"
    assert rows["efficiency_ratio"].value == pytest.approx(27.7)
    assert rows["efficiency_ratio"].definition_version == "v1"
    # Provenance is always populated.
    assert all(r.source_url for r in rows.values())


def test_q1_2026_new_format_and_quirks():
    rows = _rows_by_metric("nu_q1_2026_newfmt.htm")
    assert rows["customers"].period_end == dt.date(2026, 3, 31)
    assert rows["customers"].value == pytest.approx(135.2)
    assert rows["arpac"].value == pytest.approx(15.9)
    # Cost-to-serve is printed negative in the new layout; we store its magnitude.
    assert rows["cost_to_serve"].value == pytest.approx(1.0)
    # Credit metrics are structured (not prose) in the new layout -> redefined (v2).
    assert rows["npl_15_90"].value == pytest.approx(5.0)
    assert rows["npl_15_90"].definition_version == "v2"
    assert rows["npl_90_plus"].value == pytest.approx(6.5)
    assert rows["efficiency_ratio"].value == pytest.approx(17.6)
    assert rows["efficiency_ratio"].definition_version == "v2"
    # The new doc must NOT also emit a v1 prose value for the same quarter.
    assert sum(1 for r in parse_release((FIXTURES / "nu_q1_2026_newfmt.htm").read_bytes(),
                                        "u") if r.metric == "npl_15_90") == 1


def test_fx_basis_assignment():
    rows = _rows_by_metric("nu_q3_2025_oldfmt.htm")
    assert rows["revenue"].fx_basis == "reported"      # money metric
    assert rows["customers"].fx_basis == "n/a"          # count metric
    assert rows["npl_15_90"].fx_basis == "n/a"          # ratio metric


def test_missing_marker_fails_loud():
    with pytest.raises(ValueError):
        detect_current_quarter("a document with no metrics block")
    with pytest.raises(ValueError):
        parse_release(b"<html><body>no metrics here</body></html>", "https://example.com/x")


def test_plain_text_strips_tags():
    out = plain_text(b"<p>Hello&nbsp;<b>world</b></p>")
    assert "Hello world" in out
    assert "<" not in out
