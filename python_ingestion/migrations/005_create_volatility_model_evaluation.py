"""
Migration 005: Create volatility_model_evaluation table.

Background:
    Phase 3 introduces one-day-ahead volatility forecasting and formal
    out-of-sample model evaluation. Forecasts are written back to
    daily_volatility, while per-symbol evaluation metrics are persisted
    separately so model quality can be tracked over time.

What this migration does:
    Creates volatility_model_evaluation with one row per
    (symbol, model_name, eval_window_end).

Schema notes:
    - symbol uses utf8mb4_unicode_ci to match the Phase 1/2 derived
      tables and the earnings/financials tables.
    - model_name stores HAR-RV and baseline identifiers such as
      har_rv_v1, baseline_yesterday_rv, and baseline_rolling21.
    - UNIQUE KEY (symbol, model_name, eval_window_end) makes repeated
      evaluation runs idempotent for the same evaluation end date.

Idempotent:
    Uses CREATE TABLE IF NOT EXISTS. Safe to run repeatedly.

Usage:
    python -m python_ingestion.migrations.005_create_volatility_model_evaluation [--dry-run]
"""
import argparse
import logging

logger = logging.getLogger(__name__)


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS volatility_model_evaluation (
    id BIGINT NOT NULL AUTO_INCREMENT,
    symbol VARCHAR(16) NOT NULL,
    model_name VARCHAR(32) NOT NULL,
    eval_window_start DATE NOT NULL,
    eval_window_end DATE NOT NULL,
    eval_window_days INT NOT NULL,
    mae DECIMAL(12, 8) NULL,
    rmse DECIMAL(12, 8) NULL,
    qlike DECIMAL(12, 8) NULL,
    n_observations INT NOT NULL,
    computed_at DATETIME NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_vol_eval_symbol_model_end (symbol, model_name, eval_window_end),
    INDEX idx_vol_eval_symbol_model_end (symbol, model_name, eval_window_end DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""


def has_table(db) -> bool:
    rows = db.execute(
        """
        SELECT 1 FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'volatility_model_evaluation'
        LIMIT 1
        """
    ) or []
    return len(rows) > 0


def run_migration(dry_run: bool = False):
    from python_ingestion.db import get_db_manager
    db = get_db_manager()

    if has_table(db):
        logger.info("volatility_model_evaluation table already exists. Nothing to do.")
        return

    if dry_run:
        logger.info("[DRY RUN] Would create volatility_model_evaluation table.")
        return

    db.execute(CREATE_TABLE_SQL)
    logger.info("Created volatility_model_evaluation table.")


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    parser = argparse.ArgumentParser(
        description="Create the volatility_model_evaluation table for the Phase 3 HAR-RV layer."
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Report what would change without modifying the database.",
    )
    args = parser.parse_args()
    run_migration(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
