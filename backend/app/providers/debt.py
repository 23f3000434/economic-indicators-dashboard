"""IMF WEO GGXWDG_NGDP via the official World Bank Data360 public mirror."""

import asyncio
import csv
import hashlib
import json
import re
from datetime import date, datetime
from decimal import Decimal
from io import StringIO

from ..batches import MeasurementBatch, scope
from ..measurements import Definition, Period, SupportingSource, fiscal, measurements, number
from .files import pdf_pages

DATA = "https://data360files.worldbank.org/data360-data/data/IMF_WEO/IMF_WEO_GGXWDG_NGDP.csv"
METADATA = "https://data360files.worldbank.org/data360-data/metadata/IMF_WEO/IMF_WEO_GGXWDG_NGDP.json"


def period(country, year):
    if country == "IND":
        return fiscal(year)
    return Period(
        key=str(year),
        label=f"CY {year}",
        kind="calendar_year",
        start=date(year, 1, 1),
        end=date(year, 12, 31),
    )


def appendix_rules(body, vintage):
    pages = pdf_pages(body, limit=40, layout=True)
    header = re.sub(r"\s+", " ", pages[0]).lower()
    if f"world economic outlook, {vintage:%B %Y}".lower() not in header:
        raise ValueError("Debt appendix does not match the mirror vintage; review DEBT_APPENDIX_URL")
    exceptional = [p for p in pages if "Economies with Exceptional Reporting Periods" in p]
    if len(exceptional) != 1 or not re.search(r"India\s+Apr/Mar\s+Apr/Mar", exceptional[0]):
        raise ValueError("India reporting convention changed")
    if "United States" in exceptional[0]:
        raise ValueError("US exceptional reporting convention requires review")
    result = {}
    for country, name, coverage, accounting in [
        ("IND", "India", "CG,SG", "C"),
        ("USA", "United States", "CG,SG,LG", "A"),
    ]:
        found = []
        for page in pages:
            if "Government Finance" not in page or "Latest Actual" not in page:
                continue
            found += re.findall(
                rf"(?m)^\s*{country}\s+{name}\s+(?:MoF|Other)\s+(20\d\d)(/\d\d)?\s+\d{{4}}\s+{coverage}\s+{accounting}\s+",
                page,
            )
        if len(found) != 1 or bool(found[0][1]) != (country == "IND"):
            raise ValueError("Debt country actual-year/coverage convention changed")
        result[country] = int(found[0][0])
    return result


def parse(body, metadata, at, start, end, appendix, appendix_url):
    meta = json.loads(metadata)
    definition = meta["series_description"]
    if (
        definition["idno"] != "IMF_WEO_GGXWDG_NGDP"
        or definition["database_id"] != "IMF_WEO"
        or definition["measurement_unit"] != "Percentage of GDP"
        or definition["periodicity"] != "Annual"
        or "Central, state, and local governments" not in definition["definition_long"]
        or definition["sources"][0]["organization"] != "International Monetary Fund (IMF)"
    ):
        raise ValueError("Debt metadata definition/source changed")
    vintage = date.fromisoformat(definition["version_statement"]["version_date"])
    if vintage > datetime.fromisoformat(at.replace("Z", "+00:00")).date():
        raise ValueError("Future debt metadata vintage")
    cutoffs = appendix_rules(appendix, vintage)
    rows, seen = [], set()
    for row in csv.DictReader(StringIO(body.decode("utf-8-sig"))):
        country = row["REF_AREA"]
        if country not in {"IND", "USA"}:
            continue
        year = int(row["TIME_PERIOD"])
        if not start <= year <= end:
            continue
        required = {
            "FREQ": "A",
            "DATABASE_ID": "IMF_WEO",
            "INDICATOR": "IMF_WEO_GGXWDG_NGDP",
            "UNIT_MEASURE": "PT_GDP",
            "UNIT_MULT": "0",
            "UNIT_TYPE": "RATIO",
            "COMP_BREAKDOWN_1": "V_LST",
            "COMP_BREAKDOWN_2": "_Z",
            "COMP_BREAKDOWN_3": "_Z",
            "SEX": "_Z",
            "AGE": "_Z",
            "URBANISATION": "_Z",
            "OBS_CONF": "PU",
        }
        if any(row[k] != v for k, v in required.items()):
            raise ValueError("Debt units, coverage or vintage dimension changed")
        if (country, year) in seen:
            raise ValueError("Ambiguous debt observation")
        seen.add((country, year))
        status = row["OBS_STATUS"]
        if status not in {"A", "E", "F"}:
            raise ValueError("Unreviewed debt observation status")
        value = number(row["OBS_VALUE"]) if row["OBS_VALUE"].strip() else None
        if value is not None and not Decimal(0) <= Decimal(value) <= Decimal(1000):
            raise ValueError("Invalid gross-debt ratio")
        rows += measurements(
            {"debt_india" if country == "IND" else "debt_us": value},
            period(country, year),
            Definition(
                group="debt",
                provider="world_bank_data360",
                unit="percent",
                methodology="imf_weo_general_government_gross_debt_percent_gdp",
                status="estimate" if status in {"E", "F"} or year > cutoffs[country] else "actual",
                source_status=f"{status}: {row['OBS_STATUS_LABEL']}",
                vintage_date=vintage,
                supporting_sources=[
                    SupportingSource(
                        role="metadata", url=METADATA, response_sha256=hashlib.sha256(metadata).hexdigest()
                    ),
                    SupportingSource(
                        role="methodology",
                        url=appendix_url,
                        response_sha256=hashlib.sha256(appendix).hexdigest(),
                    ),
                ],
                publication_note=(
                    "IMF WEO via World Bank Data360, Latest Version snapshot. Vintage is the mirror's "
                    "metadata version date, not an observation publication date. Source A means Normal value. "
                    f"Actual/estimate classification uses the matching WEO appendix's Government Finance latest actual year: {cutoffs[country]}. "
                    "India: FY Apr–Mar, central/state coverage, cash; US: CY Jan–Dec, central/state/local, accrual. "
                    "Coverage/accounting differences limit comparability. Future source years are excluded."
                ),
            ),
            body,
            DATA,
            at,
        )
    if not all(
        any(p.series_id == s and p.value is not None for p in rows) for s in ("debt_india", "debt_us")
    ):
        raise ValueError("Comparable country coverage missing")
    expected = set()
    for country, sid in [("IND", "debt_india"), ("USA", "debt_us")]:
        expected |= scope([sid], [period(country, y) for y in range(start, end + 1)])
    return MeasurementBatch(rows, expected)


class Debt:
    group = panel = "debt"
    provider = "world_bank_data360"
    native_tls = True
    notes = [
        "IMF WEO GGXWDG_NGDP, redistributed by World Bank Data360: general-government gross debt as % of GDP; not central-government or external debt.",
        "Common IMF headline definition with coverage differences: India central/state (cash, FY Apr–Mar); US central/state/local (accrual, CY Jan–Dec). Changes within each series are percentage points.",
        "Latest Version mirror snapshots preserve metadata vintage and source flag. The matching official WEO appendix supplies latest-actual-year cutoffs; later observations are estimates. Future source years excluded. New vintages require a matching reviewed appendix URL.",
    ]

    def __init__(self, settings):
        self.settings, self.interval = settings, settings.debt_interval

    async def collect(self, fetch, at):
        metadata = await fetch(METADATA)
        appendix = await fetch(self.settings.debt_appendix_url)
        body = await fetch(DATA)
        stamp = at()
        end = datetime.fromisoformat(stamp.replace("Z", "+00:00")).year - 1
        start = end - self.settings.macro_report_years
        return await asyncio.to_thread(
            parse, body, metadata, stamp, start, end, appendix, self.settings.debt_appendix_url
        )

    def coverage(self, points):
        return [
            f"{sid}: {len(items)} stored annual values; latest {items[-1].period.label}; mirror metadata vintage {items[-1].definition.vintage_date}."
            for sid in ("debt_india", "debt_us")
            if (
                items := sorted(
                    [p for p in points if p.series_id == sid and p.value is not None],
                    key=lambda p: p.period.end,
                )
            )
        ] or ["No comparable debt observations stored."]
