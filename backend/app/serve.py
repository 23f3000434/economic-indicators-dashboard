"""Free production entry: one API worker, internal PostgreSQL, explicit proxy policy."""

import fcntl
import ipaddress
import os
from contextlib import contextmanager
from urllib.parse import urlsplit

import uvicorn

from .config import Settings


def configuration(settings):
    if settings.environment != "production":
        raise ValueError(
            "Deployment entry point requires APP_ENV=production; use the documented local command"
        )
    if not settings.database_url:
        raise ValueError("Free production requires DATABASE_URL; ephemeral SQLite is forbidden")
    target = urlsplit(settings.database_url)
    if not target.hostname.startswith("dpg-") or "." in target.hostname:
        raise ValueError("Production DATABASE_URL must use the Render internal hostname")
    proxies = os.environ.get("TRUSTED_PROXY_CIDRS", "")
    entries = proxies.split(",") if proxies else []
    for value in entries:
        if not value or value != value.strip():
            raise ValueError("Proxy addresses must be explicit comma-separated CIDRs")
        network = ipaddress.ip_network(value, strict=False)
        if network.prefixlen == 0:
            raise ValueError("Trusting all peers is forbidden")
    port = int(os.environ.get("PORT", "10000"))
    if not 1 <= port <= 65535:
        raise ValueError("Invalid HTTP PORT")
    return dict(
        host="0.0.0.0",
        port=port,
        workers=1,
        proxy_headers=bool(entries),
        forwarded_allow_ips=",".join(entries),
        access_log=False,
    )


@contextmanager
def sqlite_owner(path):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    descriptor = os.open(path.parent / ".api-owner.lock", os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        os.close(descriptor)


def main():
    os.umask(0o077)
    settings = Settings.load()
    options = configuration(settings)
    # PostgreSQL lifespan owns the fenced advisory collector lease. A deploying
    # standby serves reads without recovering the old active worker.
    uvicorn.run("app.main:create_app", factory=True, **options)


if __name__ == "__main__":
    main()
