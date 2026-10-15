"""Strict measurement snapshots for non-GDP adapters; decimal strings at every boundary."""

import calendar
import hashlib
import re
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import Field, field_validator, model_validator

from .models import Model

Group = Literal["expenditure", "gst", "trade", "inflation", "inflation_policy", "debt"]
Provider = Literal["cga", "gstn", "commerce", "mospi_pib", "gazette", "imf"]
Unit = Literal["inr_crore", "usd_billion", "percent", "index_2012_100", "index_2024_100"]


def number(text: str) -> str:
    """Accept published plain decimals only, without rounding or binary floats."""
    cleaned = text.strip().replace(",", "")
    if not re.fullmatch(r"-?\d+(?:\.\d+)?", cleaned):
        raise ValueError("Not a published decimal")
    value = Decimal(cleaned)
    if not value.is_finite() or len(value.as_tuple().digits) > 100:
        raise ValueError("Invalid decimal precision")
    return format(value, "f")


class Period(Model):
    key: str
    label: str
    kind: Literal["month", "fiscal_year", "fiscal_year_to_date", "calendar_year", "policy_validity"]
    start: date
    end: date

    @model_validator(mode="after")
    def ordered(self):
        if self.start > self.end:
            raise ValueError("Reversed reporting period")
        if self.kind == "month" and (
            self.start.day != 1
            or self.end
            != date(
                self.start.year, self.start.month, calendar.monthrange(self.start.year, self.start.month)[1]
            )
            or self.key != self.start.strftime("%Y-%m")
        ):
            raise ValueError("Invalid monthly period")
        if self.kind in {"fiscal_year", "fiscal_year_to_date"} and (
            self.start.month != 4
            or self.start.day != 1
            or not self.start.year <= self.end.year <= self.start.year + 1
            or self.kind == "fiscal_year"
            and self.end != date(self.start.year + 1, 3, 31)
        ):
            raise ValueError("Invalid April–March period")
        return self


def month(year: int, value: int) -> Period:
    return Period(
        key=f"{year:04}-{value:02}",
        label=f"{calendar.month_name[value]} {year}",
        kind="month",
        start=date(year, value, 1),
        end=date(year, value, calendar.monthrange(year, value)[1]),
    )


def fiscal(year: int, through: int = 3) -> Period:
    end_year = year + 1 if through <= 3 else year
    return Period(
        key=f"FY{year}-{str(year + 1)[-2:]}" + (f":{through:02}" if through != 3 else ""),
        label=f"FY {year}–{str(year + 1)[-2:]}"
        + (f" April–{calendar.month_name[through]}" if through != 3 else ""),
        kind="fiscal_year" if through == 3 else "fiscal_year_to_date",
        start=date(year, 4, 1),
        end=date(end_year, through, calendar.monthrange(end_year, through)[1]),
    )


class Reference(Model):
    series_id: str
    period_key: str


class Definition(Model):
    group: Group
    provider: Provider
    unit: Unit
    methodology: str = Field(min_length=1, max_length=160)
    status: Literal["actual", "provisional", "final", "estimate", "unspecified"]
    published_at: date | None = None
    publication_note: str = ""
    inputs: list[Reference] = Field(default_factory=list)


class Measurement(Model):
    series_id: str = Field(pattern=r"^[a-z][a-z0-9_]{1,79}$")
    period: Period
    definition: Definition
    value: str | None
    source_url: str
    retrieved_at: str
    response_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    footnote: str = ""
    retained: bool = False

    @field_validator("value")
    @classmethod
    def decimal_value(cls, value):
        return number(value) if value is not None else None

    @model_validator(mode="after")
    def identity(self):
        # A small explicit catalogue is cheaper to audit than mutable DB metadata.
        expected = CATALOGUE.get(self.series_id)
        if expected is None or expected[:3] != (
            self.definition.group,
            self.definition.provider,
            self.definition.unit,
        ):
            raise ValueError("Unknown series or inconsistent source/unit")
        from urllib.parse import urlsplit

        url = urlsplit(self.source_url)
        if url.scheme != "https" or url.hostname not in HOSTS[self.definition.provider] or url.username:
            raise ValueError("Unexpected source URL")
        return self


HOSTS = {
    "cga": {"cga.gov.in", "cga.nic.in", "www.cga.gov.in"},
    "gstn": {"www.gst.gov.in", "tutorial.gst.gov.in"},
    "commerce": {"www.commerce.gov.in", "commerce.gov.in", "www.pib.gov.in"},
    "mospi_pib": {"www.pib.gov.in", "pib.gov.in", "www.mospi.gov.in"},
    "gazette": {"egazette.gov.in"},
    "imf": {"www.imf.org", "data.imf.org"},
}
CATALOGUE = {
    "expenditure_revenue": ("expenditure", "cga", "inr_crore", "Revenue expenditure, actual"),
    "expenditure_capital": ("expenditure", "cga", "inr_crore", "Capital expenditure, actual"),
    "expenditure_total": ("expenditure", "cga", "inr_crore", "Total expenditure, actual"),
    "gst_gross_ex_cess": (
        "gst",
        "gstn",
        "inr_crore",
        "Gross GST excluding compensation cess, before refunds",
    ),
    "gst_reported_gross": (
        "gst",
        "gstn",
        "inr_crore",
        "Source-reported gross GST (see per-point cess definition)",
    ),
    "gst_cess": ("gst", "gstn", "inr_crore", "Gross compensation cess, where separately published"),
    "gst_fy_total": ("gst", "gstn", "inr_crore", "Gross GST excluding cess, completed FY total"),
    "gst_fy_average": ("gst", "gstn", "inr_crore", "Gross GST excluding cess, completed FY monthly average"),
    "gst_fytd_average": (
        "gst",
        "gstn",
        "inr_crore",
        "Gross GST excluding cess, average of published FY months",
    ),
    "trade_exports": ("trade", "commerce", "usd_billion", "Merchandise exports"),
    "trade_imports": ("trade", "commerce", "usd_billion", "Merchandise imports"),
    "trade_balance": ("trade", "commerce", "usd_billion", "Merchandise balance (exports − imports)"),
}


def measurements(
    values: dict, period: Period, definition: Definition, body: bytes, url: str, at: str, footnote=""
) -> list[Measurement]:
    return [
        Measurement(
            series_id=key,
            period=period,
            definition=definition,
            value=value,
            source_url=url,
            retrieved_at=at,
            response_sha256=hashlib.sha256(body).hexdigest(),
            footnote=footnote,
        )
        for key, value in values.items()
    ]
