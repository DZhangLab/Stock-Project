"""
Migration 007: Widen volatility_model_evaluation.qlike.

Background:
    Some finite QLIKE values can exceed DECIMAL(12, 8), which allows only
    four integer digits. DECIMAL(24, 8) preserves the existing 8 decimal
    places while allowing much larger finite values.

Idempotent:
    Checks the live column definition and only alters qlike when needed.

Usage:
    python -m python_ingestion.migrations.007_widen_volatility_evaluation_qlike [--dry-run]
"""
import argparse
import logging

logger = logging.getLogger(__name__)


ALTER_QLIKE_SQL = """
ALTER TABLE volatility_model_evaluation
MODIFY COLUMN qlike DECIMAL(24, 8) NULL
"""


def get_qlike_column(db):
    rows = db.execute(
        """
        SELECT NUMERIC_PRECISION, NUMERIC_SCALE, IS_NULLABLE, COLUMN_TYPE
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'volatility_model_evaluation'
          AND COLUMN_NAME = 'qlike'
        LIMIT 1
        """
    ) or []
    return rows[0] if rows else None


def run_migration(dry_run: bool = False):
    from python_ingestion.db import get_db_manager

    db = get_db_manager()
    column = get_qlike_column(db)
    if column is None:
        raise RuntimeError("volatility_model_evaluation.qlike column not found")

    precision, scale, is_nullable, column_type = column
    if int(precision) >= 24 and int(scale) == 8 and is_nullable == "YES":
        logger.info(
            "volatility_model_evaluation.qlike already compatible: %s",
            column_type,
        )
        return

    if dry_run:
        logger.info(
            "[DRY RUN] Would alter volatility_model_evaluation.qlike "
            "from %s to DECIMAL(24,8) NULL.",
            column_type,
        )
        return

    db.execute(ALTER_QLIKE_SQL)
    logger.info("Altered volatility_model_evaluation.qlike to DECIMAL(24,8) NULL.")


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    parser = argparse.ArgumentParser(
        description="Widen volatility_model_evaluation.qlike to DECIMAL(24,8)."
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Report what would change without modifying the database.",
    )
    args = parser.parse_args()
    run_migration(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
