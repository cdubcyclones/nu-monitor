"""Offline tests for the IFRS financial-statement parser (synthetic HTML)."""

import datetime as dt

import pytest

from nu_monitor.normalize.nu_financials import _num, parse_financials

# Interim (Q3-like): three-month + nine-month income statement, dated balance sheet.
INTERIM = """
<html><body>
<table>
<tr><td></td><td></td><td></td><td>Three-month period ended</td><td>Three-month period ended</td><td>Three-month period ended</td><td></td><td>Nine-month period ended</td><td>Nine-month period ended</td><td>Nine-month period ended</td></tr>
<tr><td></td><td>Note</td><td></td><td>09/30/2025</td><td></td><td>09/30/2024</td><td></td><td>09/30/2025</td><td></td><td>09/30/2024</td></tr>
<tr><td>Total revenue</td><td></td><td></td><td>4172716</td><td></td><td>2943188</td><td></td><td>11088875</td><td></td><td>8527780</td></tr>
<tr><td>Net income for the period</td><td></td><td></td><td>782678</td><td></td><td>553386</td><td></td><td>1976873</td><td></td><td>1419472</td></tr>
</table>
<table>
<tr><td></td><td>Note</td><td></td><td>09/30/2025</td><td></td><td>12/31/2024</td></tr>
<tr><td>Compulsory and other deposits at central banks</td><td>15</td><td></td><td>8166047</td><td></td><td>6743336</td></tr>
<tr><td>Deposits</td><td>22</td><td></td><td>38775929</td><td></td><td>28855065</td></tr>
<tr><td>Total liabilities</td><td></td><td></td><td>57809276</td><td></td><td>42284138</td></tr>
</table>
</body></html>
"""

# Annual (Q4-like): YEAR-labeled columns, "Net income for the year".
ANNUAL = """
<html><body>
<table>
<tr><td></td><td>Note</td><td></td><td>2025</td><td></td><td>2024</td></tr>
<tr><td>Total revenue</td><td></td><td></td><td>15774775</td><td></td><td>11512550</td></tr>
<tr><td>Net income for the year</td><td></td><td></td><td>2871273</td><td></td><td>1972000</td></tr>
</table>
<table>
<tr><td></td><td>Note</td><td></td><td>2025</td><td></td><td>2024</td></tr>
<tr><td>Deposits</td><td>22</td><td></td><td>41900000</td><td></td><td>28855065</td></tr>
<tr><td>Total liabilities</td><td></td><td></td><td>70000000</td><td></td><td>42284138</td></tr>
</table>
</body></html>
"""


def test_num_handles_parens_commas_dashes():
    assert _num("4,172,716") == 4172716
    assert _num("(1,275,711)") == -1275711
    assert _num("-") is None
    assert _num(782678) == 782678


def test_interim_three_month_and_nine_month():
    fin = parse_financials(INTERIM.encode(), "https://example.com/nufs3q25")
    assert fin.kind == "quarter"
    assert fin.period_end == dt.date(2025, 9, 30)
    assert fin.revenue == pytest.approx(4172716)          # current 3-month, not 9-month
    assert fin.net_income == pytest.approx(782678)
    assert fin.nine_month_revenue == pytest.approx(11088875)
    assert fin.nine_month_net_income == pytest.approx(1976873)
    # Deposits = the liability line, not "...deposits at central banks"
    assert fin.deposits == pytest.approx(38775929)


def test_annual_year_columns():
    fin = parse_financials(ANNUAL.encode(), "https://example.com/nufs4q25")
    assert fin.kind == "annual"
    assert fin.period_end == dt.date(2025, 12, 31)
    assert fin.revenue == pytest.approx(15774775)         # full-year
    assert fin.net_income == pytest.approx(2871273)
    assert fin.deposits == pytest.approx(41900000)        # year-labeled balance column
    assert fin.nine_month_revenue is None


def test_missing_income_statement_fails_loud():
    with pytest.raises(ValueError):
        parse_financials(b"<html><body><table><tr><td>nothing</td></tr></table></body></html>", "u")
