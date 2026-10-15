"""Dated statutory inflation target, independent of monthly economic observations."""

import asyncio
import re
from datetime import datetime
from decimal import Decimal

from ..batches import MeasurementBatch, scope
from ..measurements import Definition, Period, measurements
from .files import pdf_pages


def parse(body, url, at):
    flat = re.sub(r"\s+", " ", " ".join(pdf_pages(body, limit=5, layout=True)))
    if not all(
        v in flat
        for v in [
            "MINISTRY OF FINANCE",
            "Department of Economic Affairs",
            "section 45ZA",
            "Reserve Bank of India Act, 1934",
        ]
    ):
        raise ValueError("Inflation policy authority/identity changed")
    pub = re.search(r"New Delhi, the (\d{1,2})(?:st|nd|rd|th) ([A-Za-z]+), (20\d\d)", flat)
    window = re.search(
        r"beginning from the (\d{1,2})\s*(?:st|nd|rd|th) day of ([A-Za-z]+), (20\d\d) and ending on the (\d{1,2})\s*(?:st|nd|rd|th) ([A-Za-z]+), (20\d\d)",
        flat,
    )
    notification = re.search(r"S\.O\.\s*(\d+)\(E\)", flat)
    if not pub or not window or not notification:
        raise ValueError("Inflation policy dates/notification missing")

    def dated(d, m, y):
        return datetime.strptime(f"{d} {m} {y}", "%d %B %Y").date()

    published = dated(*pub.groups())
    start = dated(*window.groups()[:3])
    end = dated(*window.groups()[3:])
    if published > start:
        raise ValueError("Unexpected retrospective policy window")
    period = Period(
        key=f"{start.isoformat()}/{end.isoformat()}",
        label=f"{start:%d %B %Y}–{end:%d %B %Y}",
        kind="policy_validity",
        start=start,
        end=end,
    )
    words = {
        w.lower(): str(i)
        for i, w in enumerate(
            ["Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten"]
        )
    }
    values = {}
    for label, key in [
        ("Inflation Target", "inflation_target"),
        ("Upper tolerance level", "inflation_target_upper"),
        ("Lower tolerance level", "inflation_target_lower"),
    ]:
        found = re.findall(re.escape(label) + r"\s*:\s*([A-Za-z]+|\d+(?:\.\d+)?) per cent\.", flat)
        if len(found) != 1:
            raise ValueError("Policy percentage missing/ambiguous")
        value = words.get(found[0].lower(), found[0])
        if not re.fullmatch(r"\d+(?:\.\d+)?", value):
            raise ValueError("Unsupported policy numeric wording")
        values[key] = value
    if (
        not Decimal(values["inflation_target_lower"])
        <= Decimal(values["inflation_target"])
        <= Decimal(values["inflation_target_upper"])
    ):
        raise ValueError("Inconsistent target tolerance")
    return measurements(
        values,
        period,
        Definition(
            group="inflation_policy",
            provider="gazette",
            unit="percent",
            methodology="india_inflation_target_rbi_act_45za",
            status="final",
            published_at=published,
            publication_note=f"S.O. {notification[1]}(E), statutory policy; not a monthly CPI observation.",
        ),
        body,
        url,
        at,
    )


class Policy:
    group = "inflation_policy"
    panel = "inflation"
    provider = "gazette"
    native_tls = True
    notes = [
        "The inflation target/tolerance is a separately dated Government policy under RBI Act section 45ZA, not a monthly CPI series.",
        "Only the verified notification validity window is applied. A successor notification needs review/configuration; no automatic extension after expiry.",
    ]

    def __init__(self, settings):
        self.settings = settings
        self.interval = settings.policy_interval

    async def collect(self, fetch, at):
        rows = await asyncio.to_thread(
            parse, await fetch(self.settings.policy_url), self.settings.policy_url, at()
        )
        return MeasurementBatch(
            rows,
            scope(("inflation_target", "inflation_target_lower", "inflation_target_upper"), [rows[0].period]),
        )

    def coverage(self, points):
        return [
            f"Policy validity: {p.period.label}." for p in points if p.series_id == "inflation_target"
        ] or ["No verified inflation-target policy stored."]
