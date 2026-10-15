import asyncio
from datetime import datetime, timezone
from email.utils import format_datetime

import httpx
import pytest
from app.collection import Deferred, GroupState, ProviderHTTP, retry_after
from app.db import Database
from app.gdp import Collector, timestamp


def test_retry_after_seconds_http_date_and_invalid():
    now = 1792065600
    assert retry_after("120", now) == now + 120
    header = format_datetime(datetime.fromtimestamp(now + 90, timezone.utc), usegmt=True)
    assert retry_after(header, now) == now + 90
    assert retry_after(format_datetime(datetime.fromtimestamp(now - 60, timezone.utc)), now) == now
    for invalid in (None, "-1", "1.5", "next Tuesday", ""):
        assert retry_after(invalid, now) is None


def test_overall_budget_closes_slow_dripping_stream(settings, clock):
    database = Database(settings.database)
    database.migrate()
    state = GroupState(database, clock, "slow_source", "test")

    class Drip(httpx.AsyncByteStream):
        closed = False

        async def __aiter__(self):
            for _ in range(100):
                await asyncio.sleep(0.02)
                yield b"piece"

        async def aclose(self):
            self.closed = True

    stream = Drip()

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda r: httpx.Response(200, stream=stream))
        ) as client:
            with pytest.raises(TimeoutError):
                await ProviderHTTP(state, client, timeout=0.05, attempts=1).fetch("https://example.com/slow")

    asyncio.run(run())
    assert stream.closed


@pytest.mark.parametrize("header_kind", ["seconds", "date"])
def test_long_cooldown_persists_across_attempts_and_restart(settings, clock, header_kind):
    database = Database(settings.database)
    database.migrate()
    state = GroupState(database, clock)
    calls = []
    header = (
        "120"
        if header_kind == "seconds"
        else format_datetime(datetime.fromtimestamp(clock() + 120, timezone.utc), usegmt=True)
    )

    def handler(request):
        calls.append(clock())
        return httpx.Response(429, headers={"Retry-After": header})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with pytest.raises(Deferred):
                await ProviderHTTP(state, client, timeout=1, attempts=2).fetch("https://example.com/data")

    asyncio.run(run())
    assert len(calls) == 1
    assert state.cooldown() == clock() + 120
    assert state.begin(timestamp(clock()), 2020, 2025) is None
    restarted = GroupState(Database(settings.database), clock)
    assert not restarted.due()
    assert not Collector(settings, Database(settings.database), clock).due()
    clock.advance(121)
    assert restarted.due()


@pytest.mark.parametrize("header_kind", ["seconds", "date"])
def test_short_retry_waits_until_deadline_and_does_not_retry_early(settings, clock, header_kind):
    database = Database(settings.database)
    database.migrate()
    state = GroupState(database, clock)
    calls = []
    header = (
        "3"
        if header_kind == "seconds"
        else format_datetime(datetime.fromtimestamp(clock() + 3, timezone.utc), usegmt=True)
    )

    def handler(request):
        calls.append(clock())
        return (
            httpx.Response(503, headers={"Retry-After": header})
            if len(calls) == 1
            else httpx.Response(200, content=b"verified")
        )

    async def sleep(seconds):
        clock.advance(seconds)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await ProviderHTTP(
                state, client, timeout=10, attempts=2, sleep=sleep, monotonic=clock
            ).fetch("https://example.com/data")

    assert asyncio.run(run()) == b"verified"
    assert calls[1] - calls[0] == 3


def test_cooldowns_are_provider_wide_but_do_not_delay_other_providers(settings, clock):
    database = Database(settings.database)
    database.migrate()
    a = GroupState(database, clock, "cpi", "mospi")
    b = GroupState(database, clock, "cpi_metadata", "mospi")
    independent = GroupState(database, clock, "gst", "gstn")
    a.defer(clock() + 600)
    a.defer(clock() + 10)
    assert a.cooldown() == clock() + 600
    assert not b.due()
    assert independent.due()


def test_history_retention_never_prunes_other_groups_running_or_last_success(settings, clock):
    database = Database(settings.database)
    database.migrate()
    gdp = GroupState(database, clock, retention=3)
    first = gdp.begin(timestamp(clock()), 2020, 2025)
    gdp.finish(first, timestamp(clock()))
    running = gdp.begin(timestamp(clock()), 2020, 2025)
    market = GroupState(database, clock, "test_market", "test_provider", retention=3)
    success = market.begin(timestamp(clock()), 2020, 2025)
    market.finish(success, timestamp(clock()))
    for _ in range(12):
        run = market.begin(timestamp(clock()), 2020, 2025)
        market.finish(run, timestamp(clock()), "test_timeout")
    with database.connect() as db:
        assert db.execute("SELECT outcome FROM collection_runs WHERE id=?", (first,)).fetchone()[0] == "ok"
        assert (
            db.execute("SELECT outcome FROM collection_runs WHERE id=?", (running,)).fetchone()[0]
            == "running"
        )
        assert db.execute("SELECT outcome FROM collection_runs WHERE id=?", (success,)).fetchone()[0] == "ok"
        assert (
            db.execute("SELECT COUNT(*) FROM collection_runs WHERE group_id=?", ("test_market",)).fetchone()[
                0
            ]
            == 4
        )
