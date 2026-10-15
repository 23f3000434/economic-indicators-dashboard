"""Validated WDI adapter and database-only panel projection. No fixtures or browser-triggered fetches."""

import asyncio
import hashlib
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal, localcontext

import httpx

from .config import Settings
from .db import Database
from .models import Panel

LOG = logging.getLogger(__name__)
INDICATOR = "NY.GDP.MKTP.KD.ZG"
BASE = "https://api.worldbank.org/v2"
COUNTRIES = {"gdp_india": ("IND", "India"), "gdp_world": ("WLD", "World")}


def timestamp(value: float | None = None) -> str:
    return (
        datetime.fromtimestamp(value, timezone.utc).isoformat().replace("+00:00", "Z")
        if value is not None
        else datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )


def source_url(country: str, start: int, end: int) -> str:
    return f"{BASE}/country/{country}/indicator/{INDICATOR}?format=json&date={start}:{end}&per_page=100&footnote=y"


def validate_series(body: bytes, country: str, start: int, end: int) -> tuple[str, dict]:
    payload = json.loads(body, parse_float=Decimal)
    if not isinstance(payload, list) or len(payload) != 2:
        raise ValueError("Invalid WDI envelope")
    meta, rows = payload
    if not isinstance(meta, dict) or not isinstance(rows, list):
        raise ValueError("Invalid WDI types")
    if (
        meta.get("page") != 1
        or meta.get("pages") != 1
        or meta.get("total") != len(rows)
        or str(meta.get("sourceid")) != "2"
    ):
        raise ValueError("Incomplete WDI pagination or wrong source")
    updated = meta.get("lastupdated")
    datetime.strptime(updated, "%Y-%m-%d")
    prepared = {}
    for row in rows:
        if (
            not isinstance(row, dict)
            or row.get("indicator", {}).get("id") != INDICATOR
            or row.get("countryiso3code") != country
        ):
            raise ValueError("Wrong series or geography")
        year = row.get("date")
        if (
            not isinstance(year, str)
            or len(year) != 4
            or not year.isdigit()
            or not start <= int(year) <= end
            or year in prepared
        ):
            raise ValueError("Invalid or duplicate period")
        value = row.get("value")
        if value is not None:
            if isinstance(value, bool) or not isinstance(value, (int, Decimal)):
                raise ValueError("Expected numeric observation")
            value = Decimal(value)
            if (
                not value.is_finite()
                or abs(value.as_tuple().exponent) > 50
                or len(value.as_tuple().digits) > 60
            ):
                raise ValueError("Non-finite observation")
            value = format(value, "f")
        status, footnote = row.get("obs_status", ""), row.get("footnote", "")
        if not isinstance(status, str) or not isinstance(footnote, str):
            raise ValueError("Invalid observation metadata")
        prepared[year] = (value, status, footnote)
    return updated, prepared


def validate_metadata(indicator: bytes, country: bytes):
    meta = json.loads(indicator)
    if (
        not isinstance(meta, list)
        or len(meta) != 2
        or len(meta[1]) != 1
        or meta[1][0]["id"] != INDICATOR
        or str(meta[1][0]["source"]["id"]) != "2"
    ):
        raise ValueError("GDP indicator metadata changed")
    country_meta = json.loads(country)
    for source in country_meta.get("source", []):
        if source.get("id") == "2":
            for concept in source.get("concept", []):
                for variable in concept.get("variable", []):
                    if variable.get("id") == "IND":
                        for item in variable.get("metatype", []):
                            if item.get("id") == "SpecialNotes" and "fiscal year-end: March 31" in item.get(
                                "value", ""
                            ):
                                return
    raise ValueError("India fiscal reporting metadata missing or changed")


class Collector:
    def __init__(
        self, settings: Settings, database: Database, clock, client: httpx.AsyncClient | None = None
    ):
        self.settings, self.db, self.clock, self.client = settings, database, clock, client
        self.task: asyncio.Task | None = None

    def recover(self):
        with self.db.connect(write=True) as db:
            db.execute(
                "UPDATE collection_runs SET outcome='error', error_kind='interrupted', completed_at=? WHERE outcome='running'",
                (timestamp(self.clock()),),
            )

    def due(self):
        with self.db.connect() as db:
            row = db.execute(
                "SELECT * FROM collection_runs WHERE group_id='gdp' ORDER BY id DESC LIMIT 1"
            ).fetchone()
        if not row:
            return True
        interval = (
            min(3600, self.settings.collection_interval)
            if row["outcome"] == "error"
            else self.settings.collection_interval
        )
        return (
            self.clock()
            >= datetime.fromisoformat(row["attempted_at"].replace("Z", "+00:00")).timestamp() + interval
        )

    def begin(self, start, end):
        with self.db.connect(write=True) as db:
            if db.execute(
                "SELECT 1 FROM collection_runs WHERE group_id='gdp' AND outcome='running'"
            ).fetchone():
                return None
            return db.execute(
                "INSERT INTO collection_runs(group_id, attempted_at, outcome, window_start, window_end) VALUES ('gdp', ?, 'running', ?, ?)",
                (timestamp(self.clock()), start, end),
            ).lastrowid

    async def fetch(self, client, url):
        for attempt in range(self.settings.upstream_attempts):
            try:
                async with client.stream("GET", url) as response:
                    response.raise_for_status()
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > 4 * 1024 * 1024:
                            raise ValueError("Upstream response exceeds limit")
                return bytes(body), timestamp(self.clock())
            except (httpx.TimeoutException, httpx.NetworkError):
                if attempt + 1 == self.settings.upstream_attempts:
                    raise
            except httpx.HTTPStatusError as exc:
                if (
                    exc.response.status_code not in {429, 502, 503, 504}
                    or attempt + 1 == self.settings.upstream_attempts
                ):
                    raise
            await asyncio.sleep(0.5 * (attempt + 1))

    async def collect_once(self) -> bool:
        start, end = self.settings.window(datetime.fromtimestamp(self.clock(), timezone.utc).year)
        run = await asyncio.to_thread(self.begin, start, end)
        if run is None:
            return False
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(self.settings.upstream_timeout, connect=5),
                follow_redirects=False,
                headers={"User-Agent": "EconomicIndicatorsDashboard/0.1", "Accept": "application/json"},
            ) as owned:
                client = self.client or owned
                urls = [
                    source_url("IND", start, end),
                    source_url("WLD", start, end),
                    f"{BASE}/indicator/{INDICATOR}?format=json",
                    f"{BASE}/sources/2/country/IND/metadata?format=json",
                ]
                responses = await asyncio.wait_for(
                    asyncio.gather(*(self.fetch(client, url) for url in urls), return_exceptions=True),
                    timeout=self.settings.upstream_timeout * self.settings.upstream_attempts + 10,
                )
                for result in responses:
                    if isinstance(result, BaseException):
                        raise result
            validate_metadata(responses[2][0], responses[3][0])
            prepared = []
            for i, (series_id, (country, _)) in enumerate(COUNTRIES.items()):
                body, retrieved = responses[i]
                updated, rows = validate_series(body, country, start, end)
                for year in range(start, end + 1):
                    value, status, footnote = rows.get(str(year), (None, "", ""))
                    prepared.append(
                        (
                            series_id,
                            str(year),
                            value,
                            status,
                            footnote,
                            urls[i],
                            updated,
                            retrieved,
                            hashlib.sha256(body).hexdigest(),
                        )
                    )
            await asyncio.to_thread(self.store, run, prepared)
            LOG.info("GDP collection %s succeeded", run)
            return True
        except asyncio.CancelledError:
            await asyncio.to_thread(self.fail, run, "interrupted")
            raise
        except Exception as exc:
            kind = (
                "timeout"
                if isinstance(exc, (httpx.TimeoutException, TimeoutError))
                else "http_rejection"
                if isinstance(exc, httpx.HTTPStatusError)
                else "network_error"
                if isinstance(exc, httpx.RequestError)
                else "invalid_payload"
                if isinstance(exc, (ValueError, TypeError, KeyError, AttributeError))
                else "storage_error"
            )
            await asyncio.to_thread(self.fail, run, kind)
            LOG.warning("GDP collection %s failed (%s)", run, kind)
            return False

    def store(self, run, rows):
        with self.db.connect(write=True) as db:
            for row in rows:
                if row[2] is None:
                    db.execute(
                        "UPDATE observations SET retained=1 WHERE series_id=? AND period_key=?", row[:2]
                    )
                else:
                    db.execute(
                        """INSERT INTO observations(series_id, period_key, value, provider_status, footnote, source_url, dataset_updated_on, retrieved_at, response_sha256) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(series_id, period_key) DO UPDATE SET value=excluded.value, provider_status=excluded.provider_status, footnote=excluded.footnote, source_url=excluded.source_url, dataset_updated_on=excluded.dataset_updated_on, retrieved_at=excluded.retrieved_at, response_sha256=excluded.response_sha256, retained=0""",
                        row,
                    )
            db.execute(
                "UPDATE collection_runs SET outcome='ok', completed_at=? WHERE id=?",
                (timestamp(self.clock()), run),
            )
            # Bounded diagnostic history; retain the most recent successful run too.
            db.execute(
                "DELETE FROM collection_runs WHERE id NOT IN (SELECT id FROM collection_runs ORDER BY id DESC LIMIT 200) AND id != (SELECT MAX(id) FROM collection_runs WHERE outcome='ok')"
            )

    def fail(self, run, kind):
        with self.db.connect(write=True) as db:
            db.execute(
                "UPDATE collection_runs SET outcome='error', error_kind=?, completed_at=? WHERE id=?",
                (kind, timestamp(self.clock()), run),
            )
            db.execute(
                "DELETE FROM collection_runs WHERE id NOT IN (SELECT id FROM collection_runs ORDER BY id DESC LIMIT 200) AND id != COALESCE((SELECT MAX(id) FROM collection_runs WHERE outcome='ok'), -1)"
            )

    async def supervise(self):
        while True:
            try:
                if await asyncio.to_thread(self.due):
                    await self.collect_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                LOG.exception("Collector supervisor will retry")
            await asyncio.sleep(min(30, self.settings.collection_interval))


def read_panel(database: Database, settings: Settings, now: float) -> Panel:
    # A read transaction guarantees a consistent run/observation snapshot.
    with database.connect() as db:
        db.execute("BEGIN")
        records = [dict(row) for row in db.execute("SELECT * FROM observations ORDER BY period_key")]
        latest = db.execute(
            "SELECT * FROM collection_runs WHERE group_id='gdp' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        finished = db.execute(
            "SELECT * FROM collection_runs WHERE group_id='gdp' AND outcome!='running' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        success = db.execute(
            "SELECT * FROM collection_runs WHERE group_id='gdp' AND outcome='ok' ORDER BY id DESC LIMIT 1"
        ).fetchone()
    _, end = settings.window(datetime.fromtimestamp(now, timezone.utc).year)
    years = [str(year) for year in range(end - settings.report_years + 1, end + 1)]
    failed = bool(finished and finished["outcome"] == "error")
    series, summaries = [], []
    for series_id, (country, label) in COUNTRIES.items():
        lookup = {r["period_key"]: r for r in records if r["series_id"] == series_id}
        points = []
        for year in years:
            row = lookup.get(year, {})
            fiscal = country == "IND"
            points.append(
                dict(
                    period_key=year,
                    period_label=f"FY {year}–{str(int(year) + 1)[-2:]}" if fiscal else f"CY {year}",
                    period_start=f"{year}-04-01" if fiscal else f"{year}-01-01",
                    period_end=f"{int(year) + 1}-03-31" if fiscal else f"{year}-12-31",
                    value=row.get("value"),
                    provider_status=row.get("provider_status", ""),
                    footnote=row.get("footnote", ""),
                    retrieved_at=row.get("retrieved_at"),
                    dataset_updated_on=row.get("dataset_updated_on"),
                    retained=bool(row.get("retained")),
                )
            )
        current, prior = points[-1], lookup.get(str(end - 1), {})
        with localcontext() as context:
            context.prec = 200
            delta = (
                format(Decimal(current["value"]) - Decimal(prior["value"]), "f")
                if current["value"] is not None and prior.get("value") is not None
                else None
            )
        most_recent = max(
            (lookup[y] for y in years if y in lookup), key=lambda r: r["retrieved_at"], default={}
        )
        series.append(
            dict(
                id=series_id,
                label=label,
                reporting_basis="fiscal_year_apr_mar" if country == "IND" else "calendar_year_aggregate",
                points=points,
                source=dict(
                    url=most_recent.get(
                        "source_url",
                        source_url(country, *settings.window(datetime.fromtimestamp(now, timezone.utc).year)),
                    ),
                    dataset_updated_on=most_recent.get("dataset_updated_on"),
                    retrieved_at=most_recent.get("retrieved_at"),
                ),
            )
        )
        summaries.append(
            dict(
                series_id=series_id,
                current_period_key=str(end),
                comparison_period_key=str(end - 1),
                change=dict(value=delta),
            )
        )
    has_data = any(p["value"] is not None for s in series for p in s["points"])
    retained = any(p["retained"] for s in series for p in s["points"])
    overdue_collection = bool(
        success
        and now - datetime.fromisoformat(success["completed_at"].replace("Z", "+00:00")).timestamp()
        > settings.collection_interval * 2
    )
    state = (
        ("stale" if failed or retained or overdue_collection else "ready")
        if has_data
        else ("unavailable" if failed else "empty")
    )
    return Panel.model_validate(
        dict(
            state=state,
            collection=dict(
                last_attempt_at=latest["attempted_at"] if latest else None,
                last_success_at=success["completed_at"] if success else None,
                last_error_kind=finished["error_kind"]
                if failed
                else "collection_overdue"
                if overdue_collection
                else "provider_missing_retained"
                if retained
                else None,
                in_progress=bool(latest and latest["outcome"] == "running"),
            ),
            series=series,
            summaries=summaries,
            notes=[
                "India: April–March fiscal years; World: published calendar-year aggregate. These windows differ.",
                "Real GDP growth, annual %. Changes compare growth rates in percentage points (pp).",
                "Release freshness unknown: WDI dataset update and collection times are not observation publication dates.",
                "A retained point keeps its original provenance when a successful response omits its value.",
            ],
        )
    )
