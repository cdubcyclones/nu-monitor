"""Offline tests for the BCB SGS macro ingestion."""

import datetime as dt

import pytest

from nu_monitor.ingest.bcb import (
    BR_MACRO_SERIES,
    _calendar_quarter_ends,
    parse_observations,
    quarter_aligned,
)


def test_scope_is_exactly_two_verified_series():
    """Series list is intentionally locked. Adding a third needs an explicit decision."""
    codes = {s.code for s in BR_MACRO_SERIES}
    metrics = {s.metric for s in BR_MACRO_SERIES}
    assert codes == {432, 21084}
    assert metrics == {"selic_target", "household_default"}
    # every series advertises its catalog URL for provenance
    assert all(s.catalog_url.startswith("https://dadosabertos.bcb.gov.br/") for s in BR_MACRO_SERIES)


def test_parse_observations_handles_brazilian_date_and_decimal():
    raw = b'[{"data":"01/04/2026","valor":"5.37"},{"data":"01/03/2026","valor":"5.26"}]'
    out = parse_observations(raw)
    assert out == [(dt.date(2026, 3, 1), 5.26), (dt.date(2026, 4, 1), 5.37)]  # sorted


def test_quarter_aligned_daily_takes_last_value_on_or_before():
    obs = [(dt.date(2026, 3, 27), 14.75), (dt.date(2026, 3, 30), 14.50),
           (dt.date(2026, 4, 15), 14.50)]
    # Q1'26 (Mar 31) -> Mar 30 value (last on-or-before)
    val, when = quarter_aligned(obs, dt.date(2026, 3, 31), "daily")
    assert val == 14.50 and when == dt.date(2026, 3, 30)


def test_quarter_aligned_monthly_picks_same_month():
    obs = [(dt.date(2026, 2, 1), 5.42), (dt.date(2026, 3, 1), 5.26),
           (dt.date(2026, 4, 1), 5.37)]
    # Q1'26 (Mar 31) -> March observation
    val, when = quarter_aligned(obs, dt.date(2026, 3, 31), "monthly")
    assert val == 5.26 and when == dt.date(2026, 3, 1)
    # Q2'26 (Jun 30) -> no June obs yet -> None (gap, not guess)
    assert quarter_aligned(obs, dt.date(2026, 6, 30), "monthly") is None


def test_quarter_aligned_unknown_kind_raises():
    with pytest.raises(ValueError):
        quarter_aligned([], dt.date(2026, 3, 31), "weekly")


def test_calendar_quarter_ends_enumerates_correctly():
    qs = _calendar_quarter_ends(dt.date(2021, 12, 31), dt.date(2022, 9, 30))
    assert qs == [dt.date(2021, 12, 31), dt.date(2022, 3, 31),
                  dt.date(2022, 6, 30), dt.date(2022, 9, 30)]
