"""Per-group collection history and durable provider-wide HTTP cooldowns."""

import asyncio
import logging
import sqlite3
import threading
import time
from datetime import timezone
from email.utils import parsedate_to_datetime

import httpx

from .db import Database


async def joined_thread(function, *args, cancelled_result=None):
    """Do not classify cancelled work as abandoned while its SQL worker is active."""
    task = asyncio.create_task(asyncio.to_thread(function, *args))
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        try:
            result = await task
        except Exception:
            pass  # the caller records interruption after the worker has settled
        else:
            if cancelled_result:
                await asyncio.to_thread(cancelled_result, result)
        raise


def retry_after(value: str | None, now: float) -> float | None:
    if value is None:
        return None
    value = value.strip()
    if value.isascii() and value.isdigit():
        try:
            return now + int(value)
        except (ValueError, OverflowError):
            return None
    try:
        date = parsedate_to_datetime(value)
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        return max(now, date.timestamp())
    except (ValueError, TypeError, OverflowError):
        return None


class Deferred(Exception):
    def __init__(self, not_before: float):
        self.not_before = not_before
        super().__init__("Provider cooldown exceeds the current request budget")


class NotConfigured(Exception):
    pass


class GroupState:
    def __init__(
        self,
        database: Database,
        clock,
        group="gdp",
        provider="world_bank_wdi",
        interval=604800,
        retention=200,
    ):
        self.database, self.clock = database, clock
        self.group, self.provider, self.interval, self.retention = group, provider, interval, retention
        # Only this instance's definitively finished work is eligible for recovery.
        # Never expire a run merely because it is old: HTTP/parsing work may still be active.
        self.pending_failures = {}
        self.pending_lock = threading.RLock()

    def fail_safely(self, run, at, error):
        with self.pending_lock:
            self.pending_failures[run] = (at, error)
            try:
                self.retry_failures()
            except sqlite3.Error:
                logging.getLogger(__name__).warning("%s run %s awaits storage recovery", self.group, run)

    def retry_failures(self):
        with self.pending_lock:
            for run, (at, error) in list(self.pending_failures.items()):
                self.finish(run, at, error)
                del self.pending_failures[run]

    def cooldown(self):
        with self.database.connect() as db:
            row = db.execute(
                "SELECT not_before FROM provider_cooldowns WHERE provider_id=?", (self.provider,)
            ).fetchone()
        return row[0] if row else 0

    def defer(self, not_before):
        with self.database.connect(write=True) as db:
            db.execute(
                "INSERT INTO provider_cooldowns VALUES (?, ?, 'retry_after') ON CONFLICT(provider_id) DO UPDATE SET not_before=MAX(not_before, excluded.not_before), reason=excluded.reason",
                (self.provider, not_before),
            )

    def recover(self, at):
        with self.database.connect(write=True) as db:
            db.execute(
                "UPDATE collection_runs SET outcome='error', error_kind='interrupted', completed_at=? WHERE group_id=? AND outcome='running'",
                (at, self.group),
            )

    def due(self):
        self.retry_failures()
        if self.clock() < self.cooldown():
            return False
        with self.database.connect() as db:
            row = db.execute(
                "SELECT * FROM collection_runs WHERE group_id=? ORDER BY id DESC LIMIT 1", (self.group,)
            ).fetchone()
        if not row:
            return True
        if row["outcome"] == "running":
            return False
        from datetime import datetime

        interval = min(3600, self.interval) if row["outcome"] == "error" else self.interval
        return (
            self.clock()
            >= datetime.fromisoformat(row["attempted_at"].replace("Z", "+00:00")).timestamp() + interval
        )

    def begin(self, at, start, end):
        self.retry_failures()
        with self.database.connect(write=True) as db:
            cooldown = db.execute(
                "SELECT not_before FROM provider_cooldowns WHERE provider_id=?", (self.provider,)
            ).fetchone()
            if (cooldown and self.clock() < cooldown[0]) or db.execute(
                "SELECT 1 FROM collection_runs WHERE group_id=? AND outcome='running'", (self.group,)
            ).fetchone():
                return None
            return db.execute(
                "INSERT INTO collection_runs(group_id, provider_id, attempted_at, outcome, window_start, window_end) VALUES (?, ?, ?, 'running', ?, ?)",
                (self.group, self.provider, at, start, end),
            ).lastrowid

    def finish_in(self, db, run, at, error=None):
        db.execute(
            "UPDATE collection_runs SET outcome=?, error_kind=?, completed_at=? WHERE id=? AND group_id=? AND outcome='running'",
            ("error" if error else "ok", error, at, run, self.group),
        )
        # Retain this group's recent completed records plus its last success and all running records.
        # Other groups are never candidates, however frequent their collection schedule.
        db.execute(
            """DELETE FROM collection_runs WHERE group_id=? AND outcome!='running'
            AND id NOT IN (SELECT id FROM collection_runs WHERE group_id=? AND outcome!='running' ORDER BY id DESC LIMIT ?)
            AND id != COALESCE((SELECT MAX(id) FROM collection_runs WHERE group_id=? AND outcome='ok'), -1)""",
            (self.group, self.group, self.retention, self.group),
        )

    def finish(self, run, at, error=None):
        with self.database.connect(write=True) as db:
            self.finish_in(db, run, at, error)


class ProviderHTTP:
    def __init__(
        self,
        state: GroupState,
        client: httpx.AsyncClient,
        timeout=20,
        attempts=2,
        sleep=asyncio.sleep,
        monotonic=time.monotonic,
    ):
        self.state, self.client = state, client
        self.timeout, self.attempts, self.sleep, self.monotonic = timeout, attempts, sleep, monotonic

    async def fetch(self, url, max_bytes=4 * 1024 * 1024, *, method="GET", json=None, headers=None):
        if method not in {"GET", "POST"}:
            raise ValueError("Unsupported public provider request method")
        # HTTPX read timeouts reset between chunks. This outer deadline also
        # bounds slow/dripping streams and mock transports that ignore timeouts.
        async with asyncio.timeout(self.timeout * self.attempts):
            return await self._fetch(url, max_bytes, method, json, headers)

    async def _fetch(self, url, max_bytes, method, payload, headers):
        deadline = self.monotonic() + self.timeout * self.attempts
        for attempt in range(self.attempts):
            # Recheck before every request: a different request/group may have extended this provider's cooldown.
            delay = max(0, self.state.cooldown() - self.state.clock())
            remaining = deadline - self.monotonic()
            if delay:
                if delay >= remaining:
                    raise Deferred(self.state.cooldown())
                await self.sleep(delay)
                while self.state.clock() < self.state.cooldown():
                    delay = self.state.cooldown() - self.state.clock()
                    if delay >= deadline - self.monotonic():
                        raise Deferred(self.state.cooldown())
                    await self.sleep(delay)
            remaining = deadline - self.monotonic()
            if remaining <= 0:
                raise TimeoutError("Request budget exhausted")
            try:
                async with self.client.stream(
                    method,
                    url,
                    json=payload,
                    headers=headers,
                    timeout=httpx.Timeout(min(self.timeout, remaining), connect=min(5, remaining)),
                ) as response:
                    until = (
                        retry_after(response.headers.get("retry-after"), self.state.clock())
                        if response.status_code in {429, 503}
                        else None
                    )
                    if until is not None:
                        self.state.defer(
                            until
                        )  # persist before deciding whether another attempt is affordable
                        if (
                            attempt + 1 == self.attempts
                            or until - self.state.clock() >= deadline - self.monotonic()
                        ):
                            raise Deferred(self.state.cooldown())
                        continue
                    response.raise_for_status()
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > max_bytes:
                            raise ValueError("Upstream response exceeds byte budget")
                    return bytes(body)
            except (httpx.TimeoutException, httpx.NetworkError):
                if attempt + 1 == self.attempts:
                    raise
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code not in {429, 502, 503, 504} or attempt + 1 == self.attempts:
                    raise
            wait = 0.5 * (attempt + 1)
            if wait >= deadline - self.monotonic():
                raise TimeoutError("Retry budget exhausted")
            await self.sleep(wait)
        raise RuntimeError("No HTTP attempt result")
