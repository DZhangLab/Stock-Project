"""
Migration 002: Deduplicate everydayAfterClose and add unique constraint.

Background:
    The everydayAfterClose table uses a plain INSERT (no ON DUPLICATE KEY
    UPDATE) and has no unique constraint on (symbol, datetime).  This means
    every scheduler run that processes the same symbol on the same day
    creates a duplicate row.  As of this migration the table has ~309
    duplicate rows across 258 (symbol, datetime) groups.

What this migration does:
    1. Removes duplicate rows, keeping the newest (highest id) per
       (symbol, datetime) group.
    2. Adds a UNIQUE KEY on (symbol, datetime) to prevent future
       duplicates.

Schema tradeoff:
    The ideal semantic key would be (symbol, trade_date) on a DATE column.
    However the current `datetime` column is VARCHAR(50) storing ISO date
    strings like "2025-11-10".  Adding a new DATE column and migrating all
    consumers is disruptive.  Since the VARCHAR values are consistently
    formatted and lexicographically sortable, a UNIQUE KEY on the existing
    (symbol, datetime) columns is safe and sufficient for now.  A future
    migration can introduce a proper daily_bars table with a DATE column
    if needed.

Idempotent:
    Safe to run multiple times.  The dedup DELETE is a no-op when no
    duplicates exist, and the ADD UNIQUE KEY is skipped if already present.

Usage:
    python -m python_ingestion.migrations.002_fix_daily_quote_duplicates [--dry-run]
"""
import argparse
import logging
import sys

logger = logging.getLogger(__name__)


def count_duplicates(db) -> int:
    """Return the number of duplicate rows (total rows minus distinct pairs)."""
    rows = db.execute("""
        SELECT COUNT(*) FROM (
            SELECT symbol, datetime FROM everydayAfterClose
            GROUP BY symbol, datetime HAVING COUNT(*) > 1
        ) t
    """)
    return rows[0][0] if rows else 0


def has_unique_key(db) -> bool:
    """Check whether the uq_symbol_datetime unique key already exists."""
    rows = db.execute("""
        SELECT 1 FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'everydayAfterClose'
          AND INDEX_NAME = 'uq_symbol_datetime'
        LIMIT 1
    """) or []
    return len(rows) > 0


def run_migration(dry_run: bool = False):
    from python_ingestion.db import get_db_manager

    db = get_db_manager()

    # --- Phase 1: Remove duplicates (keep newest row per group) ---
    dupe_groups = count_duplicates(db)
    if dupe_groups > 0:
        # Count exact rows that will be deleted
        excess = db.execute("""
            SELECT COUNT(*) FROM everydayAfterClose a
            INNER JOIN (
                SELECT symbol, datetime, MAX(id) AS keep_id
                FROM everydayAfterClose
                GROUP BY symbol, datetime
                HAVING COUNT(*) > 1
            ) b ON a.symbol = b.symbol AND a.datetime = b.datetime AND a.id < b.keep_id
        """)
        rows_to_delete = excess[0][0] if excess else 0

        if dry_run:
            logger.info(
                "[DRY RUN] Would delete %d duplicate rows across %d (symbol, datetime) groups",
                rows_to_delete, dupe_groups,
            )
        else:
            db.execute("""
                DELETE a FROM everydayAfterClose a
                INNER JOIN (
                    SELECT symbol, datetime, MAX(id) AS keep_id
                    FROM everydayAfterClose
                    GROUP BY symbol, datetime
                    HAVING COUNT(*) > 1
                ) b ON a.symbol = b.symbol AND a.datetime = b.datetime AND a.id < b.keep_id
            """)
            logger.info(
                "Deleted %d duplicate rows across %d groups", rows_to_delete, dupe_groups
            )
    else:
        logger.info("No duplicate (symbol, datetime) rows found.")

    # --- Phase 2: Add UNIQUE KEY ---
    if has_unique_key(db):
        logger.info("UNIQUE KEY uq_symbol_datetime already exists. Skipping.")
    elif dry_run:
        logger.info("[DRY RUN] Would add UNIQUE KEY uq_symbol_datetime (symbol, datetime)")
    else:
        db.execute("""
            ALTER TABLE everydayAfterClose
            ADD UNIQUE KEY uq_symbol_datetime (symbol, datetime)
        """)
        logger.info("Added UNIQUE KEY uq_symbol_datetime (symbol, datetime)")

    # --- Summary ---
    if dry_run:
        logger.info("Dry run complete.")
    else:
        remaining = db.execute("SELECT COUNT(*) FROM everydayAfterClose")
        logger.info("Migration complete. %d rows remain.", remaining[0][0])


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Deduplicate everydayAfterClose and add UNIQUE KEY (symbol, datetime)."
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Report what would change without modifying the database.",
    )
    args = parser.parse_args()
    run_migration(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
