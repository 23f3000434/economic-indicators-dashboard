import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

MIGRATIONS = Path(__file__).resolve().parents[1] / "migrations"


class Database:
    def __init__(self, path: Path):
        self.path = path

    @contextmanager
    def connect(self, write=False):
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
