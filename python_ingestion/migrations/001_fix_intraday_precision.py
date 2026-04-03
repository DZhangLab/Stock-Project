"""
Migration 001: Fix intraday table precision loss.

Background:
    Some intraday per-symbol tables were created with an older schema that
    used INT columns for price fields (minuteOpen, minuteHigh, minuteLow,
    minuteClose).  This silently truncated decimal prices to whole numbers
    on every INSERT (e.g. $253.14 became $253).

    The same legacy tables were also missing a UNIQUE KEY on timePoint,
    which prevented the ingestion system's ON DUPLICATE KEY UPDATE from
    working correctly (it inserted duplicate rows instead of updating).

What this migration does:
    1. Scans information_schema for intraday tables whose price columns
       are still INT and converts them to DECIMAL(18,4).
    2. Adds a UNIQUE KEY on timePoint where missing (after removing any
       duplicate rows, keeping the newest per timePoint).

What this migration does NOT do:
    - It does NOT restore decimal precision for rows that were already
      truncated.  Those values are permanently lost and must be re-ingested
      from the upstream API.  See the backfill step below.

Backfill (manual follow-up after running this migration):
    Re-ingest affected symbols to replace the truncated integer data with
    fresh decimal-precision data from the API.  Example for a single symbol:

        from python_ingestion.jobs.intraday import IntradayCollector
        c = IntradayCollector()
        c.collect_intraday("AAPL")

    Or use refresh_all.py for AAPL, or run the full ingestion scheduler
    (main.py) to let it cycle through all symbols automatically.

Usage:
    python -m python_ingestion.migrations.001_fix_intraday_precision [--dry-run]

Idempotent:
    Safe to run multiple times.  Tables already at DECIMAL(18,4) with the
    UNIQUE KEY present are skipped with no changes.
"""
import argparse
import logging
import sys

logger = logging.getLogger(__name__)


def find_affected_tables(db) -> list:
    """Return table names that still have INT price columns."""
    rows = db.execute(
        """
        SELECT DISTINCT TABLE_NAME
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = %s
          AND COLUMN_NAME = 'minuteOpen'
          AND DATA_TYPE = 'int'
        ORDER BY TABLE_NAME
        """,
        (db.config.database,),
    ) or []
    return [r[0] for r in rows]


def find_tables_missing_unique_key(db) -> list:
    """Return intraday table names that lack uq_timepoint."""
    # First get all intraday tables (those with a minuteOpen column)
    all_rows = db.execute(
        """
        SELECT DISTINCT TABLE_NAME
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = %s
          AND COLUMN_NAME = 'minuteOpen'
        ORDER BY TABLE_NAME
        """,
        (db.config.database,),
    ) or []
    all_tables = {r[0] for r in all_rows}

    # Then get tables that already have the unique key
    uq_rows = db.execute(
        """
        SELECT DISTINCT TABLE_NAME
        FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = %s
          AND INDEX_NAME = 'uq_timepoint'
        """,
        (db.config.database,),
    ) or []
    have_uq = {r[0] for r in uq_rows}

    return sorted(all_tables - have_uq)


def run_migration(dry_run: bool = False):
    """
    Scan all intraday tables and fix schema where needed.

    Args:
        dry_run: If True, only report what would change without modifying anything.
    """
    from python_ingestion.db import get_db_manager

    db = get_db_manager()

    # --- Phase 1: INT -> DECIMAL(18,4) ---
    int_tables = find_affected_tables(db)
    if int_tables:
        logger.info(
            "Found %d table(s) with INT price columns: %s",
            len(int_tables),
            ", ".join(int_tables),
        )
    else:
        logger.info("No tables with INT price columns found. Schema is up to date.")

    for table in int_tables:
        if dry_run:
            logger.info("[DRY RUN] Would convert %s price columns to DECIMAL(18,4)", table)
        else:
            db.execute(f"""
                ALTER TABLE `{table}`
                    MODIFY minuteOpen  DECIMAL(18, 4),
                    MODIFY minuteHigh  DECIMAL(18, 4),
                    MODIFY minuteLow   DECIMAL(18, 4),
                    MODIFY minuteClose DECIMAL(18, 4),
                    MODIFY minuteVolume DOUBLE
            """)
            logger.info("Migrated %s: price columns INT -> DECIMAL(18,4)", table)

    # --- Phase 2: Ensure UNIQUE KEY uq_timepoint ---
    missing_uq_tables = find_tables_missing_unique_key(db)
    if missing_uq_tables:
        logger.info(
            "Found %d table(s) missing UNIQUE KEY uq_timepoint: %s",
            len(missing_uq_tables),
            ", ".join(missing_uq_tables),
        )
    else:
        logger.info("All intraday tables have UNIQUE KEY uq_timepoint.")

    for table in missing_uq_tables:
        if dry_run:
            logger.info("[DRY RUN] Would add UNIQUE KEY uq_timepoint to %s", table)
        else:
            # Remove duplicates first (keep newest row per timePoint)
            db.execute(f"""
                DELETE a FROM `{table}` a
                INNER JOIN (
                    SELECT timePoint, MAX(id) AS keep_id
                    FROM `{table}`
                    GROUP BY timePoint
                    HAVING COUNT(*) > 1
                ) b ON a.timePoint = b.timePoint AND a.id < b.keep_id
            """)
            db.execute(f"ALTER TABLE `{table}` ADD UNIQUE KEY uq_timepoint (timePoint)")
            logger.info("Added UNIQUE KEY uq_timepoint to %s", table)

    # --- Summary ---
    total_fixed = len(int_tables) + len(missing_uq_tables)
    if dry_run:
        logger.info("Dry run complete. %d table(s) would be modified.", total_fixed)
    elif total_fixed > 0:
        logger.info("Migration complete. %d table(s) modified.", total_fixed)
        if int_tables:
            logger.info(
                "NOTE: Existing rows in these tables still contain truncated "
                "integer prices. Re-ingest from the API to restore decimal "
                "precision. Affected tables: %s",
                ", ".join(int_tables),
            )
    else:
        logger.info("Nothing to migrate. All tables are already up to date.")


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Fix intraday table precision: INT -> DECIMAL(18,4), add UNIQUE KEY."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would change without modifying the database.",
    )
    args = parser.parse_args()

    run_migration(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
