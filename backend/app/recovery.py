"""Private SQLite online snapshots and restore into a new, never-live destination."""

import os
import sqlite3
import tempfile
import time
from contextlib import closing
from pathlib import Path

from .db import MIGRATIONS, Database

TABLES = {"observations", "collection_runs", "users", "sessions", "refresh_tokens"}


def validate(connection):
    version = connection.execute("PRAGMA user_version").fetchone()[0]
    if not 1 <= version <= len(list(MIGRATIONS.glob("*.sql"))):
        raise ValueError("Snapshot has an unsupported schema version")
    tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if not TABLES <= tables:
        raise ValueError("Snapshot is not an application database")
    # Reuse the immutable migrations, rather than maintain a second schema definition.
    with closing(sqlite3.connect(":memory:")) as expected:
        for migration in sorted(MIGRATIONS.glob("*.sql")):
            if int(migration.name.split("_", 1)[0]) <= version:
                expected.executescript(migration.read_text())
        for (table,) in expected.execute("SELECT name FROM sqlite_master WHERE type='table'"):
            for pragma in ("table_info", "foreign_key_list"):
                statement = f"PRAGMA {pragma}({table})"  # identifiers come only from our migrations
                if connection.execute(statement).fetchall() != expected.execute(statement).fetchall():
                    raise ValueError("Snapshot application schema does not match its version")
    if connection.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
        raise ValueError("SQLite integrity check failed")
    if connection.execute("PRAGMA foreign_key_check").fetchone():
        raise ValueError("Snapshot has invalid foreign keys")
    return version


def copy_database(source: Path, destination: Path, *, restore=False):
    """Consistent backup API, exclusive publication, no overwrite; restored sessions are removed."""
    source = source.resolve(strict=True)
    destination = destination.absolute()
    if destination.exists() or destination.is_symlink():
        raise FileExistsError("Destination already exists; stop the service and choose a new path")
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if destination.parent.stat().st_mode & 0o077:
        raise PermissionError(
            "Destination directory must be private (mode 0700); choose a dedicated directory"
        )
    fd, temporary = tempfile.mkstemp(prefix=".sqlite-snapshot-", dir=destination.parent)
    os.close(fd)  # mkstemp is private before SQLite writes any bytes.
    staged = Path(temporary)
    try:
        with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True, timeout=5)) as original:
            with closing(sqlite3.connect(staged)) as target:
                deadline = time.monotonic() + 30

                def progress(status, remaining, total):
                    if time.monotonic() > deadline:
                        raise TimeoutError("Snapshot exceeded its 30-second budget; no output published")

                original.backup(target, pages=128, progress=progress, sleep=0.01)
                validate(target)
        if restore:
            Database(staged).migrate()
            with Database(staged).connect(write=True) as target:
                # Old backups must not resurrect subsequently revoked bearer/refresh sessions.
                target.execute("DELETE FROM sessions")
        with closing(sqlite3.connect(staged)) as target:
            version = validate(target)
            counts = {
                table: target.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                for table in sorted(TABLES)
            }  # fixed internal allowlist only
        with staged.open("rb") as handle:
            os.fsync(handle.fileno())
        os.link(staged, destination)  # atomic, fails if another process created the destination
        directory = os.open(destination.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        return {
            "schema_version": version,
            "counts": counts,
            "sessions_invalidated": restore,
            "destination": str(destination),
        }
    finally:
        staged.unlink(missing_ok=True)
