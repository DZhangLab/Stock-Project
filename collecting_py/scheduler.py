"""APScheduler integration for running collectors on a schedule."""
from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .collectors.intraday import IntradayCollector
from .collectors.quote import QuoteCollector
from .config import Settings, get_settings

LOGGER = logging.getLogger(__name__)


class CollectorScheduler:
    """Registers periodic jobs for the intraday and quote collectors."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.scheduler = BackgroundScheduler(timezone=self.settings.timezone)
        self.intraday_collector = IntradayCollector(self.settings)
        self.quote_collector = QuoteCollector(self.settings)

    def start(self) -> None:
        self._register_jobs()
        LOGGER.info("Starting scheduler with %s jobs", len(self.scheduler.get_jobs()))
        self.scheduler.start()

    def shutdown(self) -> None:
        LOGGER.info("Shutting down scheduler")
        self.scheduler.shutdown(wait=False)

    def _register_jobs(self) -> None:
        if self.settings.intraday_symbols:
            trigger = IntervalTrigger(seconds=self.settings.intraday_interval_seconds)
            self.scheduler.add_job(
                self.intraday_collector.collect,
                trigger=trigger,
                kwargs={"symbols": self.settings.intraday_symbols},
                id="intraday-collector",
                replace_existing=True,
            )
            LOGGER.info(
                "Registered intraday job every %s seconds for %s symbols",
                self.settings.intraday_interval_seconds,
                len(self.settings.intraday_symbols),
            )
        if self.settings.quote_symbols:
            trigger = IntervalTrigger(seconds=self.settings.quote_interval_seconds)
            self.scheduler.add_job(
                self.quote_collector.collect,
                trigger=trigger,
                kwargs={"symbols": self.settings.quote_symbols},
                id="quote-collector",
                replace_existing=True,
            )
            LOGGER.info(
                "Registered quote job every %s seconds for %s symbols",
                self.settings.quote_interval_seconds,
                len(self.settings.quote_symbols),
            )

