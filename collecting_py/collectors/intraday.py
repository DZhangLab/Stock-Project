"""Minute-level data collection for Twelve Data symbols."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Iterable, Sequence

from zoneinfo import ZoneInfo

from ..clients import TwelveDataClient, extract_time_series
from ..config import Settings, get_settings
from ..db import bulk_upsert_intraday, ensure_intraday_table, get_engine

LOGGER = logging.getLogger(__name__)


class IntradayCollector:
    """Fetches intraday candles and persists them in per-symbol tables."""

    def __init__(self, settings: Settings | None = None, client: TwelveDataClient | None = None) -> None:
        self.settings = settings or get_settings()
        self.client = client or TwelveDataClient(self.settings)
        self.engine = get_engine(self.settings)
        self.timezone: ZoneInfo = self.settings.timezone

    def collect(self, symbols: Sequence[str] | None = None) -> int:
        """Collect intraday data for *symbols* (defaults to settings)."""

        symbols = symbols or self.settings.intraday_symbols
        if not symbols:
            LOGGER.warning("No symbols configured for intraday collection")
            return 0

        processed = 0
        for symbol in symbols:
            processed += self._collect_symbol(symbol)
        return processed

    def _collect_symbol(self, symbol: str) -> int:
        LOGGER.info("Fetching intraday series for %s", symbol)
        payload = self.client.fetch_intraday(symbol)
        table = ensure_intraday_table(self.engine, symbol)
        rows = [self._normalise_entry(entry, symbol) for entry in extract_time_series(payload)]
        inserted = bulk_upsert_intraday(self.engine, table, rows)
        LOGGER.info("Upserted %s rows into %s", inserted, table.name)
        return inserted

    def _normalise_entry(self, entry: dict, symbol: str) -> dict:
        timestamp = datetime.strptime(entry["datetime"], "%Y-%m-%d %H:%M:%S")
        timestamp = timestamp.replace(tzinfo=self.timezone)
        return {
            "timestamp": timestamp,
            "open": float(entry["open"]),
            "high": float(entry["high"]),
            "low": float(entry["low"]),
            "close": float(entry["close"]),
            "volume": float(entry["volume"]),
        }


def collect_once(symbols: Iterable[str] | None = None) -> int:
    """Convenience function for ad-hoc intraday runs."""

    collector = IntradayCollector()
    return collector.collect(list(symbols) if symbols else None)

