"""One supervised task and one atomic commit per provider group; no API-triggered requests."""

import asyncio
import logging
from datetime import datetime, timezone

import httpx

from .collection import Deferred, GroupState, ProviderHTTP
from .gdp import timestamp
from .indicators import store_batch

LOG = logging.getLogger(__name__)


class MacroCollector:
    def __init__(self, adapter, settings, database, clock, client=None):
        self.adapter, self.settings, self.db, self.clock, self.client = (
            adapter,
            settings,
            database,
            clock,
            client,
        )
        self.group, self.provider, self.panel = adapter.group, adapter.provider, adapter.panel
        self.interval, self.notes = adapter.interval, adapter.notes
        self.state = GroupState(database, clock, self.group, self.provider, self.interval)
        self.task = None

    def coverage(self, points):
        return self.adapter.coverage([p for p in points if p.definition.group == self.group])

    def recover(self):
        self.state.recover(timestamp(self.clock()))

    async def collect_once(self):
        year = datetime.fromtimestamp(self.clock(), timezone.utc).year
        run = await asyncio.to_thread(
            self.state.begin, timestamp(self.clock()), year - self.settings.report_years - 1, year
        )
        if run is None:
            return False
        try:
            async with httpx.AsyncClient(
                follow_redirects=False,
                headers={"User-Agent": "EconomicIndicatorsDashboard/0.2", "Accept": "*/*"},
            ) as owned:
                http = ProviderHTTP(
                    self.state,
                    self.client or owned,
                    self.settings.upstream_timeout,
                    self.settings.upstream_attempts,
                )

                async def fetch(url):
                    return await http.fetch(url, max_bytes=32 * 1024 * 1024)

                async with asyncio.timeout(self.settings.collection_budget):
                    rows = await self.adapter.collect(fetch, lambda: timestamp(self.clock()))
            await asyncio.to_thread(store_batch, self.db, self.state, run, rows)
            LOG.info("%s collection %s succeeded (%s points)", self.group, run, len(rows))
            return True
        except asyncio.CancelledError:
            await asyncio.to_thread(self.state.finish, run, timestamp(self.clock()), "interrupted")
            raise
        except Exception as exc:
            kind = (
                "rate_limited"
                if isinstance(exc, Deferred)
                else "timeout"
                if isinstance(exc, (httpx.TimeoutException, TimeoutError))
                else "http_rejection"
                if isinstance(exc, httpx.HTTPStatusError)
                else "network_error"
                if isinstance(exc, httpx.RequestError)
                else "invalid_payload"
                if isinstance(exc, (ValueError, TypeError, KeyError, AttributeError))
                else "storage_error"
            )
            await asyncio.to_thread(self.state.finish, run, timestamp(self.clock()), kind)
            LOG.warning("%s collection %s failed (%s)", self.group, run, kind)
            return False

    async def supervise(self):
        while True:
            try:
                if await asyncio.to_thread(self.state.due):
                    await self.collect_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                LOG.exception("%s supervisor will retry", self.group)
            await asyncio.sleep(min(30, self.interval))
