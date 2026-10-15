"""MoSPI's public release-list POST and published All-India combined headline rates."""

import asyncio
import calendar
import json
import re
from datetime import date, datetime
from urllib.parse import quote, urljoin, urlsplit

from ..measurements import Definition, measurements, month, number
from .files import pdf_pages

LIST = "https://www.mospi.gov.in/api/latest-release/get-web-latest-release-list"
HISTORY_TITLE = "press release of cpi for the month of december 2025"


def listing(body):
    payload = json.loads(body)
    if (
        payload.get("status") != "success"
        or payload.get("code") != 200
        or not isinstance(payload.get("data"), list)
    ):
        raise ValueError("Invalid MoSPI release envelope")
    page = payload["pagination"]
    if not 1 <= page["currentPage"] <= page["totalPages"] <= 5 or page["pageSize"] != 100:
        raise ValueError("MoSPI listing exceeds discovery page budget")
    rows = []
    for row in payload["data"]:
        title = re.sub(r"\s+", " ", row["title"]).strip().lower()
        if not re.fullmatch(r"press release of cpi for the month of [a-z]+ 20\d\d", title):
            continue
        file = row["file_one"]
        url = urljoin("https://www.mospi.gov.in/", file["path"])
        if (
            file.get("filemime") != "application/pdf"
            or urlsplit(url).hostname != "www.mospi.gov.in"
            or not urlsplit(url).path.lower().endswith(".pdf")
        ):
            raise ValueError("Unexpected CPI release attachment")
        rows.append((date.fromisoformat(row["published_year"]), title, quote(url, safe=":/%,")))
    return rows, page


def release_date(text):
    flat = re.sub(r"\s+", " ", text)
    found = re.search(r"Dated\s+(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+),?\s+(20\d\d)", flat, re.I)
    if not found or "NATIONAL STATISTICS OFFICE" not in flat:
        raise ValueError("CPI release identity/date missing")
    return datetime.strptime(f"{found[1]} {found[2]} {found[3]}", "%d %B %Y").date()


def parse_old(body, url, at, published, minimum_year):
    pages = pdf_pages(body, limit=30, layout=True)
    text = "\n".join(pages)
    flat = re.sub(r"\s+", " ", text)
    if release_date(text) != published or not re.search(r"last release of CPI for base 2012=100", flat, re.I):
        raise ValueError("CPI 2012 boundary release changed")
    tables = [
        p
        for p in pages
        if re.search(r"Annexure\s*VII", p) and "Year-on-year inflation" in re.sub(r"\s+", " ", p)
    ]
    tables = [p for p in tables if re.search(r"^\s*2014\s+", p, re.M)]
    if len(tables) != 1:
        raise ValueError("CPI 2012 headline time-series table missing")
    table = tables[0]
    if "Year Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec" not in re.sub(r"\s+", " ", table):
        raise ValueError("CPI historical month-column order changed")
    if not re.search(r"All India.*General CPI.*2012\s*=\s*100", re.sub(r"\s+", " ", table)):
        raise ValueError("CPI 2012 geography/base changed")
    rows = re.findall(r"^\s*(20\d\d)\s+((?:-?\d+\.\d+\*?|-)(?:\s+(?:-?\d+\.\d+\*?|-)){11})\s*$", table, re.M)
    if len(rows) != 12 or {int(y) for y, _ in rows} != set(range(2014, 2026)):
        raise ValueError("CPI 2012 historical coverage changed")
    result = []
    for year, values in rows:
        y = int(year)
        if y < minimum_year:
            continue
        for m, value in enumerate(values.split(), 1):
            status = (
                "provisional" if value.endswith("*") else "final" if (y, m) == (2025, 11) else "unspecified"
            )
            definition = Definition(
                group="inflation",
                provider="mospi",
                unit="percent",
                methodology="all_india_combined_headline_yoy_base_2012",
                status=status,
                published_at=published,
                publication_note="Last 2012-base release. Historical finality unspecified except explicitly labelled months.",
            )
            result += measurements(
                {"cpi_yoy_2012": None if value == "-" else number(value.rstrip("*"))},
                month(y, m),
                definition,
                body,
                url,
                at,
                "All-India combined general CPI YoY. Pandemic non-compilation remains null; not food/rural/urban CPI.",
            )
    return result


def parse_current(body, url, at, published):
    pages = pdf_pages(body, limit=30, layout=True)
    text = "\n".join(pages)
    flat = re.sub(r"\s+", " ", text)
    if release_date(text) != published or not re.search(r"CONSUMER PRICE INDEX ON BASE 2024=100", flat, re.I):
        raise ValueError("Unsupported CPI base or release date")
    tables = [
        p
        for p in pages
        if "All India Combined (General) level index and inflation" in re.sub(r"\s+", " ", p)
        and re.search(r"^\s*Jan-25\s+", p, re.M)
    ]
    if len(tables) != 1:
        raise ValueError("CPI 2024 combined history table missing")
    if not re.search(
        r"Month Index Inflation\s*\(%\) Rural Urban Combined Rural Urban Combined",
        re.sub(r"\s+", " ", tables[0]),
    ):
        raise ValueError("CPI index/inflation or rural/urban/combined column order changed")
    rows = re.findall(r"^\s*([A-Za-z]{3})-(\d{2})(\*?)\s+(.+?)\s*$", tables[0], re.M)
    result = []
    rates = {}
    for mon, yy, star, data in rows:
        m = list(calendar.month_abbr).index(mon)
        y = 2000 + int(yy)
        nums = data.split()
        if y == 2025:
            if len(nums) != 3:
                raise ValueError("Unexpected 2025 inflation before comparable base-year data")
            continue  # Indices exist; the source does not publish 2025 YoY under this base.
        if len(nums) != 6 or not all(re.fullmatch(r"-?\d+\.\d+", v) for v in nums):
            raise ValueError("CPI table columns changed")
        key = f"{y:04}-{m:02}"
        if key in rates:
            raise ValueError("Duplicate CPI month")
        rates[key] = number(nums[5])
        definition = Definition(
            group="inflation",
            provider="mospi",
            unit="percent",
            methodology="all_india_combined_headline_yoy_base_2024",
            status="provisional" if star else "unspecified",
            published_at=published,
        )
        result += measurements(
            {"cpi_yoy_2024": number(nums[5])},
            month(y, m),
            definition,
            body,
            url,
            at,
            "Published All-India combined general CPI YoY. Base 2024=100; not spliced to the 2012 series. Rates use unrounded source indices, not rounded displayed index arithmetic.",
        )
    if not result or sum(p.definition.status == "provisional" for p in result) != 1:
        raise ValueError("CPI current provisional month missing/ambiguous")
    latest = max(result, key=lambda p: p.period.end)
    if latest.definition.status != "provisional":
        raise ValueError("CPI provisional period is not latest")
    expected = (published.year - 1, 12) if published.month == 1 else (published.year, published.month - 1)
    if (latest.period.start.year, latest.period.start.month) != expected:
        raise ValueError("CPI observation month does not precede release month")
    # Cross-check the latest headline and mark the explicitly labelled prior final month.
    headline = re.search(
        r"Year-on-year inflation rate based on All India.*?is\s+(-?\d+\.\d+)\s*%\s*\(Provisional\)",
        flat,
        re.I,
    )
    if not headline or number(headline[1]) != latest.value:
        raise ValueError("CPI headline/history mismatch")
    y, m = latest.period.start.year, latest.period.start.month
    previous = (y - 1, 12) if m == 1 else (y, m - 1)
    if f"{calendar.month_name[previous[1]]}, {previous[0]} (Final)" in flat:
        for p in result:
            if (p.period.start.year, p.period.start.month) == previous:
                p.definition.status = "final"
    return result


class CPI:
    group = panel = "inflation"
    provider = "mospi"
    notes = [
        "All-India combined headline CPI year-on-year rates, percent. Monthly badge changes are percentage points.",
        "The final 2012-base release covers December 2025; 2024-base releases start January 2026. Keep separate series and never bridge them with a comparison.",
        "Published inflation uses unrounded underlying indices. Do not recompute it from rounded published index levels.",
    ]

    def __init__(self, settings):
        self.settings = settings
        self.interval = settings.cpi_interval

    async def collect(self, fetch, at):
        rows = []
        page = 1
        while True:
            payload = {
                "page_no": page,
                "page_size": 100,
                "search_term": "CPI",
                "sort_field": "published_year",
                "sort_order": "DESC",
                "from_date": "",
                "to_date": "",
                "lang": "en",
            }
            found, meta = listing(await fetch(LIST, method="POST", json=payload))
            if meta["currentPage"] != page:
                raise ValueError("MoSPI repeated listing page")
            rows += found
            if page == meta["totalPages"]:
                break
            page += 1
        if not rows:
            raise ValueError("No CPI releases discovered")
        published, _, url = max(rows)
        current = await asyncio.to_thread(parse_current, await fetch(url), url, at(), published)
        minimum = max(p.period.start.year for p in current) - self.settings.macro_report_years - 1
        if minimum > 2025:
            return current
        history = [r for r in rows if r[1] == HISTORY_TITLE]
        if len(history) != 1:
            raise ValueError("Last 2012-base release not discovered")
        hp, _, hu = history[0]
        old = await asyncio.to_thread(parse_old, await fetch(hu), hu, at(), hp, minimum)
        return old + current

    def coverage(self, points):
        result = []
        for sid in ("cpi_yoy_2012", "cpi_yoy_2024"):
            keys = sorted(p.period.key for p in points if p.series_id == sid)
            result.append(
                f"{sid}: {keys[0]}–{keys[-1]}, {len(keys)} calendar months."
                if keys
                else f"{sid}: unavailable."
            )
        return result
