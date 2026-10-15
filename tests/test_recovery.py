import asyncio
import hashlib
import os
import sqlite3
import threading
import time
from dataclasses import replace

import httpx
import pytest
from app.db import MIGRATIONS, Database
from app.gdp import read_panel
from app.main import create_app
from app.recovery import copy_database
from fastapi.testclient import TestClient

from tests.conftest import fixture_response, login


def private_dir(path):
    path.mkdir(mode=0o700)
    return path


def test_live_snapshot_restore_preserves_data_and_invalidates_old_sessions(
    client, app, settings, clock, tmp_path
):
    tokens = login(client).json()
    with httpx.Client():  # no upstream networking: GDP uses the mock transport below

        async def collect():
            async with httpx.AsyncClient(transport=httpx.MockTransport(fixture_response)) as upstream:
                app.state.collector.client = upstream
                assert await app.state.collector.collect_once()

        asyncio.run(collect())
    with app.state.db.connect(write=True) as db:
        db.execute("UPDATE observations SET retained=1 WHERE series_id='gdp_india' AND period_key='2025'")
        db.execute(
            "INSERT INTO provider_cooldowns VALUES ('example_provider', ?, 'retry_after')", (clock() + 600,)
        )
    original = read_panel(app.state.db, settings, clock()).model_dump()
    directory = private_dir(tmp_path / "snapshots")
    snapshot = directory / "saved.sqlite3"
    backup = copy_database(settings.database, snapshot)
    before = hashlib.sha256(snapshot.read_bytes()).hexdigest()
    assert backup["counts"]["observations"] == 12
    assert snapshot.stat().st_mode & 0o777 == 0o600
    # The saved session is now obsolete; restore must never bring its JWT back to life.
    app.state.auth.logout(tokens["access_token"], None, tokens["csrf_token"])
    restored = directory / "restored.sqlite3"
    result = copy_database(snapshot, restored, restore=True)
    assert result["sessions_invalidated"] and result["counts"]["sessions"] == 0
    assert hashlib.sha256(snapshot.read_bytes()).hexdigest() == before
    restored_settings = replace(settings, database=restored)
    with TestClient(create_app(restored_settings, clock)) as recovered:
        assert recovered.get("/healthz").status_code == 200
        assert (
            recovered.get(
                "/api/v1/dashboard", headers={"Authorization": "Bearer " + tokens["access_token"]}
            ).status_code
            == 401
        )
        fresh = login(recovered).json()
        assert (
            recovered.get(
                "/api/v1/panels/gdp", headers={"Authorization": "Bearer " + fresh["access_token"]}
            ).status_code
            == 200
        )
        assert read_panel(recovered.app.state.db, restored_settings, clock()).model_dump() == original
        with recovered.app.state.db.connect() as db:
            assert db.execute("SELECT not_before FROM provider_cooldowns").fetchone()[0] == clock() + 600
    with app.state.db.connect() as db:
        assert db.execute("SELECT revoked_at FROM sessions").fetchone()[0] is not None


def test_existing_v1_database_migrates_without_losing_auth_or_gdp(tmp_path):
    directory = private_dir(tmp_path / "legacy")
    path = directory / "dashboard.sqlite3"
    with sqlite3.connect(path) as db:
        db.executescript((MIGRATIONS / "001_initial.sql").read_text())
        db.execute("PRAGMA user_version=1")
        db.execute("INSERT INTO users VALUES ('u', 'analyst', 'preserved-hash', 1)")
        db.execute("INSERT INTO sessions VALUES ('s','u',100,1000,NULL,NULL)")
        db.execute(
            "INSERT INTO observations VALUES ('gdp_india','2025','7.57','','','https://api.worldbank.org/v2','2026-10-07','2026-10-15T00:00:00Z',?,1)",
            ("a" * 64,),
        )
    legacy_restore = directory / "legacy-restored.sqlite3"
    copy_database(path, legacy_restore, restore=True)
    with Database(legacy_restore).connect() as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 3
        assert db.execute("SELECT count(*) FROM sessions").fetchone()[0] == 0
        assert db.execute("SELECT value FROM observations").fetchone()[0] == "7.57"
    database = Database(path)
    database.migrate()
    database.migrate()
    with database.connect() as db:
        row = db.execute("SELECT * FROM observations").fetchone()
        assert row["value"] == "7.57" and row["retained"] == 1 and row["group_id"] == "gdp"
        assert row["measurement_json"] is None and row["response_sha256"] == "a" * 64
        assert db.execute("SELECT password_hash FROM users").fetchone()[0] == "preserved-hash"
        assert db.execute("SELECT id FROM sessions").fetchone()[0] == "s"
        assert db.execute("PRAGMA user_version").fetchone()[0] == 3
    assert os.stat(path).st_mode & 0o777 == 0o600


def test_online_backup_never_copies_a_partially_written_transaction(tmp_path):
    directory = private_dir(tmp_path / "online")
    source = directory / "source.sqlite3"
    Database(source).migrate()
    with sqlite3.connect(source) as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("CREATE TABLE consistency_probe (a INTEGER, b INTEGER)")
        db.execute("INSERT INTO consistency_probe VALUES (0,0)")
    stop = threading.Event()
    writes = []

    def writer():
        with sqlite3.connect(source, timeout=5) as db:
            while not stop.is_set():
                db.execute("BEGIN IMMEDIATE")
                db.execute("UPDATE consistency_probe SET a=a+1")
                time.sleep(0.002)
                db.execute("UPDATE consistency_probe SET b=b+1")
                db.commit()
                writes.append(1)
                time.sleep(0.002)

    thread = threading.Thread(target=writer)
    thread.start()
    try:
        for i in range(3):
            snapshot = directory / f"snapshot-{i}.sqlite3"
            copy_database(source, snapshot)
            with sqlite3.connect(snapshot) as db:
                a, b = db.execute("SELECT a,b FROM consistency_probe").fetchone()
                assert a == b
    finally:
        stop.set()
        thread.join(timeout=10)
    assert not thread.is_alive() and writes


def test_restore_refuses_existing_corrupt_or_newer_destinations(tmp_path):
    directory = private_dir(tmp_path / "failure")
    source = directory / "source.sqlite3"
    Database(source).migrate()
    with pytest.raises(FileExistsError):
        copy_database(source, source, restore=True)
    corrupt = directory / "bad.sqlite3"
    corrupt.write_bytes(b"not a database")
    output = directory / "output.sqlite3"
    with pytest.raises(sqlite3.DatabaseError):
        copy_database(corrupt, output, restore=True)
    assert not output.exists()
    with sqlite3.connect(source) as db:
        db.execute("PRAGMA user_version=999")
    with pytest.raises(ValueError, match="unsupported"):
        copy_database(source, output, restore=True)
    assert not output.exists() and not list(directory.glob(".sqlite-snapshot-*"))


def test_backup_refuses_public_directory_without_changing_permissions(tmp_path):
    source = tmp_path / "source.sqlite3"
    Database(source).migrate()
    public = tmp_path / "public"
    public.mkdir(mode=0o755)
    with pytest.raises(PermissionError, match="private"):
        copy_database(source, public / "backup.sqlite3")
    assert public.stat().st_mode & 0o777 == 0o755


@pytest.mark.parametrize(
    "mutation", ["DROP TABLE provider_cooldowns", "ALTER TABLE collection_runs DROP COLUMN provider_id"]
)
def test_restore_rejects_incomplete_schema_even_if_sqlite_integrity_is_ok(tmp_path, mutation):
    directory = private_dir(tmp_path / "incomplete")
    source = directory / "source.sqlite3"
    Database(source).migrate()
    with sqlite3.connect(source) as db:
        db.execute(mutation)
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    destination = directory / "restored.sqlite3"
    with pytest.raises(ValueError, match="schema"):
        copy_database(source, destination, restore=True)
    assert not destination.exists()
