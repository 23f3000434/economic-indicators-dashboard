import asyncio
import sqlite3
import threading
from contextlib import contextmanager

import httpx
import pytest
from app.batches import MeasurementBatch, scope
from app.collection import GroupState, joined_thread
from app.gdp import timestamp
from app.indicators import read_indicator, store_batch
from app.main import create_app
from fastapi.testclient import TestClient

from tests.test_dashboard import provider_response


@pytest.mark.parametrize("group", ["gdp", "expenditure"])
def test_write_outage_recovers_exact_abandoned_run_in_same_process(settings, clock, monkeypatch, group):
    app = create_app(settings, clock, httpx.AsyncClient(transport=httpx.MockTransport(provider_response)))
    with TestClient(app):
        job = app.state.collector if group == "gdp" else app.state.jobs[group]
        assert asyncio.run(job.collect_once())
        active = GroupState(app.state.db, clock, "genuinely_active", "test")
        active_run = active.begin(timestamp(clock()), 2026, 2026)
        connect = app.state.db.connect
        outage = False

        @contextmanager
        def flaky(write=False):
            if write and outage:
                raise sqlite3.OperationalError("injected temporary write outage")
            with connect(write=write) as db:
                yield db

        monkeypatch.setattr(app.state.db, "connect", flaky)
        if group == "gdp":
            original = job.store

            def store(*args):
                nonlocal outage
                outage = True
                return original(*args)

            monkeypatch.setattr(job, "store", store)
        else:
            original = job.adapter.collect

            async def collect(*args):
                nonlocal outage
                rows = await original(*args)
                outage = True
                return rows

            monkeypatch.setattr(job.adapter, "collect", collect)
        assert not asyncio.run(job.collect_once())
        assert len(job.state.pending_failures) == 1
        abandoned = next(iter(job.state.pending_failures))
        with connect() as db:
            assert (
                db.execute("SELECT outcome FROM collection_runs WHERE id=?", (abandoned,)).fetchone()[0]
                == "running"
            )
        with pytest.raises(sqlite3.OperationalError):
            job.state.due()
        outage = False
        clock.advance(3601)
        assert job.state.due()  # repairs failure status before deciding schedule
        assert not job.state.pending_failures
        assert not active.due()  # no time-based expiry of genuine work
        with connect() as db:
            assert (
                db.execute("SELECT outcome FROM collection_runs WHERE id=?", (active_run,)).fetchone()[0]
                == "running"
            )
            record = db.execute(
                "SELECT outcome,error_kind FROM collection_runs WHERE id=?", (abandoned,)
            ).fetchone()
            assert tuple(record) == ("error", "storage_error")
        if group == "gdp":
            monkeypatch.setattr(job, "store", original)
        else:
            monkeypatch.setattr(job.adapter, "collect", original)
        assert asyncio.run(job.collect_once())


def test_successful_omission_scope_preserves_original_and_ignores_older_history(settings, clock):
    app = create_app(settings, clock, httpx.AsyncClient(transport=httpx.MockTransport(provider_response)))
    with TestClient(app):
        job = app.state.jobs["expenditure"]
        assert asyncio.run(job.collect_once())
        before = read_indicator(app.state.db, "expenditure", app.state.jobs, clock())
        original = {(p.series_id, p.period.key): p for s in before.series for p in s.points}
        current = [p for p in original.values() if p.period.key == "FY2026-27:08"]
        expected = scope([p.series_id for p in current], [current[0].period])
        clock.advance(10)
        run = job.state.begin(timestamp(clock()), 2026, 2026)
        # Entirely absent row, not an explicit null. Batch coverage remains known.
        store_batch(app.state.db, job.state, run, MeasurementBatch(current[1:], expected))
        after = read_indicator(app.state.db, "expenditure", app.state.jobs, clock())
        assert after.state == "stale"
        assert after.collection[0].last_error_kind == "provider_missing_retained"
        points = {(p.series_id, p.period.key): p for s in after.series for p in s.points}
        missing = current[0]
        assert points[missing.series_id, missing.period.key] == missing.model_copy(update={"retained": True})
        assert all(not p.retained for p in points.values() if p.period.key != missing.period.key)
        # Even all omissions are representable if the response's scope is explicit.
        run = job.state.begin(timestamp(clock()), 2026, 2026)
        store_batch(app.state.db, job.state, run, MeasurementBatch([], expected))
        assert read_indicator(app.state.db, "expenditure", app.state.jobs, clock()).state == "stale"
        assert asyncio.run(job.collect_once())
        assert read_indicator(app.state.db, "expenditure", app.state.jobs, clock()).state == "ready"


def test_cancelled_sql_worker_remains_active_until_it_finishes(settings, clock):
    from app.db import Database

    database = Database(settings.database)
    database.migrate()
    state = GroupState(database, clock)
    run = state.begin(timestamp(clock()), 2020, 2025)
    started, release = threading.Event(), threading.Event()

    def worker():
        started.set()
        release.wait(3)
        state.finish(run, timestamp(clock()))

    async def scenario():
        task = asyncio.create_task(joined_thread(worker))
        await asyncio.to_thread(started.wait, 1)
        task.cancel()
        await asyncio.sleep(0.02)
        assert not task.done()
        assert not state.due() and not state.pending_failures
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        # Late interruption cannot downgrade an already committed success.
        state.fail_safely(run, timestamp(clock()), "interrupted")
        with database.connect() as db:
            assert db.execute("SELECT outcome FROM collection_runs WHERE id=?", (run,)).fetchone()[0] == "ok"

    asyncio.run(scenario())
