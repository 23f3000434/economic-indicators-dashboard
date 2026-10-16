"""Validated exchange snapshots and network-free ticker projection. No simulated ticks."""

import hashlib
import json
import re
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal, localcontext
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, model_validator

from .collection import NotConfigured
from .gdp import timestamp
from .indicators import GroupCollection, collection_status
from .measurements import number
from .models import Model

NSE_URL = "https://www.nseindia.com/api/allIndices"
BSE_URL = "https://api.upstox.com/v3/market-quote/quotes?instrument_key=BSE_INDEX%7CSENSEX"
STATUS_URL = "https://api.upstox.com/v2/market/status/"
TIMINGS_URL = "https://api.upstox.com/v2/market/timings/"
INSTRUMENTS = {
    "sensex": ("SENSEX", "BSE", "upstox", "market_bse"),
    "nifty_bank": ("NIFTY BANK", "NSE", "nse", "market_nse"),
    "nifty_it": ("NIFTY IT", "NSE", "nse", "market_nse"),
}
STATUSES = {
    "NORMAL_OPEN": "open",
    "NORMAL_CLOSE": "closed",
    "CLOSING_START": "closing",
    "CLOSING_END": "closed",
    "PRE_OPEN_START": "preopen",
    "PRE_OPEN_END": "preopen",
}
IST = timezone(timedelta(hours=5, minutes=30))


def instant(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Market times must include a timezone")
    return parsed.timestamp()


def epoch_ms(value):
    if not re.fullmatch(r"\d{13}", str(value)):
        raise ValueError("Invalid exchange milliseconds")
    return (
        (datetime(1970, 1, 1, tzinfo=UTC) + timedelta(milliseconds=int(value)))
        .isoformat()
        .replace("+00:00", "Z")
    )


def decimal(value):
    if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
        raise ValueError("Market numeric field must be a published decimal")
    return number(format(value, "f") if isinstance(value, Decimal) else str(value))


class Quote(Model):
    instrument_id: Literal["sensex", "nifty_bank", "nifty_it"]
    provider_id: Literal["nse", "upstox"]
    value: str
    previous_close: str
    previous_close_basis: Literal["published_previous_close", "last_price_minus_net_change"]
    exchange_timestamp: str
    exchange_timestamp_precision: Literal["minute", "millisecond"]
    provider_timestamp: str | None = None
    retrieved_at: str
    source_url: str
    response_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def valid(self):
        for field in ("value", "previous_close"):
            value = number(getattr(self, field))
            if not Decimal(0) < Decimal(value) < Decimal(10_000_000):
                raise ValueError("Invalid positive index value/previous close")
        if self.provider_id != INSTRUMENTS[self.instrument_id][2]:
            raise ValueError("Index/provider identity mismatch")
        if self.source_url != (NSE_URL if self.provider_id == "nse" else BSE_URL):
            raise ValueError("Unexpected quote URL")
        received, exchange = instant(self.retrieved_at), instant(self.exchange_timestamp)
        if exchange > received + 60 or (
            self.provider_timestamp
            and (
                instant(self.provider_timestamp) > received + 60
                or exchange > instant(self.provider_timestamp) + 60
            )
        ):
            raise ValueError("Future or inconsistent exchange/provider time")
        return self


class ExchangeSession(Model):
    exchange: Literal["NSE", "BSE"]
    status: Literal[
        "NORMAL_OPEN", "NORMAL_CLOSE", "CLOSING_START", "CLOSING_END", "PRE_OPEN_START", "PRE_OPEN_END"
    ]
    transition_at: str
    checked_at: str
    source_url: str
    response_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    regular_open_at: str
    regular_close_at: str
    timings_source_url: str
    timings_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def valid(self):
        if (
            self.source_url != STATUS_URL + self.exchange
            or instant(self.transition_at) > instant(self.checked_at) + 60
        ):
            raise ValueError("Invalid exchange status provenance/time")
        session_day = datetime.fromtimestamp(instant(self.transition_at), IST).date().isoformat()
        if (
            self.timings_source_url != TIMINGS_URL + session_day
            or not instant(self.regular_open_at) < instant(self.regular_close_at)
            or datetime.fromtimestamp(instant(self.regular_close_at), IST).date().isoformat() != session_day
        ):
            raise ValueError("Exchange session timing identity changed")
        return self


class QuoteBatch(list):
    def __init__(self, rows, expected):
        super().__init__(rows)
        self.expected = frozenset(expected)
        if not self.expected <= INSTRUMENTS.keys() or not self.expected:
            raise ValueError("Unknown quote scope")


class SessionBatch(list):
    expected = frozenset({"NSE", "BSE"})


def parse_nse(body, at):
    raw = json.loads(body, parse_float=Decimal)
    stamp = (
        datetime.strptime(raw["timestamp"], "%d-%b-%Y %H:%M")
        .replace(tzinfo=IST)
        .astimezone(UTC)
        .isoformat()
        .replace("+00:00", "Z")
    )
    rows = []
    for identity in ("nifty_bank", "nifty_it"):
        label = INSTRUMENTS[identity][0]
        found = [r for r in raw["data"] if r.get("index") == label]
        if len(found) > 1:
            raise ValueError("Duplicate NSE index")
        if not found or found[0].get("last") is None or found[0].get("previousClose") is None:
            continue  # Expected but missing: SQL retains the previous observation with its provenance.
        row = found[0]
        value, prior = decimal(row["last"]), decimal(row["previousClose"])
        with localcontext() as ctx:
            ctx.prec = 40
            if abs(Decimal(value) - Decimal(prior) - Decimal(decimal(row["variation"]))) > Decimal("0.02"):
                raise ValueError("NSE previous-close/change mismatch")
            if Decimal(prior) == 0 or abs(
                (Decimal(value) / Decimal(prior) - 1) * 100 - Decimal(decimal(row["percentChange"]))
            ) > Decimal("0.011"):
                raise ValueError("NSE percentage comparison mismatch")
        rows.append(
            Quote(
                instrument_id=identity,
                provider_id="nse",
                value=value,
                previous_close=prior,
                previous_close_basis="published_previous_close",
                exchange_timestamp=stamp,
                exchange_timestamp_precision="minute",
                retrieved_at=at,
                source_url=NSE_URL,
                response_sha256=hashlib.sha256(body).hexdigest(),
            )
        )
    return QuoteBatch(rows, {"nifty_bank", "nifty_it"})


def parse_bse(body, at):
    raw = json.loads(body, parse_float=Decimal)
    if raw["status"] != "success" or not isinstance(raw["data"], dict):
        raise ValueError("Unsuccessful quote envelope")
    item = raw["data"].get("BSE_INDEX:SENSEX")
    if item is None or item.get("last_price") is None:
        return QuoteBatch([], {"sensex"})
    if item["instrument_token"] != "BSE_INDEX|SENSEX":
        raise ValueError("Incorrect SENSEX instrument")
    value, net = Decimal(decimal(item["last_price"])), Decimal(decimal(item["net_change"]))
    # V3 index responses currently publish prev_close_price=null; OHLC close is the
    # current session's close. The documented net_change is versus previous close.
    prior = value - net
    published = item.get("prev_close_price")
    if published is not None and abs(Decimal(decimal(published)) - prior) > Decimal("0.02"):
        raise ValueError("SENSEX previous-close/change mismatch")
    return QuoteBatch(
        [
            Quote(
                instrument_id="sensex",
                provider_id="upstox",
                value=format(value, "f"),
                previous_close=decimal(published) if published is not None else format(prior, "f"),
                previous_close_basis="published_previous_close"
                if published is not None
                else "last_price_minus_net_change",
                exchange_timestamp=epoch_ms(item["last_trade_time"]),
                exchange_timestamp_precision="millisecond",
                provider_timestamp=datetime.fromtimestamp(instant(item["timestamp"]), UTC).isoformat(),
                retrieved_at=at,
                source_url=BSE_URL,
                response_sha256=hashlib.sha256(body).hexdigest(),
            )
        ],
        {"sensex"},
    )


def parse_status(body, exchange, at, timings, timings_url):
    raw = json.loads(body)
    item = raw["data"]
    if raw["status"] != "success" or item["exchange"] != exchange or item["status"] not in STATUSES:
        raise ValueError("Unknown exchange status or identity")
    schedule = json.loads(timings)
    found = [r for r in schedule["data"] if r["exchange"] == exchange]
    if schedule["status"] != "success" or len(found) != 1:
        raise ValueError("Exchange session schedule missing/ambiguous")
    return ExchangeSession(
        exchange=exchange,
        status=item["status"],
        transition_at=epoch_ms(item["last_updated"]),
        checked_at=at,
        regular_open_at=epoch_ms(found[0]["start_time"]),
        regular_close_at=epoch_ms(found[0]["end_time"]),
        timings_source_url=timings_url,
        timings_sha256=hashlib.sha256(timings).hexdigest(),
        source_url=STATUS_URL + exchange,
        response_sha256=hashlib.sha256(body).hexdigest(),
    )


def store_quotes(database, state, run, batch):
    if len({q.instrument_id for q in batch}) != len(batch) or any(
        q.instrument_id not in batch.expected for q in batch
    ):
        raise ValueError("Duplicate/out-of-scope quotes")
    if any(INSTRUMENTS[key][2:] != (state.provider, state.group) for key in batch.expected):
        raise ValueError("Quote group/provider scope mismatch")
    rows = [Quote.model_validate(q.model_dump()) for q in batch]
    with database.connect(write=True) as db:
        for q in rows:
            old = db.execute(
                "SELECT payload_json FROM market_quotes WHERE instrument_id=?", (q.instrument_id,)
            ).fetchone()
            if old and instant(q.exchange_timestamp) < instant(json.loads(old[0])["exchange_timestamp"]):
                raise ValueError("Regressing exchange quote timestamp")
        db.executemany(
            "UPDATE market_quotes SET retained=1 WHERE instrument_id=?", [(k,) for k in batch.expected]
        )
        db.executemany(
            "INSERT INTO market_quotes VALUES (?,?,?,0) ON CONFLICT(instrument_id) DO UPDATE SET payload_json=excluded.payload_json, retained=0",
            [(q.instrument_id, state.group, q.model_dump_json()) for q in rows],
        )
        state.finish_in(db, run, timestamp(state.clock()))


def store_sessions(database, state, run, batch):
    rows = [ExchangeSession.model_validate(s.model_dump()) for s in batch]
    if (
        {s.exchange for s in rows} != batch.expected
        or len(rows) != len(batch.expected)
        or state.group != "market_status"
    ):
        raise ValueError("Incomplete/incorrect exchange-status scope")
    with database.connect(write=True) as db:
        for s in rows:
            db.execute(
                "INSERT INTO market_sessions VALUES (?,?,0) ON CONFLICT(exchange) DO UPDATE SET payload_json=excluded.payload_json,retained=0",
                (s.exchange, s.model_dump_json()),
            )
        state.finish_in(db, run, timestamp(state.clock()))


class MarketNSE:
    group, provider, panel = "market_nse", "nse", "market"
    native_tls = True
    batch_type, persist = QuoteBatch, staticmethod(store_quotes)
    notes = []
    max_bytes = 2 * 1024 * 1024

    def __init__(self, settings):
        self.settings, self.interval = settings, settings.market_interval
        self.timeout, self.budget = settings.market_timeout, settings.market_timeout * 5

    async def collect(self, fetch, at):
        body = await fetch(NSE_URL)
        return parse_nse(body, at())


class MarketBSE(MarketNSE):
    group, provider = "market_bse", "upstox"

    def request_headers(self, url):
        # Never attach a secret to a redirect, source URL, or another provider.
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.hostname != "api.upstox.com" or parsed.username or parsed.port:
            raise ValueError("Credential destination rejected")
        if not self.settings.upstox_analytics_token:
            raise NotConfigured("Read-only market credential is not configured")
        return {"Authorization": "Bearer " + self.settings.upstox_analytics_token}

    async def collect(self, fetch, at):
        body = await fetch(BSE_URL)
        return parse_bse(body, at())


class MarketStatus(MarketBSE):
    group = "market_status"
    batch_type, persist = SessionBatch, staticmethod(store_sessions)

    async def collect(self, fetch, at):
        rows = SessionBatch()
        timings = {}
        for exchange in ("NSE", "BSE"):
            body = await fetch(STATUS_URL + exchange)
            raw = json.loads(body)
            day = (
                datetime.fromtimestamp(instant(epoch_ms(raw["data"]["last_updated"])), IST).date().isoformat()
            )
            url = TIMINGS_URL + day
            if day not in timings:
                timings[day] = await fetch(url)
            rows.append(parse_status(body, exchange, at(), timings[day], url))
        return rows


class TickerItem(Model):
    id: Literal["sensex", "nifty_bank", "nifty_it"]
    label: str
    exchange: Literal["NSE", "BSE"]
    provider_id: Literal["nse", "upstox"]
    availability: Literal["implemented"] = "implemented"
    state: Literal["live", "snapshot", "delayed", "closed", "stale", "unavailable"]
    unit: Literal["index_points"] = "index_points"
    value: str | None = None
    previous_close: str | None = None
    previous_close_basis: str | None = None
    change_points: str | None = None
    change_percent: str | None = None
    exchange_timestamp: str | None = None
    exchange_timestamp_precision: str | None = None
    provider_timestamp: str | None = None
    retrieved_at: str | None = None
    source_url: str | None = None
    response_sha256: str | None = None
    market_state: Literal["open", "closed", "closing", "preopen", "unknown"] = "unknown"
    market_status_at: str | None = None
    market_status_checked_at: str | None = None
    market_status_source_url: str | None = None
    market_status_sha256: str | None = None
    market_session_close_at: str | None = None
    market_timings_source_url: str | None = None
    market_timings_sha256: str | None = None
    retained: bool = False
    error_kind: str | None = None


class TickerSnapshot(Model):
    schema_version: Literal["1"] = "1"
    generated_at: str
    ticker: list[TickerItem]
    collection_groups: list[GroupCollection]


def read_markets(database, jobs, now):
    with database.connect() as db:
        db.execute("BEGIN")
        quotes = {
            r["instrument_id"]: (Quote.model_validate_json(r["payload_json"]), bool(r["retained"]))
            for r in db.execute("SELECT * FROM market_quotes")
        }
        sessions = {
            r["exchange"]: ExchangeSession.model_validate_json(r["payload_json"])
            for r in db.execute("SELECT * FROM market_sessions")
        }
        groups = {
            g: collection_status(db, g, jobs[g].provider, jobs[g].interval, now)
            for g in ("market_nse", "market_bse", "market_status")
        }
    result = []
    for identity, (label, exchange, provider, group) in INSTRUMENTS.items():
        q, retained = quotes.get(identity, (None, False))
        status = sessions.get(exchange)
        error = groups[group].last_error_kind
        session_error = groups["market_status"].last_error_kind
        state = "unavailable"
        market_state = STATUSES[status.status] if status else "unknown"
        if q:
            if error or retained:
                state, error = "stale", error or "provider_missing_retained"
            elif (
                not status
                or session_error
                or now - instant(status.checked_at) > jobs["market_status"].interval * 2
            ):
                state, error = "stale", session_error or "market_status_unverified"
            elif market_state == "closed":
                # Phase transitions are not quote times. The separate session
                # schedule accounts for regular and special trading days.
                state = (
                    "closed"
                    if instant(q.exchange_timestamp) >= instant(status.regular_close_at) - 60
                    else "stale"
                )
                if state == "stale":
                    error = "quote_precedes_latest_close"
            else:
                age = now - instant(q.exchange_timestamp)
                state = (
                    "stale"
                    if age > 600
                    else "delayed"
                    if age > 90
                    else "live"
                    if provider == "upstox" and market_state == "open"
                    else "snapshot"
                )
                if state in {"stale", "delayed"}:
                    error = "quote_not_current"
                if market_state == "open" and not instant(status.regular_open_at) <= now <= instant(
                    status.regular_close_at
                ):
                    state, error = "stale", "market_status_outside_schedule"
        item = TickerItem(
            id=identity,
            label=label,
            exchange=exchange,
            provider_id=provider,
            state=state,
            market_state=market_state,
            retained=bool(q and (retained or state == "stale")),
            error_kind=error,
        )
        if q:
            for field in (
                "value",
                "previous_close",
                "previous_close_basis",
                "exchange_timestamp",
                "exchange_timestamp_precision",
                "provider_timestamp",
                "retrieved_at",
                "source_url",
                "response_sha256",
            ):
                setattr(item, field, getattr(q, field))
            with localcontext() as ctx:
                ctx.prec = 40
                item.change_points = format(Decimal(q.value) - Decimal(q.previous_close), "f")
                item.change_percent = format((Decimal(q.value) / Decimal(q.previous_close) - 1) * 100, "f")
        if status:
            item.market_session_close_at = status.regular_close_at
            item.market_timings_source_url = status.timings_source_url
            item.market_timings_sha256 = status.timings_sha256
            item.market_status_at, item.market_status_checked_at = status.transition_at, status.checked_at
            item.market_status_source_url, item.market_status_sha256 = (
                status.source_url,
                status.response_sha256,
            )
        result.append(item)
    return result, list(groups.values())
