"""
Migration 008: Create earnings_sentiment_features table.

Background:
    Phase 6 feasibility uses numeric FinBERT sentiment features derived
    from earnings_ai_analysis.tone_summary_json. This table is a local
    derived read model so downstream analysis and APIs do not need to
    repeatedly parse large JSON payloads.

Idempotent:
    Uses CREATE TABLE IF NOT EXISTS. Safe to run repeatedly.

Usage:
    python -m python_ingestion.migrations.008_create_earnings_sentiment_features [--dry-run]
"""
import argparse
import logging

logger = logging.getLogger(__name__)


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS earnings_sentiment_features (
    id BIGINT NOT NULL AUTO_INCREMENT,
    symbol VARCHAR(16) COLLATE utf8mb4_unicode_ci NOT NULL,
    fiscal_period_label VARCHAR(32) NOT NULL,
    normalized_fiscal_period_label VARCHAR(32) NOT NULL,
    earnings_ai_analysis_id BIGINT NOT NULL,
    overall_tone VARCHAR(32) NULL,
    finbert_overall_tone VARCHAR(32) NULL,
    finbert_aggregate_score DECIMAL(18,8) NULL,
    segment_count INT NULL,
    positive_segment_count INT NULL,
    mixed_segment_count INT NULL,
    negative_segment_count INT NULL,
    positive_segment_ratio DECIMAL(12,8) NULL,
    mixed_segment_ratio DECIMAL(12,8) NULL,
    negative_segment_ratio DECIMAL(12,8) NULL,
    avg_positive_score DECIMAL(12,8) NULL,
    avg_neutral_score DECIMAL(12,8) NULL,
    avg_negative_score DECIMAL(12,8) NULL,
    avg_pos_minus_neg_score DECIMAL(12,8) NULL,
    avg_confidence DECIMAL(12,8) NULL,
    avg_risk_signal_score DECIMAL(12,8) NULL,
    max_risk_signal_score DECIMAL(12,8) NULL,
    avg_guidance_signal_score DECIMAL(12,8) NULL,
    max_guidance_signal_score DECIMAL(12,8) NULL,
    avg_cautious_guidance_signal_score DECIMAL(12,8) NULL,
    max_cautious_guidance_signal_score DECIMAL(12,8) NULL,
    positive_signal_count INT NULL,
    negative_signal_count INT NULL,
    guidance_signal_count INT NULL,
    cautious_guidance_signal_count INT NULL,
    source_tone_analyzer VARCHAR(64) NULL,
    source_model_name VARCHAR(128) NULL,
    source_prompt_version VARCHAR(32) NULL,
    source_analysis_updated_at DATETIME NULL,
    computed_at DATETIME NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_earnings_sentiment_symbol_period (symbol, fiscal_period_label),
    INDEX idx_earnings_sentiment_symbol_norm_period (symbol, normalized_fiscal_period_label),
    INDEX idx_earnings_sentiment_ai_analysis_id (earnings_ai_analysis_id),
    INDEX idx_earnings_sentiment_symbol_updated (symbol, updated_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""


def has_table(db) -> bool:
    rows = db.execute(
        """
        SELECT 1 FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'earnings_sentiment_features'
        LIMIT 1
        """
    ) or []
    return len(rows) > 0


def run_migration(dry_run: bool = False):
    from python_ingestion.db import get_db_manager

    db = get_db_manager()
    if has_table(db):
        logger.info("earnings_sentiment_features table already exists. Nothing to do.")
        return

    if dry_run:
        logger.info("[DRY RUN] Would create earnings_sentiment_features table.")
        return

    db.execute(CREATE_TABLE_SQL)
    logger.info("Created earnings_sentiment_features table.")


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    parser = argparse.ArgumentParser(
        description="Create earnings_sentiment_features for derived FinBERT features."
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Report what would change without modifying the database.",
    )
    args = parser.parse_args()
    run_migration(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
