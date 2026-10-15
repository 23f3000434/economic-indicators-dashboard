"""CGA published actual/provisional accounts, never BE/RE or COPPY percentages."""

import re
from decimal import Decimal

from bs4 import BeautifulSoup

from ..measurements import Definition, fiscal, measurements, number

HOME = "https://cga.gov.in/Index.aspx"


def clean(value):
    return re.sub(r"\s+", " ", value).strip()


def release_url(year, month):
    start = year - 1 if month <= 3 else year
    return f"https://cga.gov.in/writereaddata/MonthAccount/{month}{year}/DATA{str(start)[-2:]}{str(start + 1)[-2:]}.htm"


def discover(body):
    soup = BeautifulSoup(body, "html.parser")
    months = soup.select('select[id$="ddlMonth"] option[selected]')
    years = soup.select('select[id$="ddlYear"] option')
    if len(months) != 1 or not years:
        raise ValueError("CGA release selector missing")
    selected = [y for y in years if y.has_attr("selected")]
    value = (selected or years)[0]["value"]
    if not re.fullmatch(r"20\d\d-20\d\d", value):
        raise ValueError("CGA fiscal-year selector changed")
    start, end = map(int, value.split("-"))
    m = int(months[0]["value"])
    if end != start + 1 or not 1 <= m <= 12:
        raise ValueError("CGA selector invalid")
    return (end if m <= 3 else start), m


def parse(body, url, at, year, month):
    soup = BeautifulSoup(body.decode("cp1252"), "html.parser")
    text = clean(soup.get_text(" ", strip=True))
    if not re.search(r"1 Crore\s*=\s*10\s*Millions", text, re.I) or not re.search(
        r"unaudited provisional", text, re.I
    ):
        raise ValueError("CGA units/status not established")
    period = fiscal(year - 1 if month <= 3 else year, month)
    tables = [t for t in soup.find_all("table") if "Revenue Receipts" in clean(t.get_text(" ", strip=True))]
    if len(tables) != 1:
        raise ValueError("Ambiguous CGA accounts table")
    rows = [
        [clean(c.get_text(" ", strip=True)) for c in r.find_all(["td", "th"], recursive=False)]
        for r in tables[0].find_all("tr")
    ]
    header = rows[0]
    fy = f"{period.start.year}-{period.start.year + 1}"
    if (
        len(header) != 6
        or fy not in header[3]
        or ("Budget Estimates" not in header[3] and "Revised Estimates" not in header[3])
    ):
        raise ValueError("CGA estimate column changed")
    import calendar

    if month == 3:
        if not re.fullmatch(r"Provisional\s*@?\s*" + fy, header[4]):
            raise ValueError("CGA annual actual column changed")
    elif not re.fullmatch(
        r"Actuals\s*@?\s*upto\s*" + calendar.month_name[month] + r"\s*" + str(year), header[4]
    ):
        raise ValueError("CGA actual period mismatch")
    values = {}
    for row_id, label, key in [
        ("8", "Revenue Expenditure", "expenditure_revenue"),
        ("10", "Capital Expenditure", "expenditure_capital"),
        ("12", "Total Expenditure (8+10)", "expenditure_total"),
    ]:
        found = [r for r in rows if r and r[0] == row_id]
        if len(found) != 1 or len(found[0]) != 7 or found[0][1] != label:
            raise ValueError("CGA actual row changed")
        values[key] = number(found[0][4])
        if Decimal(values[key]) < 0:
            raise ValueError("Negative expenditure")
    if Decimal(values["expenditure_revenue"]) + Decimal(values["expenditure_capital"]) != Decimal(
        values["expenditure_total"]
    ):
        raise ValueError("CGA expenditure total does not reconcile")
    return measurements(
        values,
        period,
        Definition(
            group="expenditure",
            provider="cga",
            unit="inr_crore",
            methodology="union_government_actual_apr_mar",
            status="provisional",
        ),
        body,
        url,
        at,
        "Unaudited provisional actuals. BE/RE columns excluded; revenue + capital reconciles exactly to total.",
    )


class CGA:
    group = panel = "expenditure"
    provider = "cga"
    notes = [
        "Union Government actual expenditure, INR crore; April–March fiscal years. BE/RE are excluded.",
        "CGA monthly accounts are unaudited provisional actuals. Publication date is not supplied; retrieval is separate.",
    ]

    def __init__(self, settings):
        self.settings = settings
        self.interval = settings.cga_interval

    async def collect(self, fetch, at):
        year, m = discover(await fetch(HOME))
        current = fiscal(year - 1 if m <= 3 else year, m)
        # Five completed FYs (configurable), plus matching current/prior FYTD.
        periods = {(year, m), (year - 1, m)}
        periods.update(
            (y + 1, 3) for y in range(current.start.year - self.settings.report_years, current.start.year)
        )
        points = []
        for y, mo in sorted(periods):
            url = release_url(y, mo)
            points.extend(parse(await fetch(url), url, at(), y, mo))
        return points

    def coverage(self, points):
        years = {p.period.key for p in points if p.period.kind == "fiscal_year"}
        return [
            f"{len(years)} completed April–March fiscal years; current/prior FYTD use the same ending month. No BE/RE series."
        ]
