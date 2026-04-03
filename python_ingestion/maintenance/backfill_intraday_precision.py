"""
Backfill intraday minute bars to restore decimal precision.

Background:
    Migration 001 converted per-symbol intraday table columns from INT to
    DECIMAL(18,4), but existing rows still contain truncated integer prices
    (e.g. 253.0000 instead of 253.1400).  This script re-fetches recent
    intraday data from the TwelveData API and upserts it, replacing the
    truncated values with full-precision floats.

    AAPL was already re-ingested via refresh_all.py.  This script handles
    every other symbol.

Modes:
    selective (default) — scan for tables whose recent 50 rows are ALL
        integer-valued, then backfill only those.  Fast but can miss
        partially-affected tables (see "Why scan misses mixed tables"
        below).

    --symbol SYM — backfill specific symbols unconditionally (no scan).

    --all — force-refresh ALL tracked symbols unconditionally.  Ignores
        scan results entirely.  Use this when you suspect partial-window
        issues that the heuristic cannot detect.

    --scan-only — report which tables look affected, then exit.

Why scan misses mixed-state tables:
    The scan heuristic samples the 50 most recent rows and flags a table
    only when EVERY sampled row has integer-valued prices.  This works for
    tables that were never re-ingested at all, but misses tables where:
      - The scheduler has already refreshed the most recent 1-2 days with
        decimal data (so the newest 50 rows look fine), while older rows
        within the 1W window still contain truncated integers.
      - A symbol was partially backfilled or had a mix of legacy and fresh
        data from different ingestion runs.
    In these cases the 1W chart still renders flat/staircase segments for
    the older portion, but --scan-only reports "all data looks fine".
    Use --all to unconditionally refresh every symbol and eliminate these
    partial-window gaps.

Rate limiting:
    TwelveData free-tier accounts are limited to 8 API credits per minute.
    This script enforces that limit proactively with a sliding-window
    rate limiter (configurable via --rpm).  If the API still returns a
    rate-limit error despite the limiter, the script detects it, waits
    for the next safe window, and retries the same symbol (up to 3 times).

Resume support:
    Long runs (e.g. --all with 505 symbols) can be resumed after
    interruption using --start-from SYMBOL.  The script skips all symbols
    before the named one and continues from there.

Usage:
    # Scan only — report tables with integer-only prices
    python -m python_ingestion.maintenance.backfill_intraday_precision --scan-only

    # Selective backfill — scan-detected symbols, last 10 days (default)
    python -m python_ingestion.maintenance.backfill_intraday_precision

    # Selective backfill with longer window
    python -m python_ingestion.maintenance.backfill_intraday_precision --days 15

    # Specific symbols
    python -m python_ingestion.maintenance.backfill_intraday_precision \\
        --symbol AMZN --days 15

    # Force-refresh ALL tracked symbols (safe for free-tier)
    python -m python_ingestion.maintenance.backfill_intraday_precision --all --days 15

    # Force-refresh ALL with dry run (no API calls or writes)
    python -m python_ingestion.maintenance.backfill_intraday_precision --all --dry-run

    # Resume a previously interrupted --all run from GOOGL onward
    python -m python_ingestion.maintenance.backfill_intraday_precision \\
        --all --days 15 --start-from GOOGL

    # Use a slower rate for very restricted accounts (5 req/min)
    python -m python_ingestion.maintenance.backfill_intraday_precision \\
        --all --days 15 --rpm 5
"""
import argparse
import logging
import time
from collections import deque
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Default TwelveData free-tier credit limit
DEFAULT_RPM = 8

# Maximum retries per symbol when rate-limited
MAX_RETRIES = 3

# Extra safety margin added to the sleep when waiting for rate-limit window (seconds)
RATE_LIMIT_MARGIN = 2.0


class RateLimiter:
    """
    Sliding-window rate limiter.

    Tracks timestamps of the last N requests within a 60-second window.
    Before each request, if the window is full, sleeps until the oldest
    request falls outside the window.
    """

    def __init__(self, max_per_minute: int):
        self.max_per_minute = max_per_minute
        self.window = 60.0  # seconds
        self.timestamps = deque()

    def wait_if_needed(self):
        """Block until it is safe to make the next request."""
        now = time.monotonic()

        # Evict timestamps older than the window
        while self.timestamps and (now - self.timestamps[0]) >= self.window:
            self.timestamps.popleft()

        if len(self.timestamps) >= self.max_per_minute:
            # Must wait until the oldest timestamp exits the window
            oldest = self.timestamps[0]
            sleep_for = (oldest + self.window) - now + RATE_LIMIT_MARGIN
            if sleep_for > 0:
                logger.info(
                    "Rate limiter: %d/%d credits used in window, "
                    "sleeping %.1fs",
                    len(self.timestamps), self.max_per_minute, sleep_for,
                )
                time.sleep(sleep_for)

            # Evict again after sleeping
            now = time.monotonic()
            while self.timestamps and (now - self.timestamps[0]) >= self.window:
                self.timestamps.popleft()

    def record(self):
        """Record that a request was just made."""
        self.timestamps.append(time.monotonic())


def is_rate_limit_error(exc: Exception) -> bool:
    """Return True if the exception indicates a TwelveData rate-limit / credit error."""
    msg = str(exc).lower()
    # TwelveData signals: JSON code 429, or message mentioning rate/credit/quota
    return (
        "429" in msg
        or "rate" in msg
        or "credit" in msg
        or "too many" in msg
        or "quota" in msg
    )


def find_tables_with_integer_data(db) -> list:
    """
    Find intraday tables that still contain truncated integer prices.

    A price is considered truncated if its fractional part is exactly zero.
    We check a sample of recent rows — if ALL sampled prices have .0000
    fractional parts, the table likely needs backfill.

    NOTE: This heuristic misses partially-affected tables where recent rows
    have decimal precision but older rows within the 1W window are still
    truncated integers.  Use --all for unconditional refresh.

    Returns list of (table_name, sample_count) tuples.
    """
    all_rows = db.execute(
        """
        SELECT DISTINCT TABLE_NAME
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = %s
          AND COLUMN_NAME = 'minuteOpen'
          AND DATA_TYPE = 'decimal'
        ORDER BY TABLE_NAME
        """,
        (db.config.database,),
    ) or []

    affected = []
    for (table_name,) in all_rows:
        rows = db.execute(
            f"""
            SELECT COUNT(*) AS total,
                   SUM(CASE WHEN minuteOpen = FLOOR(minuteOpen)
                             AND minuteHigh = FLOOR(minuteHigh)
                             AND minuteLow = FLOOR(minuteLow)
                             AND minuteClose = FLOOR(minuteClose) THEN 1 ELSE 0 END) AS int_count
            FROM (
                SELECT minuteOpen, minuteHigh, minuteLow, minuteClose
                FROM `{table_name}`
                ORDER BY timePoint DESC
                LIMIT 50
            ) sample
            """
        )
        if rows and rows[0][0] and rows[0][0] > 0:
            total, int_count = rows[0]
            if int_count == total:
                affected.append((table_name, total))

    return affected


def backfill_symbol(api_client, db, symbol: str, table_name: str,
                    start_date: str, end_date: str, dry_run: bool) -> str:
    """
    Re-ingest intraday data for one symbol.

    Returns "ok", "empty", or "error".
    Raises ValueError/requests.RequestException on rate-limit errors
    (caller handles retry).
    """
    if dry_run:
        logger.info("[DRY RUN] Would backfill %s (%s) from %s to %s",
                     symbol, table_name, start_date, end_date)
        return "ok"

    # Ensure table schema is up to date (this is a local DB call, no API)
    db.ensure_intraday_table(symbol, table_name)

    # This call hits the TwelveData API — may raise on rate limit
    data_points = api_client.get_time_series_range(
        symbol=symbol,
        interval="1min",
        start_date=start_date,
        end_date=end_date,
    )

    if not data_points:
        logger.warning("%s: no data returned from API", symbol)
        return "empty"

    data_points.sort(key=lambda x: x.datetime)

    insert_sql = f"""
    INSERT INTO `{table_name}` (timePoint, minuteOpen, minuteHigh, minuteLow, minuteClose, minuteVolume)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        minuteOpen = VALUES(minuteOpen),
        minuteHigh = VALUES(minuteHigh),
        minuteLow = VALUES(minuteLow),
        minuteClose = VALUES(minuteClose),
        minuteVolume = VALUES(minuteVolume)
    """
    params_list = [
        (p.datetime, p.open, p.high, p.low, p.close, p.volume)
        for p in data_points
    ]
    affected = db.executemany(insert_sql, params_list)
    logger.info("%s: upserted %d bars (%d affected)", symbol, len(params_list), affected)
    return "ok"


def run_backfill(symbols: list, days: int, dry_run: bool, mode_label: str,
                 rpm: int):
    """Run the backfill for the given symbols with rate limiting and retry."""
    from python_ingestion.db import get_db_manager
    from python_ingestion.twelve_data import TwelveDataClient
    from python_ingestion.config import load_config
    from python_ingestion.symbols import normalize_table_name

    config = load_config()
    db = get_db_manager()
    api_client = TwelveDataClient(config.api)
    limiter = RateLimiter(rpm)

    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=days)
    start_date = start_dt.strftime("%Y-%m-%d 09:30:00")
    end_date = end_dt.strftime("%Y-%m-%d 16:00:00")

    print(f"\nMode: {mode_label}")
    print(f"Symbols: {len(symbols)}")
    print(f"Window: {start_date} to {end_date} ({days} days)")
    print(f"Rate limit: {rpm} requests/minute")
    if dry_run:
        print("DRY RUN — no API calls or database writes\n")
    else:
        est_minutes = len(symbols) * 60.0 / rpm / 60.0
        print(f"Estimated time: ~{est_minutes:.0f} minutes\n")

    results = {"ok": 0, "empty": 0, "error": 0}

    for i, sym in enumerate(symbols):
        table_name = normalize_table_name(sym)
        prefix = f"[{i + 1}/{len(symbols)}] {sym}"

        status = None
        for attempt in range(1, MAX_RETRIES + 1):
            # Proactive rate limiting (no-op for dry runs)
            if not dry_run:
                limiter.wait_if_needed()

            try:
                status = backfill_symbol(
                    api_client, db, sym, table_name,
                    start_date, end_date, dry_run,
                )
                if not dry_run:
                    limiter.record()
                break  # success — no retry needed

            except Exception as e:
                if not dry_run:
                    limiter.record()

                if is_rate_limit_error(e) and attempt < MAX_RETRIES:
                    wait = 60.0 + RATE_LIMIT_MARGIN
                    logger.warning(
                        "%s: rate-limited (attempt %d/%d), "
                        "waiting %.0fs before retry — %s",
                        prefix, attempt, MAX_RETRIES, wait, e,
                    )
                    time.sleep(wait)
                    # Clear the limiter window after a forced wait —
                    # we just slept a full minute so all old credits expired
                    limiter.timestamps.clear()
                    continue
                else:
                    logger.error("%s: failed — %s", prefix, e)
                    status = "error"
                    break

        results[status] = results.get(status, 0) + 1

        if status == "ok":
            logger.info("%s: done", prefix)
        elif status == "empty":
            logger.info("%s: no data from API", prefix)

        if (i + 1) % 25 == 0 or (i + 1) == len(symbols):
            ok, empty, err = results["ok"], results["empty"], results["error"]
            print(f"  Progress: {i + 1}/{len(symbols)}  "
                  f"(ok={ok} empty={empty} error={err})")

    print(f"\nBackfill {'(dry run) ' if dry_run else ''}complete.")
    print(f"  OK: {results['ok']}  Empty: {results['empty']}  "
          f"Errors: {results['error']}")

    if results["error"] > 0:
        print(f"\n  Tip: re-run with --start-from <SYMBOL> to resume "
              f"from the first failure,")
        print(f"  or with --symbol <SYM> to retry specific symbols.")


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Backfill intraday minute bars to restore decimal precision."
    )
    parser.add_argument(
        "--symbol", action="append", dest="symbols",
        help="Symbol to backfill (repeatable). Skips scan, backfills only these.",
    )
    parser.add_argument(
        "--all", action="store_true", dest="force_all",
        help="Force-refresh ALL tracked symbols unconditionally (ignores scan).",
    )
    parser.add_argument(
        "--days", type=int, default=10,
        help="Number of calendar days to backfill (default: 10, covers 1W chart).",
    )
    parser.add_argument(
        "--rpm", type=int, default=DEFAULT_RPM,
        help=f"Max API requests per minute (default: {DEFAULT_RPM}).",
    )
    parser.add_argument(
        "--start-from", dest="start_from", metavar="SYMBOL",
        help="Skip symbols before this one (for resuming interrupted runs).",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Report what would change without making API calls or writes.",
    )
    parser.add_argument(
        "--scan-only", action="store_true",
        help="Only scan for tables with integer data; do not backfill.",
    )
    args = parser.parse_args()

    # Validation
    if args.force_all and args.symbols:
        parser.error("--all and --symbol are mutually exclusive. "
                     "Use --all for every symbol, or --symbol for specific ones.")

    if args.rpm < 1:
        parser.error("--rpm must be at least 1.")

    from python_ingestion.symbols import SYMBOL_LIST, normalize_table_name

    # --- Mode: scan-only ---
    if args.scan_only:
        from python_ingestion.db import get_db_manager
        db = get_db_manager()
        affected = find_tables_with_integer_data(db)
        if affected:
            print(f"\nFound {len(affected)} table(s) with integer-only prices:")
            for tbl, cnt in affected:
                print(f"  {tbl} ({cnt} sampled rows)")
        else:
            print("\nNo tables with integer-only prices found. All data looks fine.")
        print(f"\nNote: scan only detects tables where ALL recent rows are "
              f"integer-valued.")
        print(f"Tables with mixed data (some decimal, some integer) are not "
              f"flagged.")
        print(f"Use --all to force-refresh every symbol unconditionally.")
        return

    # --- Resolve symbol list based on mode ---
    if args.force_all:
        symbols = list(SYMBOL_LIST)
        mode_label = "force-all"
    elif args.symbols:
        symbols = list(args.symbols)
        mode_label = "symbol-specific"
    else:
        # Selective: scan then backfill detected tables
        from python_ingestion.db import get_db_manager
        db = get_db_manager()
        affected = find_tables_with_integer_data(db)
        if affected:
            print(f"\nFound {len(affected)} table(s) with integer-only prices:")
            for tbl, cnt in affected:
                print(f"  {tbl} ({cnt} sampled rows)")
        else:
            print("\nNo tables with integer-only prices found. All data looks "
                  "fine.")
            print("Tip: use --all to force-refresh every symbol regardless of "
                  "scan results.")
            return

        table_to_symbol = {normalize_table_name(s): s for s in SYMBOL_LIST}
        symbols = [table_to_symbol.get(tbl, tbl) for tbl, _ in affected]
        if not symbols:
            print("Nothing to backfill.")
            return
        mode_label = "selective (scan-detected)"

    # --- Apply --start-from if provided ---
    if args.start_from:
        target = args.start_from.upper()
        try:
            idx = next(
                i for i, s in enumerate(symbols)
                if s.upper() == target
            )
        except StopIteration:
            parser.error(
                f"--start-from symbol '{args.start_from}' not found in the "
                f"target list ({len(symbols)} symbols). Check spelling."
            )
            return  # unreachable, but keeps linters happy

        skipped = symbols[:idx]
        symbols = symbols[idx:]
        print(f"\nResuming from {target} (skipping {len(skipped)} symbols)")
        mode_label += f", resumed from {target}"

    run_backfill(symbols, args.days, args.dry_run, mode_label, args.rpm)


if __name__ == "__main__":
    main()
