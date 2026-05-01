"""
Migration 003: Create daily_returns table.

Background:
    Phase 1 of the market-reaction analysis plan introduces a shared
    returns layer that downstream analytics (volatility forecasting,
    post-earnings drift) can read from instead of recomputing returns
    in every query.

What this migration does:
    Creates the daily_returns table with one row per (symbol, trade_date),
    storing prev_close, close, log_return, and simple_return.

Schema notes:
    - trade_date is a proper DATE column (everydayAfterClose stores
      its date as VARCHAR; this table normalizes to DATE).
    - The symbol column uses utf8mb4_unicode_ci so cross-table joins
      against the earnings_* tables (which already use utf8mb4_unicode_ci)
      do not need a COLLATE override.  Joins against everydayAfterClose,
      whose symbol column uses utf8mb4_0900_ai_ci, will still need a
      COLLATE clause in queries that span both — that is unchanged.
    - UNIQUE KEY (symbol, trade_date) makes upserts via
      INSERT ... ON DUPLICATE KEY UPDATE idempotent.

Idempotent:
    Uses CREATE TABLE IF NOT EXISTS.  Safe to run repeatedly.

Usage:
    python -m python_ingestion.migrations.003_create_daily_returns [--dry-run]
"""
import argparse
import logging

logger = logging.getLogger(__name__)


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS daily_returns (
    id BIGINT NOT NULL AUTO_INCREMENT,
    symbol VARCHAR(16) NOT NULL,
    trade_date DATE NOT NULL,
    prev_close DECIMAL(18, 4) NOT NULL,
    close DECIMAL(18, 4) NOT NULL,
    log_return DECIMAL(18, 8) NOT NULL,
    simple_return DECIMAL(18, 8) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_daily_returns_symbol_date (symbol, trade_date),
    INDEX idx_daily_returns_symbol_date (symbol, trade_date DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""


def has_table(db) -> bool:
    rows = db.execute(
        """
        SELECT 1 FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'daily_returns'
        LIMIT 1
        """
    ) or []
    return len(rows) > 0


def run_migration(dry_run: bool = False):
    from python_ingestion.db import get_db_manager
    db = get_db_manager()

    if has_table(db):
        logger.info("daily_returns table already exists. Nothing to do.")
        return

    if dry_run:
        logger.info("[DRY RUN] Would create daily_returns table.")
        return

    db.execute(CREATE_TABLE_SQL)
    logger.info("Created daily_returns table.")


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    parser = argparse.ArgumentParser(
        description="Create the daily_returns table for the Phase 1 shared returns layer."
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Report what would change without modifying the database.",
    )
    args = parser.parse_args()
    run_migration(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
