"""
Migration 006: Create earnings_event_outcome table.

Phase 4A introduces a descriptive post-earnings drift event-outcome
layer.  It stores realized post-event returns for quarterly reporting
events using local price data only.  It is not a predictive model.

Idempotent:
    Uses CREATE TABLE IF NOT EXISTS. Safe to run repeatedly.

Usage:
    python -m python_ingestion.migrations.006_create_earnings_event_outcome [--dry-run]
"""
import argparse
import logging

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


def has_table(db) -> bool:
    rows = db.execute(
        """
        SELECT 1 FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'earnings_event_outcome'
        LIMIT 1
        """
    ) or []
    return len(rows) > 0


def run_migration(dry_run: bool = False):
    from python_ingestion.db import get_db_manager
    db = get_db_manager()

    if has_table(db):
        logger.info("earnings_event_outcome table already exists. Nothing to do.")
        return

    if dry_run:
        logger.info("[DRY RUN] Would create earnings_event_outcome table.")
        return

    db.execute(CREATE_TABLE_SQL)
    logger.info("Created earnings_event_outcome table.")


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    parser = argparse.ArgumentParser(
        description="Create earnings_event_outcome for Phase 4A PEAD outcomes."
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
