"""Command line entry point for the collectors."""
from __future__ import annotations

import argparse
import logging
from datetime import datetime
from typing import Iterable, Sequence

from .collectors.history import HistoryCollector
from .collectors.intraday import IntradayCollector
from .collectors.quote import QuoteCollector
from .config import Settings, get_settings
from .scheduler import CollectorScheduler


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Twelve Data collection toolkit")
    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_intraday = subparsers.add_parser("collect-intraday", help="Collect intraday candles once")
    parser_intraday.add_argument("symbols", nargs="*", help="Symbols to collect; defaults to INTRADAY_SYMBOLS")

    parser_quote = subparsers.add_parser("collect-quote", help="Collect quotes once")
    parser_quote.add_argument("symbols", nargs="*", help="Symbols to collect; defaults to QUOTE_SYMBOLS")

    parser_history = subparsers.add_parser("collect-history", help="Backfill intraday data for a date range")
    parser_history.add_argument("symbol", help="Symbol to backfill")
    parser_history.add_argument("start", help="Start date (YYYY-MM-DD)")
    parser_history.add_argument("end", help="End date (YYYY-MM-DD)")

    subparsers.add_parser("run-scheduler", help="Run the background scheduler")

    return parser


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")


def parse_date(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging()

    settings = get_settings()

    if args.command == "collect-intraday":
        collector = IntradayCollector(settings)
        count = collector.collect(args.symbols or None)
        logging.info("Collected %s intraday rows", count)
        return 0
    if args.command == "collect-quote":
        collector = QuoteCollector(settings)
        count = collector.collect(args.symbols or None)
        logging.info("Collected %s quote rows", count)
        return 0
    if args.command == "collect-history":
        collector = HistoryCollector(settings)
        start = parse_date(args.start).date()
        end = parse_date(args.end).date()
        count = collector.collect(args.symbol, start, end)
        logging.info("Backfilled %s rows", count)
        return 0
    if args.command == "run-scheduler":
        scheduler = CollectorScheduler(settings)
        scheduler.start()
        try:
            logging.info("Scheduler running; press Ctrl+C to exit")
            while True:
                pass
        except KeyboardInterrupt:
            scheduler.shutdown()
        return 0
    parser.error("Unknown command")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

