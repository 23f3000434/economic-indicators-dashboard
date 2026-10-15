"""Commerce merchandise trade, monthly and matching FYTD/completed fiscal years."""

import asyncio
import calendar
import re
from datetime import date, datetime
from decimal import Decimal
from urllib.parse import quote, urljoin, urlsplit

from bs4 import BeautifulSoup

from ..measurements import Definition, Reference, fiscal, measurements, month, number
from .files import pdf_pages

INDEX = "https://www.commerce.gov.in/ministryofcommerce/taxonomy/term/530"


def monthly_nodes(body):
    soup = BeautifulSoup(body, "html.parser")
    result = []
    for a in soup.select("a[href]"):
        label = a.get_text(" ", strip=True).lower()
        if "monthly press release" in label and "foreign trade" in label:
            url = urljoin(INDEX, a["href"])
            if not re.fullmatch(r"https://www\.commerce\.gov\.in/ministryofcommerce/node/\d+", url):
                raise ValueError("Unexpected Commerce node")
            if url not in result:
                result.append(url)
    if not result:
        raise ValueError("Commerce monthly-release listing missing")
    return result


def attachment(body):
    soup = BeautifulSoup(body, "html.parser")
    urls = {
        urljoin(INDEX, a["href"])
        for a in soup.select("a[href]")
        if urlsplit(a["href"]).path.lower().endswith(".pdf")
    }
    dates = {t.get("datetime", "")[:10] for t in soup.select("time[datetime]")}
    if len(urls) != 1 or len(dates) != 1:
        raise ValueError("Commerce attachment/date missing or ambiguous")
    url = urls.pop()
    if urlsplit(url).hostname != "www.commerce.gov.in":
        raise ValueError("Unexpected trade PDF host")
    return quote(url, safe=":/%"), date.fromisoformat(dates.pop())


def points(values, period, body, url, at, published):
    definition = Definition(
        group="trade",
        provider="commerce",
        unit="usd_billion",
        methodology="india_merchandise_usd_billion_apr_mar",
        status="unspecified",
        published_at=published,
        publication_note="Published merchandise values. Services estimates excluded; no final merchandise status is inferred.",
    )
    if any(Decimal(v) < 0 for v in values.values()):
        raise ValueError("Negative trade flow")
    raw = measurements(values, period, definition, body, url, at)
    refs = [Reference(series_id=p.series_id, period_key=p.period.key) for p in raw]
    balance = format(Decimal(values["trade_exports"]) - Decimal(values["trade_imports"]), "f")
    raw += measurements(
        {"trade_balance": balance},
        period,
        definition.model_copy(update={"inputs": refs}),
        body,
        url,
        at,
        "Calculated merchandise exports − imports; negative values are deficits. Combined goods/services balance excluded.",
    )
    return raw


def parse_pdf(body, url, at):
    text = "\n".join(pdf_pages(body, limit=20, layout=True))
    flat = re.sub(r"\s+", " ", text)
    match = re.search(r"Dated\s+(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+),?\s+(20\d\d)", flat, re.I)
    if not match or "Department of Commerce" not in flat:
        raise ValueError("Commerce release identity/date missing")
    published = datetime.strptime(f"{match[1]} {match[2]} {match[3]}", "%d %B %Y").date()
    result = []
    current_ym = None
    for table in (1, 2):
        found = re.search(r"Table\s*" + str(table) + r"\s*:\s*Trade during\s+(.+?)Services\s*\*?", flat, re.I)
        if not found:
            raise ValueError("Merchandise trade table missing")
        band = found[1]
        if len(re.findall(r"\((?:US\$|USD) Billion\)", band)) != 2:
            raise ValueError("Trade units changed")
        row = re.search(
            r"Merchandise\s+Exports\s+([\d,.]+)\s+([\d,.]+)\s+Imports\s+([\d,.]+)\s+([\d,.]+)\s*$", band
        )
        if not row:
            raise ValueError("Trade merchandise rows changed")
        if table == 1:
            dates = re.findall(r"([A-Za-z]+)\s+(20\d\d)", band[: band.index("Merchandise")])
            dates = list(dict.fromkeys(dates))
            if len(dates) != 2:
                raise ValueError("Trade month headers missing")
            current_ym = (int(dates[0][1]), list(calendar.month_name).index(dates[0][0]))
            if dates[1] != (dates[0][0], str(current_ym[0] - 1)):
                raise ValueError("Trade monthly comparison mismatch")
            periods = [month(*current_ym), month(current_ym[0] - 1, current_ym[1])]
        else:
            years = list(
                dict.fromkeys(
                    int(y) for y in re.findall(r"(20\d\d)-\d{2}", band[: band.index("Merchandise")])
                )
            )
            start = current_ym[0] - (current_ym[1] <= 3)
            if years != [start, start - 1] or ("April-" + calendar.month_name[current_ym[1]]) not in band:
                raise ValueError("Trade FY comparison mismatch")
            periods = [fiscal(start, current_ym[1]), fiscal(start - 1, current_ym[1])]
        for i, period in enumerate(periods):
            result += points(
                {"trade_exports": number(row[1 + i]), "trade_imports": number(row[3 + i])},
                period,
                body,
                url,
                at,
                published,
            )
    return result


def parse_historical_html(body, url, at):
    soup = BeautifulSoup(body, "html.parser")
    text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))
    pub = re.search(r"Posted On:\s*(\d{1,2} [A-Z]{3} 20\d\d)", text)
    if not pub or "Ministry of Commerce & Industry" not in text:
        raise ValueError("Historical Commerce identity/date missing")
    published = datetime.strptime(pub[1], "%d %b %Y").date()
    candidates = {}
    for table in soup.find_all("table"):
        # Ignore the page's mobile wrapper table and duplicate desktop/mobile copies.
        if table.find("table"):
            continue
        rows = [
            [
                re.sub(r"\s+", " ", c.get_text(" ", strip=True))
                for c in tr.find_all(["td", "th"], recursive=False)
            ]
            for tr in table.find_all("tr")
        ]
        exports = [r for r in rows if len(r) == 4 and r[:2] == ["Merchandise", "Exports"]]
        imports = [r for r in rows if len(r) == 3 and r[0] == "Imports"]
        if len(exports) != 1 or not imports:
            continue
        header = " ".join(rows[0])
        years = re.findall(r"(20\d\d)-\d{2}\s*\(USD Billion\)", header)
        if len(years) != 2:
            continue
        y, prior = map(int, years)
        if prior != y - 1 or published.month != 4 or published.year != y + 1:
            raise ValueError("Historical annual headers changed")
        for i, fy in enumerate((y, prior)):
            parsed = points(
                {"trade_exports": number(exports[0][2 + i]), "trade_imports": number(imports[0][1 + i])},
                fiscal(fy),
                body,
                url,
                at,
                published,
            )
            for point in parsed:
                key = point.series_id, point.period.key
                if key in candidates and candidates[key].value != point.value:
                    raise ValueError("Duplicate historical tables disagree")
                candidates[key] = point
    if len(candidates) != 6:
        raise ValueError("Historical annual merchandise table missing")
    return list(candidates.values())


class Trade:
    group = panel = "trade"
    provider = "commerce"
    notes = [
        "Merchandise only, USD billion; negative balance = exports − imports. Services and combined-trade balances excluded.",
        "Monthly/FYTD comparisons use the same month window; annual periods run April–March.",
        "Different releases may revise earlier observations. Each point retains its accepted publication vintage; no final status is invented.",
        "Balances subtract the displayed source amounts. Independently rounded published deficit headlines may differ by 0.01 billion.",
    ]

    def __init__(self, settings):
        self.settings = settings
        self.interval = settings.trade_interval

    async def collect(self, fetch, at):
        first = await fetch(INDEX)
        nodes = monthly_nodes(first)
        pdf, _ = attachment(await fetch(nodes[0]))
        latest = await asyncio.to_thread(parse_pdf, await fetch(pdf), pdf, at())
        latest_year = max(p.period.start.year for p in latest)
        current_fy = max(
            p.period.start.year for p in latest if p.period.kind in {"fiscal_year", "fiscal_year_to_date"}
        )
        candidates = list(latest)
        seen = {nodes[0]}
        annual = any(p.period.kind == "fiscal_year" for p in latest)
        for page in range(0, 6):
            if annual:
                break
            listing = first if page == 0 else await fetch(INDEX + f"?page={page}")
            for node in monthly_nodes(listing):
                if node in seen:
                    continue
                seen.add(node)
                attachment_url, listed = attachment(await fetch(node))
                if listed.month != 4 or listed.year < current_fy:
                    continue
                rows = await asyncio.to_thread(parse_pdf, await fetch(attachment_url), attachment_url, at())
                if any(p.period.kind == "fiscal_year" for p in rows):
                    candidates += rows
                    annual = True
                    break
        if not annual:
            raise ValueError("Latest completed FY release not discovered within page budget")
        # Verified bootstrap references replace dead legacy WordPress archive links.
        # They do not cap future collection years; current discovery remains dynamic.
        for url in self.settings.trade_history_urls:
            if urlsplit(url).hostname != "www.pib.gov.in":
                raise ValueError("Unexpected historical trade host")
            candidates += await asyncio.to_thread(parse_historical_html, await fetch(url), url, at())
        chosen = {}
        for p in candidates:
            if p.period.start.year < latest_year - self.settings.report_years - 1:
                continue
            key = p.series_id, p.period.key
            if key not in chosen or p.definition.published_at > chosen[key].definition.published_at:
                chosen[key] = p
        return list(chosen.values())

    def coverage(self, points):
        years = sorted({p.period.key for p in points if p.period.kind == "fiscal_year"})
        return [
            f"Completed fiscal years: {', '.join(years)}. Current/prior monthly and FYTD amounts share matching windows.",
            "Historical PIB release references are verified bootstrap sources; dead Commerce WordPress PDFs are not used.",
        ]
