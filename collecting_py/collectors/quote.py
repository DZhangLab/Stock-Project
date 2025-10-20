"""Daily quote collection."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Iterable, Sequence

from zoneinfo import ZoneInfo

from ..clients import TwelveDataClient, extract_quote
from ..config import Settings, get_settings
from ..db import bulk_upsert_quotes, session_scope

LOGGER = logging.getLogger(__name__)


class QuoteCollector:
    """Fetches summary quote data for configured symbols."""

    def __init__(self, settings: Settings | None = None, client: TwelveDataClient | None = None) -> None:
        self.settings = settings or get_settings()
        self.client = client or TwelveDataClient(self.settings)
        self.timezone: ZoneInfo = self.settings.timezone

    def collect(self, symbols: Sequence[str] | None = None) -> int:
        symbols = symbols or self.settings.quote_symbols
        if not symbols:
            LOGGER.warning("No symbols configured for quote collection")
            return 0

        rows = []
        for symbol in symbols:
            rows.append(self._collect_symbol(symbol))
        with session_scope(self.settings) as session:
            inserted = bulk_upsert_quotes(session, rows)
        LOGGER.info("Upserted %s quotes", inserted)
        return inserted

    def _collect_symbol(self, symbol: str) -> dict:
        LOGGER.info("Fetching quote for %s", symbol)
        payload = self.client.fetch_quote(symbol)
        data = extract_quote(payload)
        timestamp = datetime.strptime(data["datetime"], "%Y-%m-%d %H:%M:%S")
        data["datetime"] = timestamp.replace(tzinfo=self.timezone)
        return data


def collect_once(symbols: Iterable[str] | None = None) -> int:
    collector = QuoteCollector()
    return collector.collect(list(symbols) if symbols else None)

