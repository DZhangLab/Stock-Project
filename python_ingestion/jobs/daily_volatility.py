"""
Daily volatility job (Phase 2 MVP).

Reads daily log returns from daily_returns and close prices from
everydayAfterClose, then writes per-symbol per-day realized volatility
metrics, a tercile regime label, a descriptive ±1-sigma close envelope,
and a trailing-90d empirical band hit-rate into daily_volatility.

This job is purely a local database transform — no external API calls.

Phase scope:
    - har_rv_forecast_1d and har_rv_model_version are NEVER written by
      this job; they remain NULL and are populated later by Phase 3.
    - Realized vol uses sample stdev of log returns annualized by
      sqrt(252).  See analytics/volatility.py for the rules.

CLI:
    python -m python_ingestion.jobs.daily_volatility [options]

Options:
    --symbol SYM             Symbol to process (repeatable).
    --all-symbols            Process every distinct symbol in daily_returns.
    --start-date YYYY-MM-DD  Optional lower bound on as_of_date written
                             (computation always uses full history).
    --end-date   YYYY-MM-DD  Optional upper bound on as_of_date written.
    --dry-run                Compute and log counts without writing.

Default scope:
    If neither --symbol nor --all-symbols is given, the job processes
    PIPELINE_SYMBOLS from python_ingestion/config.py.  This matches the
    convention used by the other scheduler-friendly jobs in jobs/.
"""
import argparse
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Optional, Sequence, Tuple

from ..analytics.volatility import (
    DailyVolatilityRow,
    compute_for_symbol,
)
from ..config import PIPELINE_SYMBOLS
from ..db import get_db_manager

logger = logging.getLogger(__name__)


_UPSERT_SQL = """
INSERT INTO daily_volatility (
    symbol, as_of_date,
    realized_vol_5d, realized_vol_21d, realized_vol_63d,
    volatility_regime, vol_band_low, vol_band_high,
    band_hit_rate_trailing_90d,
    har_rv_forecast_1d, har_rv_model_version,
    computed_at
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, NULL, NULL, %s
)
ON DUPLICATE KEY UPDATE
    realized_vol_5d = VALUES(realized_vol_5d),
    realized_vol_21d = VALUES(realized_vol_21d),
    realized_vol_63d = VALUES(realized_vol_63d),
    volatility_regime = VALUES(volatility_regime),
    vol_band_low = VALUES(vol_band_low),
    vol_band_high = VALUES(vol_band_high),
    band_hit_rate_trailing_90d = VALUES(band_hit_rate_trailing_90d),
    computed_at = VALUES(computed_at)
"""


def _select_returns(db, symbol: str) -> List[Tuple[date, float]]:
    """Read all (trade_date, log_return) rows for a symbol from daily_returns."""
    rows = db.execute(
        "SELECT trade_date, log_return FROM daily_returns "
        "WHERE symbol = %s ORDER BY trade_date ASC",
        (symbol,),
    ) or []
    return [(r[0], float(r[1])) for r in rows]


def _select_closes(db, symbol: str) -> Dict[date, Decimal]:
    """
    Read close prices from everydayAfterClose for a symbol.
    Cross-table queries against everydayAfterClose use COLLATE because
    that table's symbol column uses utf8mb4_0900_ai_ci while ours use
    utf8mb4_unicode_ci.
    """
    rows = db.execute(
        "SELECT DATE(datetime) AS trade_date, close, datetime "
        "FROM everydayAfterClose "
        "WHERE symbol COLLATE utf8mb4_unicode_ci = %s COLLATE utf8mb4_unicode_ci "
        "ORDER BY datetime ASC",
        (symbol,),
    ) or []
    out: Dict[date, Decimal] = {}
    for trade_date, close, _dt in rows:
        if close is None:
            continue
        try:
            out[trade_date] = Decimal(str(close))
        except Exception:
            continue
    return out


def _list_all_symbols(db) -> List[str]:
    rows = db.execute(
        "SELECT DISTINCT symbol FROM daily_returns ORDER BY symbol"
    ) or []
    return [r[0] for r in rows]


def _filter_by_date_range(rows: Sequence[DailyVolatilityRow],
                          start_date: Optional[date],
                          end_date: Optional[date]) -> List[DailyVolatilityRow]:
    if not start_date and not end_date:
        return list(rows)
    out = []
    for r in rows:
        if start_date and r.as_of_date < start_date:
            continue
        if end_date and r.as_of_date > end_date:
            continue
        out.append(r)
    return out


def _persist(db, rows: Sequence[DailyVolatilityRow]) -> int:
    if not rows:
        return 0
    now = datetime.now()
    params = [
        (r.symbol, r.as_of_date,
         r.realized_vol_5d, r.realized_vol_21d, r.realized_vol_63d,
         r.volatility_regime, r.vol_band_low, r.vol_band_high,
         r.band_hit_rate_trailing_90d,
         now)
        for r in rows
    ]
    return db.executemany(_UPSERT_SQL, params)


def run_for_symbols(symbols: Sequence[str],
                    start_date: Optional[date] = None,
                    end_date: Optional[date] = None,
                    dry_run: bool = False) -> dict:
    db = get_db_manager()
    db.ensure_daily_volatility_table()

    summary: dict = {}

    for i, symbol in enumerate(symbols, 1):
        returns = _select_returns(db, symbol)
        n_returns = len(returns)
        if n_returns == 0:
            logger.info("%s: 0 returns, skipping (no daily_returns rows)", symbol)
            summary[symbol] = {
                "returns": 0, "computed": 0, "written": 0,
                "rv5_non_null": 0, "rv21_non_null": 0, "rv63_non_null": 0,
                "regime_non_null": 0, "band_non_null": 0, "hit_rate_non_null": 0,
            }
            continue

        closes = _select_closes(db, symbol)
        rows = compute_for_symbol(symbol, returns, closes)

        # Counters before date filtering, so we can report what the
        # full computation produced (the date filter only narrows what
        # we write, not what we compute).
        rv5_n = sum(1 for r in rows if r.realized_vol_5d is not None)
        rv21_n = sum(1 for r in rows if r.realized_vol_21d is not None)
        rv63_n = sum(1 for r in rows if r.realized_vol_63d is not None)
        regime_n = sum(1 for r in rows if r.volatility_regime is not None)
        band_n = sum(1 for r in rows if r.vol_band_low is not None)
        hit_n = sum(1 for r in rows if r.band_hit_rate_trailing_90d is not None)

        write_rows = _filter_by_date_range(rows, start_date, end_date)
        n_computed = len(write_rows)

        if dry_run:
            written = 0
            logger.info(
                "[DRY RUN] %s: %d returns, %d output rows would be written "
                "(rv5=%d, rv21=%d, rv63=%d, regime=%d, band=%d, hit_rate=%d non-null)",
                symbol, n_returns, n_computed,
                rv5_n, rv21_n, rv63_n, regime_n, band_n, hit_n,
            )
        else:
            written = _persist(db, write_rows)
            logger.info(
                "%s: %d returns, %d rows written (rowcount=%d) "
                "(rv5=%d, rv21=%d, rv63=%d, regime=%d, band=%d, hit_rate=%d non-null)",
                symbol, n_returns, n_computed, written,
                rv5_n, rv21_n, rv63_n, regime_n, band_n, hit_n,
            )

        summary[symbol] = {
            "returns": n_returns,
            "computed": n_computed,
            "written": written,
            "rv5_non_null": rv5_n,
            "rv21_non_null": rv21_n,
            "rv63_non_null": rv63_n,
            "regime_non_null": regime_n,
            "band_non_null": band_n,
            "hit_rate_non_null": hit_n,
        }

        if i % 50 == 0:
            logger.info("Progress: %d / %d symbols processed", i, len(symbols))

    return summary


def _parse_date_arg(label: str, value: Optional[str]) -> Optional[date]:
    if value is None:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise SystemExit(f"{label} must be yyyy-mm-dd, got {value!r}")


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    parser = argparse.ArgumentParser(
        description=(
            "Compute and persist daily realized-volatility metrics, regime, "
            "and ±1-sigma envelope into daily_volatility."
        )
    )
    parser.add_argument(
        "--symbol", action="append", dest="symbols",
        help="Symbol to process (repeatable). Use --all-symbols for everything.",
    )
    parser.add_argument(
        "--all-symbols", action="store_true",
        help="Process every distinct symbol present in daily_returns.",
    )
    parser.add_argument(
        "--start-date",
        help="Optional lower bound on as_of_date (yyyy-mm-dd, inclusive).",
    )
    parser.add_argument(
        "--end-date",
        help="Optional upper bound on as_of_date (yyyy-mm-dd, inclusive).",
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

    start_date = _parse_date_arg("--start-date", args.start_date)
    end_date = _parse_date_arg("--end-date", args.end_date)

    summary = run_for_symbols(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        dry_run=args.dry_run,
    )

    total_returns = sum(s["returns"] for s in summary.values())
    total_written = sum(s["written"] for s in summary.values())
    total_computed = sum(s["computed"] for s in summary.values())
    total_rv5 = sum(s["rv5_non_null"] for s in summary.values())
    total_rv21 = sum(s["rv21_non_null"] for s in summary.values())
    total_rv63 = sum(s["rv63_non_null"] for s in summary.values())
    total_regime = sum(s["regime_non_null"] for s in summary.values())
    total_band = sum(s["band_non_null"] for s in summary.values())
    total_hit = sum(s["hit_rate_non_null"] for s in summary.values())

    print(f"\n{'=' * 55}")
    print(f"daily_volatility {'(dry run) ' if args.dry_run else ''}complete.")
    print(f"  Symbols:            {len(summary)}")
    print(f"  Returns read:       {total_returns}")
    print(f"  Rows computed:      {total_computed}")
    if not args.dry_run:
        print(f"  Rowcount written:   {total_written}")
    print(f"  Non-null rv5:       {total_rv5}")
    print(f"  Non-null rv21:      {total_rv21}")
    print(f"  Non-null rv63:      {total_rv63}")
    print(f"  Non-null regime:    {total_regime}")
    print(f"  Non-null band:      {total_band}")
    print(f"  Non-null hit_rate:  {total_hit}")
    print(f"{'=' * 55}\n")


if __name__ == "__main__":
    main()
