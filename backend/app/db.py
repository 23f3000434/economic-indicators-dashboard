import hashlib
import os
import re
import secrets
import sqlite3
from contextlib import contextmanager
from pathlib import Path

import psycopg
from psycopg.conninfo import conninfo_to_dict

MIGRATIONS = Path(__file__).resolve().parents[1] / "migrations"
POSTGRES_MIGRATIONS = MIGRATIONS / "postgres"
DB_ERRORS = (sqlite3.Error, psycopg.Error)
WRITE_LOCK = 60721181
MIGRATION_LOCK = 60721182
COLLECTOR_LOCK = 60721183


class CollectionLeaseLost(RuntimeError):
    pass


class Record:
    """The small key/index row interface used by our parameterized SQL projections."""

    def __init__(self, columns, values):
        self.columns, self.values = columns, values

    def keys(self):
        return self.columns

    def __getitem__(self, key):
        return self.values[key if isinstance(key, int) else self.columns.index(key)]

    def __iter__(self):
        return iter(self.values)


class PostgresCursor:
    def __init__(self, cursor):
        self.cursor = cursor
        self.columns = [c.name for c in cursor.description] if cursor.description else []

    def fetchone(self):
        row = self.cursor.fetchone()
        return Record(self.columns, row) if row is not None else None

    def fetchall(self):
        return [Record(self.columns, row) for row in self.cursor.fetchall()]

    def __iter__(self):
        return (Record(self.columns, row) for row in self.cursor)

    @property
    def rowcount(self):
        return self.cursor.rowcount


class PostgresConnection:
    def __init__(self, connection):
        self.connection = connection

    def execute(self, statement, parameters=None):
        if statement.strip().upper() == "BEGIN":
            statement = "BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY"
        if parameters is not None:
            # Values remain bound by psycopg. Never interpolate them into SQL. Only
            # our fixed query placeholders outside quoted literals are translated.
            parts = re.split(r"('(?:''|[^'])*'|\"(?:\"\"|[^\"])*\")", statement)
            statement = "".join(
                part.replace("%", "%%").replace("?", "%s") if i % 2 == 0 else part.replace("%", "%%")
                for i, part in enumerate(parts)
            )
        return PostgresCursor(self.connection.execute(statement, parameters))

    def executemany(self, statement, rows):
        # Batches stay in the caller's serialized transaction, using the same
        # placeholder translation and driver binding as individual statements.
        for parameters in rows:
            self.execute(statement, parameters)

    def commit(self):
        # Auth explicitly commits a reuse revocation before raising AuthError.
        self.connection.commit()


class Database:
    def __init__(self, target: Path | str, *, require_tls=False):
        self.is_postgres = isinstance(target, str) and target.startswith(("postgres://", "postgresql://"))
        self.path = None if self.is_postgres else Path(target)
        self._dsn = target if self.is_postgres else None
        self.require_tls = require_tls
        self.collector_token = None

    def postgres_connection(self):
        options = conninfo_to_dict(self._dsn).get("options", "")
        return psycopg.connect(
            self._dsn,
            autocommit=True,
            connect_timeout=5,
            options=options + " -c statement_timeout=5000 -c lock_timeout=5000",
            **({"sslmode": "require"} if self.require_tls else {}),
        )

    @contextmanager
    def collector_lease(self):
        if not self.is_postgres:
            yield True
            return
        connection = self.postgres_connection()
        try:
            if not connection.execute("SELECT pg_try_advisory_lock(%s)", (COLLECTOR_LOCK,)).fetchone()[0]:
                yield None
                return
            token = secrets.token_hex(16)
            with self.connect(write=True) as db:
                db.execute(
                    "INSERT INTO collection_owner VALUES (1, ?) ON CONFLICT(id) DO UPDATE SET token=excluded.token",
                    (token,),
                )
            self.collector_token = token
            yield connection
        finally:
            self.collector_token = None
            connection.close()

    @contextmanager
    def connect(self, write=False):
        if self.is_postgres:
            db = self.postgres_connection()
            try:
                if write:
                    db.execute("BEGIN")
                    db.execute("SELECT pg_advisory_xact_lock(%s)", (WRITE_LOCK,))
                yield PostgresConnection(db)
                if write:
                    db.commit()
            except BaseException:
                if write:
                    db.rollback()
                raise
            finally:
                db.close()
            return
        db = sqlite3.connect(
            self.path.resolve().as_uri() + "?mode=rw", uri=True, timeout=5, isolation_level=None
        )
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            if write:
                db.execute("BEGIN IMMEDIATE")
            yield db
            if write:
                db.commit()
        except BaseException:
            if write:
                db.rollback()
            raise
        finally:
            db.close()

    def migrate(self):
        if self.is_postgres:
            return self.migrate_postgres()
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(self.path.parent, 0o700)
        # Precreate with private permissions before SQLite can write anything.
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o600)
        os.close(fd)
        os.chmod(self.path, 0o600)
        with self.connect() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            for migration in sorted(MIGRATIONS.glob("*.sql")):
                number = int(migration.name.split("_", 1)[0])
                if number > version:
                    db.executescript(
                        f"BEGIN IMMEDIATE;\n{migration.read_text()}\nPRAGMA user_version={number};\nCOMMIT;"
                    )
            if db.execute("PRAGMA user_version").fetchone()[0] != len(list(MIGRATIONS.glob("*.sql"))):
                raise RuntimeError("Unsupported database schema version")

    def migrate_postgres(self):
        with self.postgres_connection() as connection:
            with connection.transaction():
                connection.execute("SELECT pg_advisory_xact_lock(%s)", (MIGRATION_LOCK,))
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, checksum TEXT NOT NULL, applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP)"
                )
                applied = dict(connection.execute("SELECT version, checksum FROM schema_migrations"))
                files = sorted(POSTGRES_MIGRATIONS.glob("*.sql"))
                expected = {int(p.name.split("_", 1)[0]) for p in files}
                if set(applied) - expected:
                    raise RuntimeError("Unsupported PostgreSQL schema version")
                for migration in files:
                    number = int(migration.name.split("_", 1)[0])
                    body = migration.read_bytes()
                    checksum = hashlib.sha256(body).hexdigest()
                    if number in applied:
                        if applied[number] != checksum:
                            raise RuntimeError("Applied PostgreSQL migration checksum mismatch")
                        continue
                    connection.execute(body.decode(), prepare=False)
                    connection.execute(
                        "INSERT INTO schema_migrations(version, checksum) VALUES (%s, %s)", (number, checksum)
                    )
