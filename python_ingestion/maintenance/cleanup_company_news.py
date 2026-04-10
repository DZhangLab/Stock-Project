"""
Detect and optionally remove historically noisy rows in company_news.

Background:
    Before precision filters were added to alpha_vantage.py, the ingestion
    pipeline stored articles where the target symbol was a secondary mention,
    appeared only in a multi-stock roundup, or was mislabeled entirely.
    This script retroactively applies the same title-based heuristics to
    flag (and optionally delete) those rows.

Modes:
    --dry-run (default) — detect and report candidates without modification.
    --delete            — delete flagged rows after explicit confirmation.
    --csv-report PATH   — export flagged rows to CSV for manual review.

Detection reuses the same static methods already defined in
AlphaVantageClient (alpha_vantage.py) so that ingestion and cleanup
apply identical standards.

Examples:
    # Audit AAPL only, print summary
    python -m python_ingestion.maintenance.cleanup_company_news --symbol AAPL

    # Audit all symbols, export CSV report
    python -m python_ingestion.maintenance.cleanup_company_news \\
        --all-symbols --csv-report cleanup_report.csv

    # Delete flagged rows for AAPL (will prompt for confirmation)
    python -m python_ingestion.maintenance.cleanup_company_news \\
        --symbol AAPL --delete

    # Resume a full audit from a specific symbol
    python -m python_ingestion.maintenance.cleanup_company_news \\
        --all-symbols --start-from GOOGL
"""
import argparse
import csv
import logging
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..alpha_vantage import AlphaVantageClient
from ..db import get_db_manager
from ..symbols import SYMBOL_LIST

logger = logging.getLogger(__name__)

# Ordered by confidence: highest-confidence reason first.
# Each entry is (reason_label, check_function).
# The check functions are static/class methods on AlphaVantageClient.
CHECKS = [
    ("different_ticker", AlphaVantageClient._title_features_different_ticker),
    ("secondary_mention", AlphaVantageClient._is_secondary_mention),
    ("etf_style", lambda title, _symbol: AlphaVantageClient._contains_etf_style_title_text(title)),
    ("generic_roundup", lambda title, _symbol: AlphaVantageClient._contains_generic_roundup_title(title)),
]


def detect_candidates(
    db: Any,
    symbol: str,
    since_date: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return rows in company_news that fail current title-based precision checks.

    Each returned dict contains the row's DB fields plus a ``flag_reason``
    key indicating which check it failed first (priority order).
    """
    query = """
        SELECT id, symbol, title, source, published_at, ingestion_time
        FROM company_news
        WHERE symbol = %s
    """
    params: list = [symbol]

    if since_date:
        query += " AND published_at >= %s"
        params.append(since_date)

    query += " ORDER BY published_at DESC"

    rows = db.execute(query, tuple(params)) or []
    candidates: List[Dict[str, Any]] = []

    for row in rows:
        row_id, row_symbol, title, source, published_at, ingestion_time = row
        if not title:
            continue

        flag_reason: Optional[str] = None
        for reason, check_fn in CHECKS:
            if check_fn(title, symbol):
                flag_reason = reason
                break

        if flag_reason:
            candidates.append({
                "id": row_id,
                "symbol": row_symbol,
                "title": title,
                "source": source or "",
                "published_at": str(published_at) if published_at else "",
                "ingestion_time": str(ingestion_time) if ingestion_time else "",
                "flag_reason": flag_reason,
            })

    return candidates


def delete_candidates(db: Any, candidates: List[Dict[str, Any]]) -> int:
    """Delete candidate rows by id.  Returns count of deleted rows."""
    if not candidates:
        return 0

    deleted = 0
    for candidate in candidates:
        row_id = candidate["id"]
        try:
            db.execute("DELETE FROM company_news WHERE id = %s", (row_id,))
            deleted += 1
        except Exception as e:
            logger.error("Failed to delete id=%s: %s", row_id, e)

    return deleted


def export_csv(candidates: List[Dict[str, Any]], path: str) -> None:
    """Write flagged candidates to a CSV file."""
    if not candidates:
        return

    fieldnames = ["id", "symbol", "title", "source", "published_at",
                  "ingestion_time", "flag_reason"]

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(candidates)


def count_total_rows(db: Any, symbol: str, since_date: Optional[str] = None) -> int:
    """Return total row count for a symbol in company_news."""
    query = "SELECT COUNT(*) FROM company_news WHERE symbol = %s"
    params: list = [symbol]
    if since_date:
        query += " AND published_at >= %s"
        params.append(since_date)

    result = db.execute(query, tuple(params))
    if result and result[0]:
        return result[0][0]
    return 0


def print_summary_table(stats: List[Dict[str, Any]]) -> None:
    """Print a formatted summary table of per-symbol results."""
    if not stats:
        print("\nNo symbols processed.")
        return

    # Header
    print(f"\n{'Symbol':<10} {'Total':>8} {'Flagged':>8} "
          f"{'diff_tick':>10} {'secondary':>10} {'etf':>6} {'roundup':>8}")
    print("-" * 72)

    grand_total = 0
    grand_flagged = 0
    grand_reasons: Dict[str, int] = {}

    for s in stats:
        reasons = s.get("reasons", {})
        diff = reasons.get("different_ticker", 0)
        sec = reasons.get("secondary_mention", 0)
        etf = reasons.get("etf_style", 0)
        rnd = reasons.get("generic_roundup", 0)

        print(f"{s['symbol']:<10} {s['total']:>8} {s['flagged']:>8} "
              f"{diff:>10} {sec:>10} {etf:>6} {rnd:>8}")

        grand_total += s["total"]
        grand_flagged += s["flagged"]
        for reason, count in reasons.items():
            grand_reasons[reason] = grand_reasons.get(reason, 0) + count

    print("-" * 72)
    print(f"{'TOTAL':<10} {grand_total:>8} {grand_flagged:>8} "
          f"{grand_reasons.get('different_ticker', 0):>10} "
          f"{grand_reasons.get('secondary_mention', 0):>10} "
          f"{grand_reasons.get('etf_style', 0):>6} "
          f"{grand_reasons.get('generic_roundup', 0):>8}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Detect and optionally remove noisy historical rows in company_news.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  %(prog)s --symbol AAPL\n"
            "  %(prog)s --all-symbols --csv-report report.csv\n"
            "  %(prog)s --symbol AAPL --delete\n"
            "  %(prog)s --all-symbols --start-from GOOGL\n"
        ),
    )

    target = parser.add_mutually_exclusive_group()
    target.add_argument("--symbol", type=str, help="Process a single symbol")
    target.add_argument("--all-symbols", action="store_true",
                        help="Process all tracked symbols")

    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Report only, do not delete (default)")
    parser.add_argument("--delete", action="store_true", default=False,
                        help="Actually delete flagged rows (will prompt for confirmation)")
    parser.add_argument("--since-date", type=str, default=None,
                        help="Only check rows published on or after this date (YYYY-MM-DD)")
    parser.add_argument("--csv-report", type=str, default=None,
                        help="Export flagged rows to CSV file at this path")
    parser.add_argument("--start-from", type=str, default=None,
                        help="Resume processing from this symbol (alphabetical)")

    args = parser.parse_args()

    # Validate: must specify either --symbol or --all-symbols
    if not args.symbol and not args.all_symbols:
        parser.error("Please specify --symbol SYMBOL or --all-symbols.")

    # Validate since-date format
    if args.since_date:
        try:
            datetime.strptime(args.since_date, "%Y-%m-%d")
        except ValueError:
            parser.error(f"Invalid --since-date format: {args.since_date}. Use YYYY-MM-DD.")

    # Determine dry-run vs delete mode
    is_dry_run = not args.delete

    # Build symbol list
    if args.symbol:
        symbols = [args.symbol.strip().upper()]
    else:
        symbols = sorted(SYMBOL_LIST)

    # Apply --start-from
    if args.start_from:
        start = args.start_from.strip().upper()
        try:
            idx = next(i for i, s in enumerate(symbols) if s >= start)
            skipped = symbols[:idx]
            symbols = symbols[idx:]
            if skipped:
                print(f"Skipping {len(skipped)} symbols before {start}")
        except StopIteration:
            parser.error(f"--start-from {start} is past all symbols in the list.")

    # Connect to DB
    db = get_db_manager()

    # Print run header
    mode_label = "DELETE" if not is_dry_run else "DRY RUN"
    print(f"\nCompany news cleanup — {mode_label}")
    print(f"Symbols: {len(symbols)}")
    if args.since_date:
        print(f"Since: {args.since_date}")
    if is_dry_run:
        print("No rows will be modified.\n")
    else:
        print("WARNING: flagged rows will be permanently deleted.\n")

    # Deletion confirmation gate
    if not is_dry_run:
        print("=" * 60)
        print("WARNING: You are about to delete rows from company_news.")
        print("This is irreversible unless you have a backup.")
        print("=" * 60)
        answer = input("Type 'yes' to proceed with deletion: ").strip().lower()
        if answer != "yes":
            print("Aborted. No rows deleted.")
            return
        print()

    # Process symbols
    all_candidates: List[Dict[str, Any]] = []
    stats: List[Dict[str, Any]] = []

    for i, symbol in enumerate(symbols):
        prefix = f"[{i + 1}/{len(symbols)}] {symbol}"

        total = count_total_rows(db, symbol, args.since_date)
        candidates = detect_candidates(db, symbol, args.since_date)

        # Count reasons
        reasons: Dict[str, int] = {}
        for c in candidates:
            r = c["flag_reason"]
            reasons[r] = reasons.get(r, 0) + 1

        stats.append({
            "symbol": symbol,
            "total": total,
            "flagged": len(candidates),
            "reasons": reasons,
        })

        if candidates:
            logger.info("%s: %d/%d rows flagged", prefix, len(candidates), total)

            # Show sample flagged titles in dry-run mode
            if is_dry_run and len(candidates) > 0:
                sample = candidates[:3]
                for c in sample:
                    print(f"  {prefix} [{c['flag_reason']}] {c['title'][:80]}")
                if len(candidates) > 3:
                    print(f"  {prefix} ... and {len(candidates) - 3} more")

            all_candidates.extend(candidates)

            # Delete if requested
            if not is_dry_run:
                deleted = delete_candidates(db, candidates)
                print(f"  {prefix}: deleted {deleted}/{len(candidates)} flagged rows")
        else:
            logger.info("%s: clean (%d rows, 0 flagged)", prefix, total)

        # Progress update every 25 symbols or at end
        if len(symbols) > 1 and ((i + 1) % 25 == 0 or (i + 1) == len(symbols)):
            total_flagged = sum(s["flagged"] for s in stats)
            print(f"  Progress: {i + 1}/{len(symbols)} symbols, "
                  f"{total_flagged} total flagged so far")

    # Export CSV if requested
    if args.csv_report and all_candidates:
        export_csv(all_candidates, args.csv_report)
        print(f"\nCSV report written to: {args.csv_report} "
              f"({len(all_candidates)} rows)")

    # Print summary
    print_summary_table(stats)

    total_flagged = sum(s["flagged"] for s in stats)
    if is_dry_run and total_flagged > 0:
        print(f"\nDry run complete. {total_flagged} candidate(s) detected.")
        print("To delete, re-run with --delete (backup recommended first).")
    elif not is_dry_run:
        print(f"\nDeletion complete. {total_flagged} row(s) removed.")
        print("Consider re-running company_news_ai_summary for affected symbols.")
    else:
        print("\nNo cleanup candidates found.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    main()
