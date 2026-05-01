"""
Daily returns job (Phase 1 shared returns layer).

Reads close-to-close prices from everydayAfterClose and writes per-symbol
daily returns into daily_returns.  No external API calls — purely a
local database transform.

Behavior:
    - One row per (symbol, trade_date) except the first observed row
      per symbol (no previous close).
    - simple_return = close / prev_close - 1
    - log_return    = ln(close / prev_close)
    - Rows with a missing or non-positive close are skipped and break
      the return chain (the next valid bar is also skipped because its
      prev_close would be invalid).
    - Idempotent upsert via INSERT ... ON DUPLICATE KEY UPDATE on the
      (symbol, trade_date) unique key.

CLI:
    python -m python_ingestion.jobs.daily_returns [options]

Options:
    --symbol SYM             Symbol to process (repeatable).
    --all-symbols            Process every distinct symbol in everydayAfterClose.
    --start-date YYYY-MM-DD  Optional lower bound on trade_date (inclusive).
    --end-date   YYYY-MM-DD  Optional upper bound on trade_date (inclusive).
    --dry-run                Compute and log counts without writing.

Default scope:
    If neither --symbol nor --all-symbols is given, the job processes
    PIPELINE_SYMBOLS from python_ingestion/config.py.  This matches the
    convention used by quarterly_snapshot.py, earnings_commentary.py,
    company_news.py, and the other scheduler-friendly jobs in jobs/.
"""
import argparse
import logging
from datetime import date, datetime
from typing import List, Optional, Sequence, Tuple

from ..analytics.returns import (
    DailyReturnRow,
    compute_returns_for_symbol,
    count_invalid_bars,
)
from ..config import PIPELINE_SYMBOLS
from ..db import get_db_manager

logger = logging.getLogger(__name__)


_UPSERT_SQL = """
INSERT INTO daily_returns (
    symbol, trade_date, prev_close, close, log_return, simple_return
) VALUES (%s, %s, %s, %s, %s, %s)
ON DUPLICATE KEY UPDATE
    prev_close = VALUES(prev_close),
    close = VALUES(close),
    log_return = VALUES(log_return),
    simple_return = VALUES(simple_return)
"""


def _select_bars(db, symbol: str,
                 start_date: Optional[str],
                 end_date: Optional[str]) -> List[Tuple[date, object]]:
    """
    Read (trade_date, close) tuples from everydayAfterClose for a symbol.

    Notes:
        - everydayAfterClose.datetime is VARCHAR; DATE() extracts the
          calendar date.
        - If multiple rows exist for the same (symbol, calendar_date)
          (e.g. an intraday refresh wrote two rows with different
          time-of-day suffixes), the row with the lexicographically
          largest datetime VARCHAR wins — i.e. the latest reported
          close for that day.
    """
    where = ["symbol = %s"]
    params: list = [symbol]
    if start_date:
        where.append("DATE(datetime) >= %s")
        params.append(start_date)
    if end_date:
        where.append("DATE(datetime) <= %s")
        params.append(end_date)

    sql = (
        "SELECT DATE(datetime) AS trade_date, close, datetime "
        "FROM everydayAfterClose "
        f"WHERE {' AND '.join(where)} "
        "ORDER BY datetime ASC"
    )
    rows = db.execute(sql, tuple(params)) or []

    # Dedupe by trade_date keeping the latest dt string (input is sorted asc).
    by_date: dict = {}
    for trade_date, close, _dt in rows:
        by_date[trade_date] = close
    return sorted(by_date.items(), key=lambda x: x[0])


def _list_all_symbols(db) -> List[str]:
    rows = db.execute(
        "SELECT DISTINCT symbol FROM everydayAfterClose ORDER BY symbol"
    ) or []
    return [r[0] for r in rows]


def _persist(db, rows: Sequence[DailyReturnRow]) -> int:
    if not rows:
        return 0
    params = [
        (r.symbol, r.trade_date, r.prev_close, r.close,
         r.log_return, r.simple_return)
        for r in rows
    ]
    return db.executemany(_UPSERT_SQL, params)


def run_for_symbols(symbols: Sequence[str],
                    start_date: Optional[str] = None,
                    end_date: Optional[str] = None,
                    dry_run: bool = False) -> dict:
    """
    Compute and persist daily returns for each symbol.

    Returns:
        dict mapping symbol -> {bars, computed, written, invalid_close}.
    """
    db = get_db_manager()
    db.ensure_daily_returns_table()

    summary: dict = {}

    for i, symbol in enumerate(symbols, 1):
        bars = _select_bars(db, symbol, start_date, end_date)
        n_bars = len(bars)
        n_invalid = count_invalid_bars(bars)

        rows = compute_returns_for_symbol(symbol, bars)
        n_computed = len(rows)

        if dry_run:
            written = 0
            logger.info(
                "[DRY RUN] %s: %d bars in window, %d invalid close, "
                "%d return rows would be written",
                symbol, n_bars, n_invalid, n_computed,
            )
        else:
            written = _persist(db, rows)
            logger.info(
                "%s: %d bars in window, %d invalid close, "
                "%d return rows written (rowcount=%d)",
                symbol, n_bars, n_invalid, n_computed, written,
            )

        summary[symbol] = {
            "bars": n_bars,
            "computed": n_computed,
            "written": written,
            "invalid_close": n_invalid,
        }

        if i % 50 == 0:
            logger.info("Progress: %d / %d symbols processed", i, len(symbols))

    return summary


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Compute and persist daily close-to-close returns into daily_returns."
    )
    parser.add_argument(
        "--symbol", action="append", dest="symbols",
        help="Symbol to process (repeatable). Use --all-symbols for everything.",
    )
    parser.add_argument(
        "--all-symbols", action="store_true",
        help="Process every distinct symbol present in everydayAfterClose.",
    )
    parser.add_argument(
        "--start-date",
        help="Optional lower bound on trade_date (yyyy-mm-dd, inclusive).",
    )
    parser.add_argument(
        "--end-date",
        help="Optional upper bound on trade_date (yyyy-mm-dd, inclusive).",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Compute and log counts without writing.",
    )
    args = parser.parse_args()

    db = get_db_manager()

    if args.all_symbols:
        symbols = _list_all_symbols(db)
    elif args.symbols:
        symbols = [s.upper() for s in args.symbols]
    else:
        symbols = list(PIPELINE_SYMBOLS)
        logger.info(
            "No --symbol or --all-symbols given; defaulting to PIPELINE_SYMBOLS=%s",
            symbols,
        )

    if not symbols:
        parser.error("No symbols to process.")

    for label, val in (("--start-date", args.start_date),
                       ("--end-date", args.end_date)):
        if val:
            try:
                datetime.strptime(val, "%Y-%m-%d")
            except ValueError:
                parser.error(f"{label} must be yyyy-mm-dd, got {val!r}")

    summary = run_for_symbols(
        symbols=symbols,
        start_date=args.start_date,
        end_date=args.end_date,
        dry_run=args.dry_run,
    )

    total_bars = sum(s["bars"] for s in summary.values())
    total_computed = sum(s["computed"] for s in summary.values())
    total_written = sum(s["written"] for s in summary.values())
    total_invalid = sum(s["invalid_close"] for s in summary.values())

    print(f"\n{'=' * 55}")
    print(f"daily_returns {'(dry run) ' if args.dry_run else ''}complete.")
    print(f"  Symbols:          {len(summary)}")
    print(f"  Bars read:        {total_bars}")
    print(f"  Invalid close:    {total_invalid}")
    print(f"  Returns computed: {total_computed}")
    if not args.dry_run:
        print(f"  Rowcount written: {total_written}")
    print(f"{'=' * 55}\n")


if __name__ == "__main__":
    main()
