"""
Catch up missing intraday 1-minute bars for one or more symbols.

For each symbol, detects the latest existing timePoint in its intraday
table (unless --start-date overrides) and fetches everything from there
through --end-date (default: now) via TwelveData's /time_series endpoint.

Upserts into the per-symbol intraday table using ON DUPLICATE KEY UPDATE
on the existing uq_timepoint unique key.

Rate limiting:
    TwelveData enforces a **rolling-window** per-minute credit limit on
    their server side.  The window is not reset between process
    invocations — if batch 0 used 6 credits in its last 30 seconds,
    batch 1 starting immediately only has 2 credits available until
    those first 6 age out of the provider's 60-second window.

    To handle this safely:

    1.  A timestamp file (~/.catch_up_intraday_ts) persists the wall-clock
        times of recent API calls.  A new process loads these on startup
        so it knows how much budget remains from the previous run.

    2.  The default --rpm is set conservatively to 6 (not the nominal
        free-tier limit of 8) to leave headroom for clock skew and for
        other processes (scheduler, manual queries) that share the same
        API key.

    3.  When a rate-limit error is received despite the local limiter,
        the script sleeps a full 62 seconds (window + margin), clears
        the limiter, and retries the same symbol up to 5 times before
        giving up.

Provider limitation:
    TwelveData free-tier accounts can only retrieve ~1-2 months of
    minute-level history.  Requests for older data will return an empty
    result set — this is an unavoidable provider limitation, not a bug.

Usage:
    # Dry run for AAPL (detect start from DB, preview only)
    python -m python_ingestion.maintenance.catch_up_intraday \\
        --symbol AAPL --dry-run

    # Real catch-up for AAPL
    python -m python_ingestion.maintenance.catch_up_intraday \\
        --symbol AAPL

    # Multiple symbols with explicit date range
    python -m python_ingestion.maintenance.catch_up_intraday \\
        --symbol AAPL --symbol MSFT \\
        --start-date 2026-03-15 --end-date 2026-04-05

    # All tracked symbols
    python -m python_ingestion.maintenance.catch_up_intraday \\
        --all-symbols --dry-run

    # All symbols in batches of 50 (run each in a separate invocation)
    python -m python_ingestion.maintenance.catch_up_intraday \\
        --all-symbols --batch-size 50 --batch-index 0
    python -m python_ingestion.maintenance.catch_up_intraday \\
        --all-symbols --batch-size 50 --batch-index 1
    # ... up to --batch-index 10 for 505 symbols
"""
import argparse
import json
import logging
import os
import sys
import time
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

# Conservative default: 6 of the nominal 8 free-tier credits/min.
# Leaves 2 credits/min headroom for clock skew, the live scheduler,
# and other processes sharing the same API key.
DEFAULT_RPM = 6

# Extra seconds added to the 60-second window when sleeping.
RATE_LIMIT_MARGIN = 2.0

# Retries per symbol when a rate-limit error is received from the
# provider despite the local limiter (cross-process budget exhaustion).
MAX_RETRIES = 5

# File used to persist recent request timestamps across invocations.
# Allows a new process to know how much budget was consumed by the
# previous run's final seconds.
_TS_FILE = Path.home() / ".catch_up_intraday_ts"

# Only timestamps younger than this are loaded from the file.
_TS_MAX_AGE = 90.0  # seconds


def _load_persisted_timestamps() -> list[float]:
    """Load wall-clock timestamps from the persistence file.

    Returns a list of time.time() floats that are still within the
    rolling window (younger than _TS_MAX_AGE seconds).
    """
    if not _TS_FILE.exists():
        return []
    try:
        data = json.loads(_TS_FILE.read_text())
        now = time.time()
        return [t for t in data if (now - t) < _TS_MAX_AGE]
    except Exception as e:
        logger.debug("Could not load timestamp file %s: %s", _TS_FILE, e)
        return []


def _save_persisted_timestamps(wall_times: list[float]):
    """Persist the most recent wall-clock timestamps to disk.

    Only keeps entries younger than _TS_MAX_AGE to avoid unbounded growth.
    """
    now = time.time()
    recent = [t for t in wall_times if (now - t) < _TS_MAX_AGE]
    try:
        _TS_FILE.write_text(json.dumps(recent))
    except Exception as e:
        logger.debug("Could not write timestamp file %s: %s", _TS_FILE, e)


class RateLimiter:
    """Sliding-window rate limiter for TwelveData API calls.

    TwelveData's per-minute limit is a **rolling window** on their server.
    This limiter mirrors that locally, tracking monotonic timestamps for
    intra-process spacing and wall-clock timestamps for cross-process
    persistence.  On startup it loads recent wall-clock timestamps from a
    file so that a freshly started batch does not assume a full budget.
    """

    def __init__(self, max_per_minute: int):
        self.max_per_minute = max_per_minute
        self.window = 60.0
        # Monotonic timestamps for intra-process sleep calculations.
        self.timestamps: deque[float] = deque()
        # Parallel wall-clock (time.time()) timestamps for persistence.
        self.wall_times: list[float] = []

        self._seed_from_file()

    def _seed_from_file(self):
        """Pre-fill the limiter with timestamps from the previous process."""
        persisted = _load_persisted_timestamps()
        if not persisted:
            return

        now_wall = time.time()
        now_mono = time.monotonic()
        seeded = 0
        for wt in persisted:
            age = now_wall - wt
            if age < self.window:
                # Convert wall-clock age to a synthetic monotonic timestamp.
                self.timestamps.append(now_mono - age)
                self.wall_times.append(wt)
                seeded += 1

        if seeded:
            logger.info(
                "Rate limiter: seeded %d request(s) from previous run "
                "(%.0fs – %.0fs ago).",
                seeded,
                min(now_wall - wt for wt in persisted if (now_wall - wt) < self.window),
                max(now_wall - wt for wt in persisted if (now_wall - wt) < self.window),
            )

    def _evict(self):
        """Remove timestamps older than the rolling window."""
        now = time.monotonic()
        while self.timestamps and (now - self.timestamps[0]) >= self.window:
            self.timestamps.popleft()
        now_wall = time.time()
        self.wall_times = [t for t in self.wall_times if (now_wall - t) < self.window]

    def acquire(self):
        """Block until it is safe to make the next request, then record it."""
        self._evict()

        if len(self.timestamps) >= self.max_per_minute:
            oldest = self.timestamps[0]
            sleep_for = (oldest + self.window) - time.monotonic() + RATE_LIMIT_MARGIN
            if sleep_for > 0:
                logger.info(
                    "Rate limiter: %d/%d credits used in window, sleeping %.1fs",
                    len(self.timestamps), self.max_per_minute, sleep_for,
                )
                time.sleep(sleep_for)
            self._evict()

        now_mono = time.monotonic()
        now_wall = time.time()
        self.timestamps.append(now_mono)
        self.wall_times.append(now_wall)
        _save_persisted_timestamps(self.wall_times)

    def clear(self):
        """Reset after a forced full-window sleep (rate-limit recovery)."""
        self.timestamps.clear()
        self.wall_times.clear()
        _save_persisted_timestamps(self.wall_times)


def is_rate_limit_error(exc: Exception) -> bool:
    """Return True if the exception indicates a TwelveData rate-limit error."""
    msg = str(exc).lower()
    return any(kw in msg for kw in ("429", "rate", "credit", "too many", "quota"))


def get_latest_timepoint(db, table_name: str) -> str | None:
    """Return the latest timePoint in the given intraday table, or None."""
    try:
        rows = db.execute(
            f"SELECT MAX(timePoint) FROM `{table_name}`"
        )
        if rows and rows[0] and rows[0][0]:
            return str(rows[0][0])
    except Exception as e:
        logger.warning("Could not read latest timePoint from %s: %s", table_name, e)
    return None


def get_row_count(db, table_name: str) -> int:
    """Return total row count in the given intraday table."""
    try:
        rows = db.execute(f"SELECT COUNT(*) FROM `{table_name}`")
        if rows and rows[0]:
            return int(rows[0][0])
    except Exception:
        pass
    return 0


def catch_up_symbol(api_client, db, symbol: str, table_name: str,
                    start_date: str, end_date: str,
                    dry_run: bool) -> dict:
    """
    Fetch and upsert missing intraday bars for one symbol.

    Returns a summary dict: symbol, table, fetched, upserted, earliest,
    latest, error.
    """
    result = {
        "symbol": symbol, "table": table_name,
        "fetched": 0, "upserted": 0,
        "earliest": None, "latest": None, "error": None,
    }

    try:
        if dry_run:
            existing = get_latest_timepoint(db, table_name)
            count = get_row_count(db, table_name)
            logger.info(
                "[DRY RUN] %s (%s): would fetch %s to %s. "
                "Currently %d rows, latest timePoint = %s",
                symbol, table_name, start_date, end_date,
                count, existing or "N/A",
            )
            return result

        # Ensure table exists with correct schema
        db.ensure_intraday_table(symbol, table_name)

        # Fetch from TwelveData
        try:
            points = api_client.get_time_series_range(
                symbol=symbol,
                interval="1min",
                start_date=start_date,
                end_date=end_date,
            )
        except ValueError as e:
            # "No data is available on the specified dates" is normal when
            # the DB is already caught up to the latest published bar.
            if "no data is available" in str(e).lower():
                logger.info(
                    "%s: already up to date (no new bars from %s to %s).",
                    symbol, start_date, end_date,
                )
                return result
            raise
        result["fetched"] = len(points)

        if not points:
            logger.warning(
                "%s: API returned 0 bars for %s to %s. "
                "This may be an unavoidable provider limitation if the "
                "requested range exceeds TwelveData's minute-level history "
                "retention for your plan.",
                symbol, start_date, end_date,
            )
            return result

        # Sort ascending before insert
        points.sort(key=lambda p: p.datetime)
        result["earliest"] = points[0].datetime
        result["latest"] = points[-1].datetime

        # Upsert
        insert_sql = f"""
        INSERT INTO `{table_name}`
            (timePoint, minuteOpen, minuteHigh, minuteLow, minuteClose, minuteVolume)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            minuteOpen  = VALUES(minuteOpen),
            minuteHigh  = VALUES(minuteHigh),
            minuteLow   = VALUES(minuteLow),
            minuteClose = VALUES(minuteClose),
            minuteVolume = VALUES(minuteVolume)
        """
        params_list = [
            (p.datetime, p.open, p.high, p.low, p.close, p.volume)
            for p in points
        ]
        affected = db.executemany(insert_sql, params_list)
        result["upserted"] = len(params_list)

        logger.info(
            "%s: fetched %d bars (%s .. %s), upserted %d (affected %d)",
            symbol, len(points), result["earliest"], result["latest"],
            result["upserted"], affected,
        )

    except Exception as e:
        # Let rate-limit errors propagate so the caller's retry loop
        # can sleep and retry the same symbol.
        if is_rate_limit_error(e):
            raise
        result["error"] = str(e)
        logger.error("%s: catch-up failed — %s", symbol, e)

    return result


def run_catch_up(symbols: list, start_date_override: str | None,
                 end_date: str, dry_run: bool, rpm: int):
    """Main driver: iterate symbols with rate limiting and retry."""
    from ..config import load_config
    from ..db import get_db_manager
    from ..twelve_data import TwelveDataClient
    from ..symbols import normalize_table_name

    config = load_config()
    db = get_db_manager()
    api_client = TwelveDataClient(config.api)
    limiter = RateLimiter(rpm)

    est_minutes = len(symbols) * 60.0 / rpm / 60.0
    print(f"\nIntraday catch-up: {len(symbols)} symbol(s), end_date={end_date}")
    print(f"Rate limit: {rpm} req/min (estimated ~{est_minutes:.0f} min)")
    if dry_run:
        print("[DRY RUN — no API calls or writes]\n")
    else:
        print()

    results = []

    for i, symbol in enumerate(symbols, 1):
        table_name = normalize_table_name(symbol)

        # Determine start_date for this symbol
        if start_date_override:
            start_date = start_date_override
        else:
            latest = get_latest_timepoint(db, table_name)
            if latest:
                # Start 1 minute after the latest existing row to avoid
                # re-fetching a bar we already have (harmless but wasteful).
                try:
                    dt = datetime.strptime(latest, "%Y-%m-%d %H:%M:%S")
                    dt += timedelta(minutes=1)
                    start_date = dt.strftime("%Y-%m-%d %H:%M:%S")
                except ValueError:
                    start_date = latest
                logger.info(
                    "%s: latest DB timePoint = %s, will fetch from %s",
                    symbol, latest, start_date,
                )
            else:
                # No data at all — default to 30 days ago
                fallback = datetime.now() - timedelta(days=30)
                start_date = fallback.strftime("%Y-%m-%d 09:30:00")
                logger.warning(
                    "%s: table `%s` is empty (no existing timePoint). "
                    "Falling back to last 30 days: start_date=%s",
                    symbol, table_name, start_date,
                )

        # Rate limiting and retry loop
        r = None
        for attempt in range(1, MAX_RETRIES + 1):
            if not dry_run:
                limiter.acquire()

            try:
                r = catch_up_symbol(
                    api_client, db, symbol, table_name,
                    start_date, end_date, dry_run,
                )
                break
            except Exception as e:
                if is_rate_limit_error(e) and attempt < MAX_RETRIES:
                    wait = 60.0 + RATE_LIMIT_MARGIN
                    logger.warning(
                        "%s: rate-limited by provider (attempt %d/%d). "
                        "Sleeping %.0fs for rolling window to reset — %s",
                        symbol, attempt, MAX_RETRIES, wait, e,
                    )
                    time.sleep(wait)
                    limiter.clear()
                    continue
                else:
                    logger.error(
                        "%s: failed after %d attempt(s) — %s",
                        symbol, attempt, e,
                    )
                    r = {
                        "symbol": symbol, "table": table_name,
                        "fetched": 0, "upserted": 0,
                        "earliest": None, "latest": None,
                        "error": str(e),
                    }
                    break

        # Progress output
        prefix = f"[{i}/{len(symbols)}] {symbol}"
        if r["error"]:
            print(f"{prefix} ERROR: {r['error']}")
        elif dry_run:
            print(f"{prefix} (dry run)")
        elif r["fetched"] == 0:
            print(f"{prefix} — no data returned")
        else:
            print(f"{prefix} OK: {r['fetched']} fetched, "
                  f"{r['upserted']} upserted "
                  f"({r['earliest']} .. {r['latest']})")

        results.append(r)

    # Summary
    succeeded = [r for r in results if r["error"] is None]
    failed = [r for r in results if r["error"] is not None]
    total_fetched = sum(r["fetched"] for r in results)
    total_upserted = sum(r["upserted"] for r in results)

    print(f"\n{'=' * 60}")
    print(f"Catch-up {'(dry run) ' if dry_run else ''}complete.")
    print(f"  Symbols:  {len(succeeded)} succeeded, {len(failed)} failed")
    print(f"  Bars:     {total_fetched} fetched, {total_upserted} upserted")
    if failed:
        print(f"  Failed:   {', '.join(r['symbol'] for r in failed)}")
    print(f"{'=' * 60}\n")


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Catch up missing intraday 1-minute bars."
    )
    parser.add_argument(
        "--symbol", action="append", dest="symbols",
        help="Symbol to catch up (repeatable). Use --all-symbols for everything.",
    )
    parser.add_argument(
        "--all-symbols", action="store_true",
        help="Catch up all symbols tracked by the ingestion system.",
    )
    parser.add_argument(
        "--start-date",
        help="Explicit start date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS). "
             "Overrides automatic detection from DB.",
    )
    parser.add_argument(
        "--end-date",
        help="End date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS). "
             "Default: today 16:00:00.",
    )
    parser.add_argument(
        "--batch-size", type=int, default=None,
        help="Process symbols in batches of this size. Requires --batch-index.",
    )
    parser.add_argument(
        "--batch-index", type=int, default=None,
        help="Zero-based batch number to process (0 = first batch).",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview what would be fetched without calling the API.",
    )
    parser.add_argument(
        "--rpm", type=int, default=DEFAULT_RPM,
        help=f"Max API requests per minute (default: {DEFAULT_RPM}).",
    )
    args = parser.parse_args()

    if args.rpm < 1:
        parser.error("--rpm must be at least 1.")

    if not args.symbols and not args.all_symbols:
        parser.error("Provide --symbol or --all-symbols.")

    if args.all_symbols and args.symbols:
        parser.error("--all-symbols and --symbol are mutually exclusive.")

    # Validate batch flags: must both be present or both absent
    if (args.batch_size is None) != (args.batch_index is None):
        parser.error("--batch-size and --batch-index must be used together.")

    if args.batch_size is not None and args.batch_size < 1:
        parser.error("--batch-size must be at least 1.")

    if args.batch_index is not None and args.batch_index < 0:
        parser.error("--batch-index must be >= 0.")

    # Resolve symbol list
    if args.all_symbols:
        from ..symbols import load_symbols
        symbols = load_symbols()
    else:
        symbols = [s.upper() for s in args.symbols]

    # Apply batch slicing
    if args.batch_size is not None:
        total = len(symbols)
        start = args.batch_index * args.batch_size
        if start >= total:
            print(f"Batch index {args.batch_index} is past the end "
                  f"({total} symbols, batch size {args.batch_size}, "
                  f"max index {(total - 1) // args.batch_size}). Nothing to do.")
            sys.exit(0)
        end = min(start + args.batch_size, total)
        symbols = symbols[start:end]
        print(f"Batch {args.batch_index}: symbols[{start}:{end}] "
              f"({len(symbols)} of {total} total)")

    # Resolve end_date
    if args.end_date:
        end_date = args.end_date
    else:
        end_date = datetime.now().strftime("%Y-%m-%d") + " 16:00:00"

    # start_date_override is None when we want auto-detect from DB
    start_date_override = args.start_date

    run_catch_up(symbols, start_date_override, end_date, args.dry_run, args.rpm)


if __name__ == "__main__":
    main()
