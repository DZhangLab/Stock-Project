"""
Migration 009: Create volatility_model_forecast table.

Background:
    Phase 3 computes one-day-ahead volatility forecasts for HAR-RV and
    baseline models. volatility_model_evaluation stores aggregate backtest
    metrics only, so per-model forecast values are stored separately here.

Idempotent:
    Uses CREATE TABLE IF NOT EXISTS. Safe to run repeatedly.

Usage:
    python -m python_ingestion.migrations.009_create_volatility_model_forecast [--dry-run]
"""
import argparse
import logging

logger = logging.getLogger(__name__)


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS volatility_model_forecast (
    id BIGINT NOT NULL AUTO_INCREMENT,
    symbol VARCHAR(16) NOT NULL,
    model_name VARCHAR(64) NOT NULL,
    as_of_date DATE NOT NULL,
    target_date DATE NOT NULL,
    forecast_vol_annualized DECIMAL(18, 8) NULL,
    forecast_variance DECIMAL(18, 12) NULL,
    actual_vol_annualized DECIMAL(18, 8) NULL,
    actual_variance DECIMAL(18, 12) NULL,
    model_version VARCHAR(64) NULL,
    computed_at DATETIME NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_vol_forecast_symbol_model_dates (symbol, model_name, as_of_date, target_date),
    INDEX idx_vol_forecast_symbol_asof (symbol, as_of_date),
    INDEX idx_vol_forecast_symbol_model_asof (symbol, model_name, as_of_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""


def has_table(db) -> bool:
    rows = db.execute(
        """
        SELECT 1 FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'volatility_model_forecast'
        LIMIT 1
        """
    ) or []
    return len(rows) > 0


def run_migration(dry_run: bool = False):
    from python_ingestion.db import get_db_manager

    db = get_db_manager()
    if has_table(db):
        logger.info("volatility_model_forecast table already exists. Nothing to do.")
        return

    if dry_run:
        logger.info("[DRY RUN] Would create volatility_model_forecast table.")
        return

    db.execute(CREATE_TABLE_SQL)
    logger.info("Created volatility_model_forecast table.")


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    parser = argparse.ArgumentParser(
        description="Create volatility_model_forecast for per-model forecast values."
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Report what would change without modifying the database.",
    )
    args = parser.parse_args()
    run_migration(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
