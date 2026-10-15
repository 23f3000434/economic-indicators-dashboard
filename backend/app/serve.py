"""Production entry point: one SQLite owner, mounted private storage, explicit proxy trust."""

import fcntl
import ipaddress
import os
from contextlib import contextmanager
from pathlib import Path

import uvicorn

from .config import Settings


def configuration(settings):
    if settings.environment != "production":
        raise ValueError(
            "Deployment entry point requires APP_ENV=production; use the documented local command"
        )
    root = Path(os.environ["PERSISTENT_DATA_DIR"]).resolve(strict=True)
    if root == Path("/") or not root.is_mount():
        raise ValueError("PERSISTENT_DATA_DIR must be the attached persistent disk mount")
    if not settings.database.is_relative_to(root) or settings.database.parent == root:
        raise ValueError("SQLITE_PATH must be inside a private subdirectory of the persistent mount")
    proxies = os.environ["TRUSTED_PROXY_CIDRS"].split(",")
    if not proxies or any(not value.strip() or value != value.strip() for value in proxies):
        raise ValueError("Provide reviewed proxy IP addresses/CIDRs, comma-separated without spaces")
    for value in proxies:
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
        proxy_headers=True,
        forwarded_allow_ips=",".join(proxies),
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
    # Acquire before lifespan migrations/recovery; a second process cannot mark active work interrupted.
    with sqlite_owner(settings.database):
        uvicorn.run("app.main:create_app", factory=True, **options)


if __name__ == "__main__":
    main()
