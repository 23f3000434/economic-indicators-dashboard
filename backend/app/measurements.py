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
Provider = Literal["cga", "gstn", "commerce", "mospi", "gazette", "imf"]
Unit = Literal["inr_crore", "usd_billion", "percent"]


def number(text: str) -> str:
    """Accept published plain decimals only, without rounding or binary floats."""
    original = text.strip()
    if not re.fullmatch(r"-?(?:\d+|\d{1,3}(?:,\d{3})+|\d{1,2}(?:,\d{2})*,\d{3})(?:\.\d+)?", original):
        raise ValueError("Not a published decimal")
    cleaned = original.replace(",", "")
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
        if self.kind in {"fiscal_year", "fiscal_year_to_date"}:
            base = f"FY{self.start.year}-{str(self.start.year + 1)[-2:]}"
            key = base if self.kind == "fiscal_year" else f"{base}:{self.end.month:02}"
            if (
                self.key != key
                or self.end.day != calendar.monthrange(self.end.year, self.end.month)[1]
                or (self.kind == "fiscal_year_to_date" and self.end.month == 3)
            ):
                raise ValueError("Fiscal key/grain must match the complete published month window")
        if self.kind == "calendar_year" and (
            self.start != date(self.start.year, 1, 1)
            or self.end != date(self.start.year, 12, 31)
            or self.key != str(self.start.year)
        ):
            raise ValueError("Invalid calendar year")
        if self.kind == "policy_validity" and self.key != f"{self.start.isoformat()}/{self.end.isoformat()}":
            raise ValueError("Policy key must identify the effective dates")
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

    @field_validator("series_id")
    @classmethod
    def known_series(cls, value):
        if value not in CATALOGUE:
            raise ValueError("Unknown canonical reference")
        return value


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
    source_url: str | None
    retrieved_at: str | None
    response_sha256: str | None = Field(pattern=r"^[a-f0-9]{64}$")
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

        if self.value is not None and not all((self.source_url, self.retrieved_at, self.response_sha256)):
            raise ValueError("A value requires original response provenance")
        if self.source_url is not None:
            url = urlsplit(self.source_url)
            if (
                url.scheme != "https"
                or url.hostname not in HOSTS[self.definition.provider]
                or url.username
                or url.password
            ):
                raise ValueError("Unexpected source URL")
        return self


HOSTS = {
    "cga": {"cga.gov.in", "cga.nic.in", "www.cga.gov.in"},
    "gstn": {"www.gst.gov.in", "tutorial.gst.gov.in"},
    "commerce": {"www.commerce.gov.in", "commerce.gov.in", "www.pib.gov.in"},
    "mospi": {"www.mospi.gov.in"},
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
    "inflation_target": (
        "inflation_policy",
        "gazette",
        "percent",
        "Inflation target, dated Government notification",
    ),
    "inflation_target_lower": ("inflation_policy", "gazette", "percent", "Inflation target lower tolerance"),
    "inflation_target_upper": ("inflation_policy", "gazette", "percent", "Inflation target upper tolerance"),
    "cpi_yoy_2012": ("inflation", "mospi", "percent", "All-India combined headline CPI YoY, base 2012=100"),
    "cpi_yoy_2024": ("inflation", "mospi", "percent", "All-India combined headline CPI YoY, base 2024=100"),
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
