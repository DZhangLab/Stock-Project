"""
Phase 4A earnings event-outcome job.

Computes descriptive post-earnings returns from local MySQL data only.
This job does not fetch release times, does not make external API calls,
and does not implement prediction, regression, aggregate buckets, Java
API endpoints, frontend UI, or scheduler hooks.
"""
import argparse
import json
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..analytics.event_window import (
    compute_event_window_returns,
    normalize_fiscal_period_label,
)
from ..config import PIPELINE_SYMBOLS
from ..db import get_db_manager

logger = logging.getLogger(__name__)


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS earnings_event_outcome (
    id BIGINT NOT NULL AUTO_INCREMENT,
    symbol VARCHAR(16) COLLATE utf8mb4_unicode_ci NOT NULL,
    fiscal_period_label VARCHAR(32) NOT NULL,
    normalized_fiscal_period_label VARCHAR(32) NULL,
    event_date DATE NOT NULL,
    event_date_basis ENUM('reported_date','call_date') NOT NULL,
    event_release_time ENUM('pre_market','during_market','post_market','unknown') NOT NULL,
    first_reaction_date DATE NULL,
    pre_event_close DECIMAL(18,4) NULL,
    ret_1d DECIMAL(18,8) NULL,
    ret_3d DECIMAL(18,8) NULL,
    ret_5d DECIMAL(18,8) NULL,
    ret_20d DECIMAL(18,8) NULL,
    car_3d DECIMAL(18,8) NULL,
    car_5d DECIMAL(18,8) NULL,
    car_20d DECIMAL(18,8) NULL,
    surprise_pct_at_event DECIMAL(10,4) NULL,
    ai_overall_tone_at_event VARCHAR(32) NULL,
    feature_snapshot_json JSON NULL,
    quality_flag ENUM('full','partial','excluded') NOT NULL,
    exclusion_reason VARCHAR(128) NULL,
    computed_at DATETIME NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_earnings_event_outcome_symbol_period_basis (
        symbol, normalized_fiscal_period_label, event_date_basis
    ),
    INDEX idx_earnings_event_outcome_symbol_event_date (symbol, event_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

UPSERT_SQL = """
INSERT INTO earnings_event_outcome (
    symbol, fiscal_period_label, normalized_fiscal_period_label,
    event_date, event_date_basis, event_release_time, first_reaction_date,
    pre_event_close, ret_1d, ret_3d, ret_5d, ret_20d,
    car_3d, car_5d, car_20d,
    surprise_pct_at_event, ai_overall_tone_at_event, feature_snapshot_json,
    quality_flag, exclusion_reason, computed_at
) VALUES (
    %s, %s, %s, %s, %s, %s, %s,
    %s, %s, %s, %s, %s,
    %s, %s, %s,
    %s, %s, %s,
    %s, %s, %s
)
ON DUPLICATE KEY UPDATE
    fiscal_period_label = VALUES(fiscal_period_label),
    event_date = VALUES(event_date),
    event_release_time = VALUES(event_release_time),
    first_reaction_date = VALUES(first_reaction_date),
    pre_event_close = VALUES(pre_event_close),
    ret_1d = VALUES(ret_1d),
    ret_3d = VALUES(ret_3d),
    ret_5d = VALUES(ret_5d),
    ret_20d = VALUES(ret_20d),
    car_3d = VALUES(car_3d),
    car_5d = VALUES(car_5d),
    car_20d = VALUES(car_20d),
    surprise_pct_at_event = VALUES(surprise_pct_at_event),
    ai_overall_tone_at_event = VALUES(ai_overall_tone_at_event),
    feature_snapshot_json = VALUES(feature_snapshot_json),
    quality_flag = VALUES(quality_flag),
    exclusion_reason = VALUES(exclusion_reason),
    computed_at = VALUES(computed_at),
    updated_at = CURRENT_TIMESTAMP
"""


def _ensure_table(db) -> None:
    db.execute(CREATE_TABLE_SQL)


def _parse_date_arg(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def _decimal_to_json(value: Any) -> Optional[str]:
    if value is None:
        return None
    return str(value)


def _select_snapshots(
    db,
    symbol: str,
    start_date: Optional[date],
    end_date: Optional[date],
) -> List[Dict[str, Any]]:
    where = ["symbol = %s"]
    params: List[Any] = [symbol]
    if start_date is not None:
        where.append("reported_date >= %s")
        params.append(start_date)
    if end_date is not None:
        where.append("reported_date <= %s")
        params.append(end_date)

    sql = f"""
        SELECT
            id, symbol, fiscal_date_ending, reported_date, fiscal_period_label,
            reported_eps, estimated_eps, surprise, surprise_percentage,
            source
        FROM quarterly_reporting_snapshot
        WHERE {' AND '.join(where)}
        ORDER BY reported_date ASC, fiscal_date_ending ASC
    """
    rows = db.execute(sql, tuple(params)) or []
    columns = [
        "snapshot_id",
        "symbol",
        "fiscal_date_ending",
        "reported_date",
        "fiscal_period_label",
        "reported_eps",
        "estimated_eps",
        "surprise",
        "surprise_percentage",
        "source",
    ]
    return [dict(zip(columns, row)) for row in rows]


def _select_daily_prices(db, symbol: str) -> List[Tuple[date, Decimal]]:
    rows = db.execute(
        """
        SELECT trade_date, close
        FROM daily_returns
        WHERE symbol = %s
        ORDER BY trade_date ASC
        """,
        (symbol,),
    ) or []
    return [(row[0], row[1]) for row in rows]


def _select_ai_tone_by_period(db, symbol: str) -> Dict[str, str]:
    rows = db.execute(
        """
        SELECT fiscal_period_label, overall_tone
        FROM earnings_ai_analysis
        WHERE symbol = %s
        """,
        (symbol,),
    ) or []
    result: Dict[str, str] = {}
    for fiscal_period_label, overall_tone in rows:
        normalized = normalize_fiscal_period_label(fiscal_period_label)
        tone = str(overall_tone).strip().lower() if overall_tone is not None else ""
        if normalized and tone:
            result[normalized] = tone[:32]
    return result


def _has_valid_surprise(snapshot: Dict[str, Any], event_date: date) -> Tuple[bool, Optional[str]]:
    surprise_pct = snapshot.get("surprise_percentage")
    reported_eps = snapshot.get("reported_eps")
    if surprise_pct is None:
        return False, "missing_surprise_percentage"
    if reported_eps is None:
        return False, "missing_reported_eps"
    if Decimal(str(reported_eps)) == Decimal("0") and Decimal(str(surprise_pct)) == Decimal("-100"):
        if event_date >= date.today():
            return False, "unreliable_zero_eps_negative_surprise"
    return True, None


def _quality_flag(
    window_has_full_returns: bool,
    surprise_valid: bool,
    ai_tone: Optional[str],
    exclusion_reason: Optional[str],
) -> Tuple[str, Optional[str]]:
    if exclusion_reason:
        return "excluded", exclusion_reason
    if not window_has_full_returns:
        return "excluded", "missing_post_event_price_window"
    if not surprise_valid:
        return "excluded", "invalid_eps_or_surprise_data"
    if ai_tone:
        return "full", None
    return "partial", "missing_ai_tone"


def _build_outcome_params(
    symbol: str,
    snapshot: Dict[str, Any],
    bars: Sequence[Tuple[date, Decimal]],
    ai_tone_by_period: Dict[str, str],
    computed_at: datetime,
) -> Optional[Tuple]:
    event_date = snapshot.get("reported_date")
    if event_date is None:
        logger.warning(
            "%s %s: skipped because reported_date is NULL and event_date is NOT NULL",
            symbol,
            snapshot.get("fiscal_period_label") or snapshot.get("fiscal_date_ending"),
        )
        return None

    fiscal_period_label = snapshot.get("fiscal_period_label")
    normalized_label = normalize_fiscal_period_label(fiscal_period_label)
    if normalized_label is None:
        normalized_label = normalize_fiscal_period_label(
            _derive_label_from_fiscal_date(snapshot.get("fiscal_date_ending"))
        )
    if normalized_label is None:
        logger.warning("%s snapshot_id=%s skipped: missing fiscal period label", symbol, snapshot["snapshot_id"])
        return None
    fiscal_period_label = str(fiscal_period_label or normalized_label)[:32]

    window = compute_event_window_returns(event_date, bars)
    surprise_valid, surprise_reason = _has_valid_surprise(snapshot, event_date)
    ai_tone = ai_tone_by_period.get(normalized_label)
    quality, quality_reason = _quality_flag(
        window_has_full_returns=window.has_full_return_window,
        surprise_valid=surprise_valid,
        ai_tone=ai_tone,
        exclusion_reason=window.exclusion_reason or surprise_reason,
    )

    feature_snapshot = {
        "phase": "4A",
        "source_snapshot_id": snapshot["snapshot_id"],
        "fiscal_date_ending": (
            None
            if snapshot.get("fiscal_date_ending") is None
            else snapshot["fiscal_date_ending"].isoformat()
        ),
        "reported_eps": _decimal_to_json(snapshot.get("reported_eps")),
        "estimated_eps": _decimal_to_json(snapshot.get("estimated_eps")),
        "surprise": _decimal_to_json(snapshot.get("surprise")),
        "surprise_percentage": _decimal_to_json(snapshot.get("surprise_percentage")),
        "event_date_rule": "reported_date",
        "event_release_time_source": "unavailable_locally",
        "first_reaction_date_rule": "next_trading_day_after_event_date_for_unknown_release_time",
        "return_window_rule": "ret_Nd_close_on_Nth_trading_day_starting_at_first_reaction_date_over_pre_event_close_minus_1",
        "car_rule": "not_computed_without_benchmark_in_phase_4A",
    }

    returns = window.returns
    return (
        symbol,
        fiscal_period_label,
        normalized_label,
        event_date,
        "reported_date",
        "unknown",
        window.first_reaction_date,
        window.pre_event_close,
        returns[1],
        returns[3],
        returns[5],
        returns[20],
        None,
        None,
        None,
        snapshot.get("surprise_percentage") if surprise_valid else None,
        ai_tone,
        json.dumps(feature_snapshot, ensure_ascii=True),
        quality,
        quality_reason,
        computed_at,
    )


def _derive_label_from_fiscal_date(fiscal_date: Optional[date]) -> Optional[str]:
    if fiscal_date is None:
        return None
    quarter = ((fiscal_date.month - 1) // 3) + 1
    return f"{fiscal_date.year}Q{quarter}"


def _persist(db, rows: Sequence[Tuple]) -> int:
    if not rows:
        return 0
    return db.executemany(UPSERT_SQL, list(rows))


def _list_all_symbols(db) -> List[str]:
    rows = db.execute(
        "SELECT DISTINCT symbol FROM quarterly_reporting_snapshot ORDER BY symbol"
    ) or []
    return [row[0] for row in rows]


def run_for_symbols(
    symbols: Sequence[str],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    dry_run: bool = False,
) -> Dict[str, dict]:
    db = get_db_manager()
    _ensure_table(db)

    start = _parse_date_arg(start_date)
    end = _parse_date_arg(end_date)
    computed_at = datetime.now()
    summary: Dict[str, dict] = {}

    for symbol in symbols:
        symbol = symbol.strip().upper()
        snapshots = _select_snapshots(db, symbol, start, end)
        bars = _select_daily_prices(db, symbol)
        ai_tone_by_period = _select_ai_tone_by_period(db, symbol)
        params = [
            row
            for snapshot in snapshots
            if (row := _build_outcome_params(symbol, snapshot, bars, ai_tone_by_period, computed_at)) is not None
        ]

        quality_counts = {"full": 0, "partial": 0, "excluded": 0}
        return_counts = {"ret_1d": 0, "ret_3d": 0, "ret_5d": 0, "ret_20d": 0}
        for row in params:
            quality_counts[row[18]] += 1
            if row[8] is not None:
                return_counts["ret_1d"] += 1
            if row[9] is not None:
                return_counts["ret_3d"] += 1
            if row[10] is not None:
                return_counts["ret_5d"] += 1
            if row[11] is not None:
                return_counts["ret_20d"] += 1

        if dry_run:
            written = 0
            logger.info(
                "[DRY RUN] %s: %d snapshots, %d price bars, %d outcome rows would be upserted",
                symbol,
                len(snapshots),
                len(bars),
                len(params),
            )
        else:
            written = _persist(db, params)
            logger.info(
                "%s: %d snapshots, %d price bars, %d outcome rows upserted (rowcount=%d)",
                symbol,
                len(snapshots),
                len(bars),
                len(params),
                written,
            )

        summary[symbol] = {
            "snapshots": len(snapshots),
            "price_bars": len(bars),
            "computed": len(params),
            "written": written,
            "quality_counts": quality_counts,
            "return_counts": return_counts,
            "skipped_missing_event_date": len(snapshots) - len(params),
        }

    return summary


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    parser = argparse.ArgumentParser(
        description="Compute Phase 4A descriptive post-earnings event outcomes."
    )
    parser.add_argument(
        "--symbol",
        action="append",
        dest="symbols",
        help="Symbol to process (repeatable). Use --all-symbols for everything.",
    )
    parser.add_argument(
        "--all-symbols",
        action="store_true",
        help="Process every distinct symbol in quarterly_reporting_snapshot.",
    )
    parser.add_argument("--start-date", help="Optional reported_date lower bound, yyyy-mm-dd.")
    parser.add_argument("--end-date", help="Optional reported_date upper bound, yyyy-mm-dd.")
    parser.add_argument("--dry-run", action="store_true", help="Compute without writing rows.")
    args = parser.parse_args()

    for label, value in (("--start-date", args.start_date), ("--end-date", args.end_date)):
        if value:
            try:
                datetime.strptime(value, "%Y-%m-%d")
            except ValueError:
                parser.error(f"{label} must be yyyy-mm-dd, got {value!r}")

    db = get_db_manager()
    if args.all_symbols:
        symbols = _list_all_symbols(db)
    elif args.symbols:
        symbols = [symbol.strip().upper() for symbol in args.symbols if symbol.strip()]
    else:
        symbols = list(PIPELINE_SYMBOLS)
        logger.info(
            "No --symbol or --all-symbols given; defaulting to PIPELINE_SYMBOLS=%s",
            symbols,
        )

    if not symbols:
        parser.error("No symbols to process.")

    summary = run_for_symbols(
        symbols=symbols,
        start_date=args.start_date,
        end_date=args.end_date,
        dry_run=args.dry_run,
    )

    total_computed = sum(item["computed"] for item in summary.values())
    total_written = sum(item["written"] for item in summary.values())
    total_quality = {
        flag: sum(item["quality_counts"][flag] for item in summary.values())
        for flag in ("full", "partial", "excluded")
    }
    total_returns = {
        key: sum(item["return_counts"][key] for item in summary.values())
        for key in ("ret_1d", "ret_3d", "ret_5d", "ret_20d")
    }

    print(f"\n{'=' * 64}")
    print(f"earnings_event_outcome {'(dry run) ' if args.dry_run else ''}complete.")
    print(f"  Symbols:        {len(summary)}")
    print(f"  Outcomes:       {total_computed}")
    if not args.dry_run:
        print(f"  Rowcount:       {total_written}")
    print(
        "  Quality:        "
        f"full={total_quality['full']} partial={total_quality['partial']} excluded={total_quality['excluded']}"
    )
    print(
        "  Return counts:  "
        f"ret_1d={total_returns['ret_1d']} ret_3d={total_returns['ret_3d']} "
        f"ret_5d={total_returns['ret_5d']} ret_20d={total_returns['ret_20d']}"
    )
    print(f"{'=' * 64}\n")


if __name__ == "__main__":
    main()
