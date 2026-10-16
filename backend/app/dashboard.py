"""Protected aggregate projection. This module has no HTTP/provider transport dependency."""

from typing import Annotated, Literal

from pydantic import Field

from .gdp import read_panel, timestamp
from .indicators import GroupCollection, IndicatorPanel, collection_status, read_indicator
from .markets import TickerItem, read_markets
from .models import Model, Panel


class Dashboard(Model):
    schema_version: Literal["1"] = "1"
    generated_at: str
    panels: list[Annotated[Panel | IndicatorPanel, Field(discriminator="id")]]
    ticker: list[TickerItem]
    collection_groups: list[GroupCollection]


def read_dashboard(database, settings, jobs, now):
    gdp = read_panel(database, settings, now)
    panels = [gdp] + [
        read_indicator(database, name, jobs, now, settings.macro_report_years)
        for name in ("debt", "trade", "gst", "inflation", "expenditure")
    ]
    with database.connect() as db:
        gdp_status = collection_status(db, "gdp", "world_bank_wdi", settings.collection_interval, now)
    ticker, market_groups = read_markets(database, jobs, now)
    groups = (
        [gdp_status]
        + [status for p in panels if isinstance(p, IndicatorPanel) for status in p.collection]
        + market_groups
    )
    return Dashboard(
        generated_at=timestamp(now),
        panels=panels,
        collection_groups=groups,
        ticker=ticker,
    )
