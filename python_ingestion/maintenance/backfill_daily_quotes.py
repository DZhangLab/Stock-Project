"""
Backfill historical daily OHLCV bars into everydayAfterClose.

Uses TwelveData's /time_series endpoint with interval="1day" to fetch
proper daily bars (not real-time quote snapshots).  Upserts into the
existing table using ON DUPLICATE KEY UPDATE on the (symbol, datetime)
unique key added by migration 002.

Prerequisites:
    - Migration 002 must have been run first (UNIQUE KEY on symbol, datetime).
      Without it, this script would create duplicates.

Usage:
    # Preview what would be fetched (no writes)
    python -m python_ingestion.maintenance.backfill_daily_quotes \\
        --symbol AAPL --start-date 2025-04-03 --end-date 2026-04-03 --dry-run

    # Run AAPL 1-year backfill
    python -m python_ingestion.maintenance.backfill_daily_quotes \\
        --symbol AAPL --start-date 2025-04-03 --end-date 2026-04-03

    # Backfill multiple symbols
    python -m python_ingestion.maintenance.backfill_daily_quotes \\
        --symbol AAPL --symbol MSFT --start-date 2025-04-03 --end-date 2026-04-03

    # Backfill all symbols tracked by the ingestion system
    python -m python_ingestion.maintenance.backfill_daily_quotes \\
        --all-symbols --start-date 2025-04-03 --end-date 2026-04-03

Rate limiting:
    A sliding-window rate limiter keeps requests within the TwelveData
    per-minute credit limit (default: 8 req/min for the free tier).
    For 505 symbols at 8 rpm this takes approximately 63 minutes.
    Adjust with --rpm if your plan allows more.
"""
import argparse
import logging
import sys
import time
from collections import deque

logger = logging.getLogger(__name__)

# TwelveData free-tier per-minute credit limit.
# The free plan allows 8 API credits per minute.
DEFAULT_RPM = 8

# Extra seconds to wait beyond the sliding-window boundary, to avoid
# race conditions with the server's own clock.
RATE_LIMIT_MARGIN = 2.0


class RateLimiter:
    """
    Sliding-window rate limiter for TwelveData API calls.

    Tracks timestamps of the last N requests within a 60-second window.
    Before each request, if the window is full, sleeps until the oldest
    request falls outside the window.
    """

    def __init__(self, max_per_minute: int):
        self.max_per_minute = max_per_minute
        self.window = 60.0  # seconds
        self.timestamps: deque = deque()

    def acquire(self):
        """Block until it is safe to make the next request, then record it."""
        now = time.monotonic()

        # Evict timestamps older than the window
        while self.timestamps and (now - self.timestamps[0]) >= self.window:
            self.timestamps.popleft()

        if len(self.timestamps) >= self.max_per_minute:
            oldest = self.timestamps[0]
            sleep_for = (oldest + self.window) - now + RATE_LIMIT_MARGIN
            if sleep_for > 0:
                logger.info(
                    "Rate limiter: %d/%d credits used in window, sleeping %.1fs",
                    len(self.timestamps), self.max_per_minute, sleep_for,
                )
                time.sleep(sleep_for)

            # Evict again after sleeping
            now = time.monotonic()
            while self.timestamps and (now - self.timestamps[0]) >= self.window:
                self.timestamps.popleft()

        self.timestamps.append(time.monotonic())

UPSERT_SQL = """
INSERT INTO everydayAfterClose (
    symbol, name, exchange, currency, datetime, timestamp,
    open, high, low, close, volume, previous_close, `change`,
    percent_change, average_volume, is_market_open,
    fifty_two_week_low, fifty_two_week_high, fifty_two_week_low_change,
    fifty_two_week_high_change, fifty_two_week_low_change_percent,
    fifty_two_week_high_change_percent, fifty_two_week_range
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
)
ON DUPLICATE KEY UPDATE
    open = VALUES(open),
    high = VALUES(high),
    low = VALUES(low),
    close = VALUES(close),
    volume = VALUES(volume)
"""


def check_unique_key(db) -> bool:
    """Verify that migration 002 has been applied."""
    rows = db.execute("""
        SELECT 1 FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'everydayAfterClose'
          AND INDEX_NAME = 'uq_symbol_datetime'
        LIMIT 1
    """) or []
    return len(rows) > 0


def get_coverage(db, symbol: str, start_date: str, end_date: str) -> dict:
    """Return current data coverage for a symbol in a date range."""
    rows = db.execute("""
        SELECT COUNT(DISTINCT datetime), MIN(datetime), MAX(datetime)
        FROM everydayAfterClose
        WHERE symbol = %s AND datetime >= %s AND datetime <= %s
    """, (symbol, start_date, end_date))
    if rows and rows[0]:
        return {
            "count": int(rows[0][0] or 0),
            "earliest": rows[0][1],
            "latest": rows[0][2],
        }
    return {"count": 0, "earliest": None, "latest": None}


def backfill_symbol(api_client, db, symbol: str,
                    start_date: str, end_date: str, dry_run: bool) -> dict:
    """
    Fetch daily bars for one symbol and upsert into everydayAfterClose.

    Returns a summary dict with keys: symbol, fetched, upserted, error.
    """
    result = {"symbol": symbol, "fetched": 0, "upserted": 0, "error": None}

    try:
        points = api_client.get_time_series_range(
            symbol=symbol,
            interval="1day",
            start_date=start_date,
            end_date=end_date,
        )
        result["fetched"] = len(points)

        if dry_run:
            before = get_coverage(db, symbol, start_date, end_date)
            logger.info(
                "[DRY RUN] %s: would upsert %d daily bars (%s to %s). "
                "Currently have %d rows in range.",
                symbol, len(points), start_date, end_date, before["count"],
            )
            return result

        if not points:
            logger.warning("%s: API returned 0 daily bars.", symbol)
            return result

        # Build param tuples — daily bars from /time_series only have OHLCV,
        # so non-OHLCV columns get NULL and won't overwrite existing quote data.
        params_list = []
        for p in points:
            # datetime from daily time_series is "yyyy-MM-dd"
            date_str = p.datetime[:10] if len(p.datetime) > 10 else p.datetime
            params_list.append((
                symbol,           # symbol
                None,             # name
                None,             # exchange
                None,             # currency
                date_str,         # datetime
                None,             # timestamp
                p.open,           # open
                p.high,           # high
                p.low,            # low
                p.close,          # close
                int(p.volume) if p.volume else None,  # volume
                None,             # previous_close
                None,             # change
                None,             # percent_change
                None,             # average_volume
                None,             # is_market_open
                None,             # fifty_two_week_low
                None,             # fifty_two_week_high
                None,             # fifty_two_week_low_change
                None,             # fifty_two_week_high_change
                None,             # fifty_two_week_low_change_percent
                None,             # fifty_two_week_high_change_percent
                None,             # fifty_two_week_range
            ))

        affected = db.executemany(UPSERT_SQL, params_list)
        result["upserted"] = len(params_list)

        after = get_coverage(db, symbol, start_date, end_date)
        logger.info(
            "%s: upserted %d daily bars. Coverage in range: %d dates (%s .. %s)",
            symbol, len(params_list), after["count"],
            after["earliest"], after["latest"],
        )

    except Exception as e:
        result["error"] = str(e)
        logger.error("%s: backfill failed — %s", symbol, e)

    return result


def run_backfill(symbols: list, start_date: str, end_date: str,
                 dry_run: bool, rpm: int = DEFAULT_RPM):
    from ..config import load_config
    from ..db import get_db_manager
    from ..twelve_data import TwelveDataClient

    config = load_config()
    db = get_db_manager()
    api_client = TwelveDataClient(config.api)

    # Safety check: unique key must exist
    if not check_unique_key(db):
        logger.error(
            "UNIQUE KEY uq_symbol_datetime not found on everydayAfterClose. "
            "Run migration 002 first:\n"
            "  python -m python_ingestion.migrations.002_fix_daily_quote_duplicates"
        )
        sys.exit(1)

    limiter = RateLimiter(rpm)
    est_minutes = len(symbols) * 60.0 / rpm / 60.0

    print(f"\nBackfilling {len(symbols)} symbol(s): {start_date} to {end_date}")
    print(f"Rate limit: {rpm} requests/minute (estimated ~{est_minutes:.0f} min)")
    if dry_run:
        print("[DRY RUN MODE — no writes]\n")
    else:
        print()

    results = []
    for i, symbol in enumerate(symbols, 1):
        # Wait for rate-limit clearance before each API call.
        # Dry-run still calls the API (to report fetched counts), so
        # the limiter applies in both modes.
        limiter.acquire()

        print(f"[{i}/{len(symbols)}] {symbol}...", end=" ", flush=True)
        r = backfill_symbol(api_client, db, symbol, start_date, end_date, dry_run)

        if r["error"]:
            print(f"ERROR: {r['error']}")
        elif dry_run:
            print(f"would fetch ~{r['fetched']} bars")
        else:
            print(f"OK ({r['fetched']} fetched, {r['upserted']} upserted)")

        results.append(r)

    # --- Summary ---
    succeeded = [r for r in results if r["error"] is None]
    failed = [r for r in results if r["error"] is not None]
    total_fetched = sum(r["fetched"] for r in results)

    print(f"\n{'=' * 55}")
    print(f"Backfill {'(dry run) ' if dry_run else ''}complete.")
    print(f"  Symbols:   {len(succeeded)} succeeded, {len(failed)} failed")
    print(f"  Bars:      {total_fetched} fetched")
    if failed:
        print(f"  Failed:    {', '.join(r['symbol'] for r in failed)}")
    print(f"{'=' * 55}\n")

    # Coverage report
    if not dry_run and succeeded:
        print("Coverage report:")
        print(f"  {'Symbol':<10} {'Dates':>6} {'Earliest':>12} {'Latest':>12}")
        print(f"  {'-'*42}")
        for r in succeeded:
            cov = get_coverage(db, r["symbol"], start_date, end_date)
            print(f"  {r['symbol']:<10} {cov['count']:>6} {cov['earliest'] or 'N/A':>12} {cov['latest'] or 'N/A':>12}")


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Backfill historical daily OHLCV bars into everydayAfterClose."
    )
    parser.add_argument(
        "--symbol", action="append", dest="symbols",
        help="Symbol to backfill (repeatable). Use --all-symbols for everything.",
    )
    parser.add_argument(
        "--all-symbols", action="store_true",
        help="Backfill all symbols tracked by the ingestion system.",
    )
    parser.add_argument(
        "--start-date", required=True,
        help="Start date (yyyy-MM-dd).",
    )
    parser.add_argument(
        "--end-date", required=True,
        help="End date (yyyy-MM-dd).",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview what would be fetched without writing to the database.",
    )
    parser.add_argument(
        "--rpm", type=int, default=DEFAULT_RPM,
        help=f"Max API requests per minute (default: {DEFAULT_RPM}).",
    )
    args = parser.parse_args()

    if args.rpm < 1:
        parser.error("--rpm must be at least 1.")

    if args.all_symbols:
        from ..symbols import load_symbols
        symbols = load_symbols()
    elif args.symbols:
        symbols = [s.upper() for s in args.symbols]
    else:
        parser.error("Provide --symbol or --all-symbols.")

    run_backfill(symbols, args.start_date, args.end_date, args.dry_run, args.rpm)


if __name__ == "__main__":
    main()
