"""Official GSTN workbook + discovered monthly PDF; consistent cess treatment."""

import calendar
import json
import re
from datetime import date, datetime, timedelta
from decimal import Decimal
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from ..measurements import Definition, Reference, measurements, month, number
from .files import pdf_pages, workbook

INDEX = "https://www.gst.gov.in/download/gststatistics"
NEWS = "https://www.gst.gov.in/fomessage/newsupdates"


def parse_month(text):
    if text.isdigit():
        d = date(1899, 12, 30) + timedelta(days=int(text))
        if not 2000 <= d.year <= 2199:
            raise ValueError("Invalid workbook month")
        return d.year, d.month
    match = re.fullmatch(r"([A-Za-z]+)[ _-]+(\d{2}|20\d\d)", text.strip())
    if not match:
        raise ValueError("Invalid published month")
    names = {m[:3].lower(): i for i, m in enumerate(calendar.month_name) if i}
    return 2000 + int(match[2]) if len(match[2]) == 2 else int(match[2]), names[match[1][:3].lower()]


def definition(methodology, published=None, inputs=()):
    return Definition(
        group="gst",
        provider="gstn",
        unit="inr_crore",
        methodology=methodology,
        status="provisional",
        published_at=published,
        inputs=list(inputs),
    )


def gross_points(values, period, body, url, at, published=None, tolerance=Decimal("0.02")):
    total = Decimal(values["Total Gross GST Revenue"])
    cess = Decimal(values["CESS"]) if "CESS" in values else None
    components = sum(Decimal(values[k]) for k in ("CGST", "SGST", "IGST"))
    if (
        min(total, components, cess if cess is not None else total) < 0
        or abs(total - components - (cess or 0)) > tolerance
    ):
        raise ValueError("GST gross components do not reconcile")
    raw = measurements(
        {"gst_reported_gross": format(total, "f")},
        period,
        definition(
            "gross_including_compensation_cess" if cess is not None else "gross_excluding_compensation_cess",
            published,
        ),
        body,
        url,
        at,
    )
    refs = [Reference(series_id="gst_reported_gross", period_key=period.key)]
    if cess is not None:
        raw += measurements(
            {"gst_cess": format(cess, "f")},
            period,
            definition("compensation_cess_before_refunds", published),
            body,
            url,
            at,
        )
        refs.append(Reference(series_id="gst_cess", period_key=period.key))
    raw += measurements(
        {"gst_gross_ex_cess": format(total - (cess or 0), "f")},
        period,
        definition("gross_cgst_sgst_igst_before_refunds", published, refs),
        body,
        url,
        at,
        "Source-reported gross less compensation cess when included. No refunds deducted. CGST+SGST+IGST reconciliation checked at publication precision.",
    )
    return raw


def parse_workbook(body, url, at):
    chosen = {}
    for name, rows in workbook(body):
        flat = {key: value for r in rows for key, value in r.items()}
        sheet_period = parse_month(name)
        # Published workbook anomalies are accepted narrowly, after validating both
        # actual month headers. Jan-25 reverses B/C and calls its monthly band Daily.
        heading = flat.get("B2")
        allowed = (
            heading == "Monthly"
            or (sheet_period == (2025, 1) and heading == "Daily")
            or (sheet_period == (2025, 11) and heading == "Montly")
        )
        if "Amount in crores" not in flat.get("A1", "") or not allowed or flat.get("A3") != "GST Collections":
            raise ValueError("GST workbook units/headings changed")
        columns = {col: parse_month(flat[f"{col}3"]) for col in ("B", "C")}
        current = sheet_period
        if set(columns.values()) != {current, (current[0] - 1, current[1])}:
            raise ValueError("GST comparison period mismatch")
        start = [
            i
            for i, r in enumerate(rows)
            if any(v.strip() == "A.3. Gross GST Revenue(A.1+A.2)" for v in r.values())
        ]
        if len(start) != 1:
            raise ValueError("GST gross band missing")
        band = []
        for row in rows[start[0] + 1 :]:
            index = next((int(re.search(r"\d+", k)[0]) for k in row if k.startswith("A")), 0)
            label = row.get(f"A{index}", "").strip()
            if label.startswith("B.1."):
                break
            if label in {"CGST", "SGST", "IGST", "CESS", "Total Gross GST Revenue"}:
                band.append((label, index))
        if len({x[0] for x in band}) != len(band):
            raise ValueError("Duplicate gross row")
        for col, ym in columns.items():
            values = {label: number(format(Decimal(flat[f"{col}{index}"]), "f")) for label, index in band}
            points = gross_points(values, month(*ym), body, url, at)
            for point in points:
                key = (point.series_id, point.period.key)
                # Later source sheets can restate prior-year comparators. Keep the newest vintage.
                if key not in chosen or chosen[key][0] < current:
                    chosen[key] = (current, point)
    if not chosen:
        raise ValueError("Empty GST workbook")
    return [item[1] for item in chosen.values()]


def discover_workbook(body):
    soup = BeautifulSoup(body, "html.parser")
    links = {
        urljoin(INDEX, a["href"])
        for a in soup.select("a[href]")
        if a["href"].endswith("/Gross_Net_Tax_collection.xlsx")
    }
    if len(links) != 1:
        raise ValueError("GST workbook discovery changed")
    url = links.pop()
    if urlsplit(url).hostname != "tutorial.gst.gov.in":
        raise ValueError("Unexpected GST workbook host")
    return url


def discover_release(body):
    payload = json.loads(body)
    candidates = []
    for row in payload["data"]:
        title = row["title"]
        match = re.fullmatch(
            r"Gross and Net GST revenue collections for the month of ([A-Za-z]+),? (20\d\d)", title, re.I
        )
        if not match:
            continue
        ym = parse_month(f"{match[1]}-{match[2]}")
        soup = BeautifulSoup(row["content"], "html.parser")
        urls = {
            a["href"]
            for a in soup.select("a[href]")
            if urlsplit(a["href"]).hostname == "tutorial.gst.gov.in" and a["href"].lower().endswith(".pdf")
        }
        if len(urls) != 1:
            raise ValueError("Ambiguous GST release")
        candidates.append((ym, urls.pop(), datetime.strptime(row["date"], "%d/%m/%Y").date()))
    if not candidates:
        raise ValueError("No monthly GST release discovered")
    return max(candidates)


def parse_pdf(body, url, at, ym, published):
    text = pdf_pages(body, limit=12)[0]
    if "Amount in crores" not in text or not re.search(r"provisional", text, re.I):
        raise ValueError("GST PDF units/status missing")
    periods = re.search(r"GST Collections\s+([A-Za-z]{3}-\d{2})\s+([A-Za-z]{3}-\d{2})", text)
    if not periods or parse_month(periods[2]) != ym or parse_month(periods[1]) != (ym[0] - 1, ym[1]):
        raise ValueError("GST PDF period mismatch")
    band = text.split("A.3. Gross GST Revenue(A.1+A.2)")
    if len(band) != 2:
        raise ValueError("GST PDF gross table changed")
    band = band[1].split("B.1. Domestic Refunds")[0]
    parsed = {}
    for label in ["CGST", "SGST", "IGST", "CESS", "Total Gross GST Revenue"]:
        found = re.findall(r"^\s*" + label + r"\s+([^\n]+)", band, re.M)
        if len(found) != 1:
            if label == "CESS" and not found:
                continue
            raise ValueError("GST PDF gross row missing/duplicate")
        tokens = found[0].split()
        nums = [number(t) for t in tokens if not t.endswith("%")]
        if len(nums) != 4:
            raise ValueError("GST PDF column count changed")
        parsed[label] = nums
    points = []
    for offset, y in [(0, ym[0] - 1), (1, ym[0])]:
        points += gross_points(
            {k: v[offset] for k, v in parsed.items()}, month(y, ym[1]), body, url, at, published, Decimal("2")
        )
    return points


class GST:
    group = panel = "gst"
    provider = "gstn"
    notes = [
        "Primary series: gross CGST + SGST + IGST before refunds, excluding compensation cess consistently.",
        "Older reported gross includes cess; newer releases separate its treatment. Source totals/cess retain distinct methodology labels.",
        "Averages use published months only. Annual totals/averages require all 12 fiscal months; missing history stays null.",
    ]

    def __init__(self, settings):
        self.settings = settings
        self.interval = settings.gst_interval

    async def collect(self, fetch, at):
        url = discover_workbook(await fetch(INDEX))
        points = parse_workbook(await fetch(url), url, at())
        ym, pdf, published = discover_release(await fetch(NEWS))
        latest = parse_pdf(await fetch(pdf), pdf, at(), ym, published)
        lookup = {(p.series_id, p.period.key): p for p in points}
        for p in latest:
            lookup[p.series_id, p.period.key] = p
        earliest = ym[0] - self.settings.report_years - 1
        return [p for p in lookup.values() if p.period.start.year >= earliest]

    def coverage(self, points):
        months = sorted(p.period.key for p in points if p.series_id == "gst_gross_ex_cess")
        return [
            f"Monthly workbook/release coverage {months[0]}–{months[-1]} ({len(months)} published months)."
            if months
            else "No published months stored.",
            "Workbook history starts April 2023; earlier FYs are unverified and are not reconstructed from state-only tables.",
        ]
