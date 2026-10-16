"""Actual PostgreSQL checks, isolated schemas, never a production fixture mode."""

import asyncio
import os
from dataclasses import replace

import httpx
import pytest
from app.collection import GroupState
from app.db import CollectionLeaseLost, Database
from app.gdp import timestamp
from app.main import create_app
from fastapi.testclient import TestClient

from tests.conftest import fixture_response

pytestmark = pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="Actual PostgreSQL DSN required")


def test_migrations_are_idempotent_and_validate_history(settings, clock):
    database = Database(settings.database_url)
    database.migrate()
    with database.connect(write=True) as db:
        db.execute("INSERT INTO users VALUES (?, ?, ?, 0)", ("id", "name'; DROP TABLE users; --", "hash"))
    database.migrate()
    reopened = Database(settings.database_url)
    with reopened.connect() as db:
        assert db.execute("SELECT username FROM users").fetchone()[0] == "name'; DROP TABLE users; --"
        original = db.execute("SELECT checksum FROM schema_migrations").fetchone()[0]
    with reopened.connect(write=True) as db:
        db.execute("UPDATE schema_migrations SET checksum=?", ("invalid",))
    with pytest.raises(RuntimeError, match="checksum"):
        reopened.migrate()
    with reopened.connect(write=True) as db:
        db.execute("UPDATE schema_migrations SET checksum=?", (original,))
    reopened.migrate()


def test_standby_does_not_recover_active_work_and_old_commits_are_fenced(settings, clock):
    database = Database(settings.database_url)
    database.migrate()
    state = GroupState(database, clock)
    with database.collector_lease() as owner:
        assert owner
        run = state.begin(timestamp(clock()), 2020, 2025)
        with TestClient(
            create_app(replace(settings, collector_enabled=True, macro_groups=()), clock)
        ) as standby:
            assert standby.get("/healthz").json()["collector"] == "standby"
            with database.connect() as db:
                assert (
                    db.execute("SELECT outcome FROM collection_runs WHERE id=?", (run,)).fetchone()[0]
                    == "running"
                )
    successor = Database(settings.database_url)
    with successor.collector_lease() as owner:
        assert owner
        GroupState(successor, clock).recover(timestamp(clock()))
        with pytest.raises(CollectionLeaseLost):
            with database.connect(write=True) as db:
                db.execute("INSERT INTO provider_cooldowns VALUES (?, ?, ?)", ("must_rollback", 1, "test"))
                state.finish_in(db, run, timestamp(clock()))
        with successor.connect() as db:
            assert (
                db.execute(
                    "SELECT COUNT(*) FROM provider_cooldowns WHERE provider_id=?", ("must_rollback",)
                ).fetchone()[0]
                == 0
            )


def test_bootstrap_cannot_replace_or_reactivate_an_existing_user(settings, clock):
    app = create_app(settings, clock)
    with TestClient(app):
        auth = app.state.auth
        auth.bootstrap_user("evaluation", auth.hasher.hash("First test password 123!"))
        with app.state.db.connect(write=True) as db:
            original = db.execute(
                "SELECT password_hash FROM users WHERE username=?", ("evaluation",)
            ).fetchone()[0]
            db.execute("UPDATE users SET active=0 WHERE username=?", ("evaluation",))
        auth.bootstrap_user("evaluation", auth.hasher.hash("Second test password 123!"))
        with app.state.db.connect() as db:
            row = db.execute(
                "SELECT password_hash, active FROM users WHERE username=?", ("evaluation",)
            ).fetchone()
            assert row[0] == original and row[1] == 0


def test_postgres_cooldown_precision_and_group_history_survive_restart(settings, clock):
    database = Database(settings.database_url)
    database.migrate()
    macro = GroupState(database, clock)
    market = GroupState(database, clock, "market_nse", "nse", interval=30, retention=2)
    run = macro.begin(timestamp(clock()), 2020, 2026)
    macro.finish(run, timestamp(clock()))
    for _ in range(6):
        run = market.begin(timestamp(clock()), 2020, 2026)
        market.finish(run, timestamp(clock()), "timeout")
    deadline = clock() + 3600.125
    market.defer(deadline)
    market.defer(clock() + 1)
    restarted = GroupState(Database(settings.database_url), clock, "market_nse", "nse", interval=30)
    assert restarted.cooldown() == deadline and not restarted.due()
    with database.connect() as db:
        assert (
            db.execute(
                "SELECT COUNT(*) FROM collection_runs WHERE group_id='gdp' AND outcome='ok'"
            ).fetchone()[0]
            == 1
        )
        assert (
            db.execute("SELECT COUNT(*) FROM collection_runs WHERE group_id='market_nse'").fetchone()[0] == 2
        )


def test_actual_read_only_outage_recovers_finished_run_without_restart(settings, clock, monkeypatch):
    app = create_app(settings, clock, httpx.AsyncClient(transport=httpx.MockTransport(fixture_response)))
    with TestClient(app):
        job, database = app.state.collector, app.state.db
        assert asyncio.run(job.collect_once())
        active = GroupState(database, clock, "genuinely_active", "test")
        active_run = active.begin(timestamp(clock()), 2020, 2026)
        connect, store, outage = database.postgres_connection, job.store, False

        def connection():
            native = connect()
            if outage:
                native.execute("SET default_transaction_read_only=on")
            return native

        def fail_storage(*args):
            nonlocal outage
            outage = True
            return store(*args)

        monkeypatch.setattr(database, "postgres_connection", connection)
        monkeypatch.setattr(job, "store", fail_storage)
        assert not asyncio.run(job.collect_once())
        assert len(job.state.pending_failures) == 1
        abandoned = next(iter(job.state.pending_failures))
        with database.connect() as db:
            assert (
                db.execute("SELECT outcome FROM collection_runs WHERE id=?", (abandoned,)).fetchone()[0]
                == "running"
            )
            assert db.execute("SELECT COUNT(*) FROM observations").fetchone()[0] > 0
        outage = False
        clock.advance(3601)
        assert job.state.due() and not job.state.pending_failures
        with database.connect() as db:
            assert tuple(
                db.execute(
                    "SELECT outcome,error_kind FROM collection_runs WHERE id=?", (abandoned,)
                ).fetchone()
            ) == ("error", "storage_error")
            assert (
                db.execute("SELECT outcome FROM collection_runs WHERE id=?", (active_run,)).fetchone()[0]
                == "running"
            )
        monkeypatch.setattr(job, "store", store)
        assert asyncio.run(job.collect_once())
