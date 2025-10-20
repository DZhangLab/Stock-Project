"""Historical backfill collection."""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Iterable, Sequence

from zoneinfo import ZoneInfo

from ..clients import TwelveDataClient, extract_time_series
from ..config import Settings, get_settings
from ..db import bulk_upsert_intraday, ensure_intraday_table, get_engine

LOGGER = logging.getLogger(__name__)


class HistoryCollector:
    """Backfills intraday data over a configurable date range."""

    def __init__(self, settings: Settings | None = None, client: TwelveDataClient | None = None) -> None:
        self.settings = settings or get_settings()
        self.client = client or TwelveDataClient(self.settings)
        self.engine = get_engine(self.settings)
        self.timezone: ZoneInfo = self.settings.timezone

    def collect(self, symbol: str, start: date, end: date) -> int:
        table = ensure_intraday_table(self.engine, symbol)
        total = 0
        for chunk in self._generate_ranges(start, end, self.settings.history_batch_days):
            start_str = chunk[0].isoformat()
            end_str = chunk[-1].isoformat()
            LOGGER.info("Fetching %s history from %s to %s", symbol, start_str, end_str)
            payload = self.client.fetch_intraday_range(symbol, start_str, end_str)
            rows = [self._normalise_entry(entry) for entry in extract_time_series(payload)]
            total += bulk_upsert_intraday(self.engine, table, rows)
        LOGGER.info("Backfill complete for %s (%s rows)", symbol, total)
        return total

    def _normalise_entry(self, entry: dict) -> dict:
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

    def _generate_ranges(self, start: date, end: date, step_days: int) -> Iterable[Sequence[date]]:
        current = start
        while current <= end:
            batch_end = min(end, current + timedelta(days=step_days - 1))
            yield [current + timedelta(days=offset) for offset in range((batch_end - current).days + 1)]
            current = batch_end + timedelta(days=1)

