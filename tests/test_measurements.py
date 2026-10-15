from datetime import date

import pytest
from app.measurements import Period, number


def test_numeric_formats_are_strict_and_preserve_zero_and_deflation():
    assert number("1,20,396") == "120396"
    assert number("120,396.50") == "120396.50"
    assert number("0") == "0"
    assert number("-0.3") == "-0.3"
    for invalid in ["NaN", "Infinity", "1,2,3", "1e999", "—", ""]:
        with pytest.raises(ValueError):
            number(invalid)


def test_fiscal_period_key_and_grain_cannot_disagree():
    args = dict(
        key="FY2026-27:08",
        label="April–August 2026",
        kind="fiscal_year_to_date",
        start=date(2026, 4, 1),
        end=date(2026, 8, 31),
    )
    Period(**args)
    for change in [{"key": "FY2025-26:08"}, {"end": date(2026, 8, 30)}, {"kind": "fiscal_year"}]:
        with pytest.raises(ValueError):
            Period(**{**args, **change})
