"""
Migration 004: Create daily_volatility table.

Background:
    Phase 2 of the market-reaction analysis plan introduces realized
    volatility metrics, a tercile regime label, a descriptive ±1-sigma
    envelope around close, and an empirical hit-rate validation field.

    The HAR-RV forecast columns (har_rv_forecast_1d, har_rv_model_version)
    are present in the schema but remain NULL in Phase 2.  They are
    populated later by Phase 3.

What this migration does:
    Creates daily_volatility with one row per (symbol, as_of_date),
    using the same idempotent additive pattern as migration 003.

Schema notes:
    - as_of_date is a proper DATE column.
    - The symbol column uses utf8mb4_unicode_ci so cross-table joins
      against earnings_*, daily_returns, and quarterly_reporting_snapshot
      do not need a COLLATE override.  Joins against everydayAfterClose
      still need COLLATE because that table uses utf8mb4_0900_ai_ci.
    - UNIQUE KEY (symbol, as_of_date) supports idempotent upserts.

Idempotent:
    Uses CREATE TABLE IF NOT EXISTS.  Safe to run repeatedly.

Usage:
    python -m python_ingestion.migrations.004_create_daily_volatility [--dry-run]
"""
import argparse
import logging

logger = logging.getLogger(__name__)


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS daily_volatility (
    id BIGINT NOT NULL AUTO_INCREMENT,
    symbol VARCHAR(16) NOT NULL,
    as_of_date DATE NOT NULL,
    realized_vol_5d DECIMAL(10, 6) NULL,
    realized_vol_21d DECIMAL(10, 6) NULL,
    realized_vol_63d DECIMAL(10, 6) NULL,
    volatility_regime ENUM('low', 'medium', 'high') NULL,
    vol_band_low DECIMAL(18, 4) NULL,
    vol_band_high DECIMAL(18, 4) NULL,
    band_hit_rate_trailing_90d DECIMAL(6, 4) NULL,
    har_rv_forecast_1d DECIMAL(10, 6) NULL,
    har_rv_model_version VARCHAR(32) NULL,
    computed_at DATETIME NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_daily_volatility_symbol_date (symbol, as_of_date),
    INDEX idx_daily_volatility_symbol_date (symbol, as_of_date DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""


def has_table(db) -> bool:
    rows = db.execute(
        """
        SELECT 1 FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'daily_volatility'
        LIMIT 1
        """
    ) or []
    return len(rows) > 0


def run_migration(dry_run: bool = False):
    from python_ingestion.db import get_db_manager
    db = get_db_manager()

    if has_table(db):
        logger.info("daily_volatility table already exists. Nothing to do.")
        return

    if dry_run:
        logger.info("[DRY RUN] Would create daily_volatility table.")
        return

    db.execute(CREATE_TABLE_SQL)
    logger.info("Created daily_volatility table.")


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    parser = argparse.ArgumentParser(
        description="Create the daily_volatility table for the Phase 2 volatility MVP."
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Report what would change without modifying the database.",
    )
    args = parser.parse_args()
    run_migration(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
