"""
Derived earnings sentiment feature job.

This job reads earnings_ai_analysis.tone_summary_json from the local
database and extracts numeric FinBERT features into
earnings_sentiment_features. It does not call external APIs.
"""
import argparse
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from ..analytics.event_window import normalize_fiscal_period_label
from ..config import PIPELINE_SYMBOLS
from ..db import get_db_manager

logger = logging.getLogger(__name__)

DECIMAL_SCALE = Decimal("0.00000001")
PERIOD_RE = re.compile(r"^\d{4}Q[1-4]$")


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

UPSERT_SQL = """
INSERT INTO earnings_sentiment_features (
    symbol, fiscal_period_label, normalized_fiscal_period_label,
    earnings_ai_analysis_id, overall_tone, finbert_overall_tone,
    finbert_aggregate_score, segment_count, positive_segment_count,
    mixed_segment_count, negative_segment_count, positive_segment_ratio,
    mixed_segment_ratio, negative_segment_ratio, avg_positive_score,
    avg_neutral_score, avg_negative_score, avg_pos_minus_neg_score,
    avg_confidence, avg_risk_signal_score, max_risk_signal_score,
    avg_guidance_signal_score, max_guidance_signal_score,
    avg_cautious_guidance_signal_score, max_cautious_guidance_signal_score,
    positive_signal_count, negative_signal_count, guidance_signal_count,
    cautious_guidance_signal_count, source_tone_analyzer, source_model_name,
    source_prompt_version, source_analysis_updated_at, computed_at
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
)
ON DUPLICATE KEY UPDATE
    normalized_fiscal_period_label = VALUES(normalized_fiscal_period_label),
    earnings_ai_analysis_id = VALUES(earnings_ai_analysis_id),
    overall_tone = VALUES(overall_tone),
    finbert_overall_tone = VALUES(finbert_overall_tone),
    finbert_aggregate_score = VALUES(finbert_aggregate_score),
    segment_count = VALUES(segment_count),
    positive_segment_count = VALUES(positive_segment_count),
    mixed_segment_count = VALUES(mixed_segment_count),
    negative_segment_count = VALUES(negative_segment_count),
    positive_segment_ratio = VALUES(positive_segment_ratio),
    mixed_segment_ratio = VALUES(mixed_segment_ratio),
    negative_segment_ratio = VALUES(negative_segment_ratio),
    avg_positive_score = VALUES(avg_positive_score),
    avg_neutral_score = VALUES(avg_neutral_score),
    avg_negative_score = VALUES(avg_negative_score),
    avg_pos_minus_neg_score = VALUES(avg_pos_minus_neg_score),
    avg_confidence = VALUES(avg_confidence),
    avg_risk_signal_score = VALUES(avg_risk_signal_score),
    max_risk_signal_score = VALUES(max_risk_signal_score),
    avg_guidance_signal_score = VALUES(avg_guidance_signal_score),
    max_guidance_signal_score = VALUES(max_guidance_signal_score),
    avg_cautious_guidance_signal_score = VALUES(avg_cautious_guidance_signal_score),
    max_cautious_guidance_signal_score = VALUES(max_cautious_guidance_signal_score),
    positive_signal_count = VALUES(positive_signal_count),
    negative_signal_count = VALUES(negative_signal_count),
    guidance_signal_count = VALUES(guidance_signal_count),
    cautious_guidance_signal_count = VALUES(cautious_guidance_signal_count),
    source_tone_analyzer = VALUES(source_tone_analyzer),
    source_model_name = VALUES(source_model_name),
    source_prompt_version = VALUES(source_prompt_version),
    source_analysis_updated_at = VALUES(source_analysis_updated_at),
    computed_at = VALUES(computed_at),
    updated_at = CURRENT_TIMESTAMP
"""


@dataclass(frozen=True)
class SourceAnalysisRow:
    id: int
    symbol: str
    fiscal_period_label: str
    tone_summary_json: Any
    overall_tone: Optional[str]
    tone_analyzer: Optional[str]
    model_name: Optional[str]
    prompt_version: Optional[str]
    updated_at: Any


@dataclass(frozen=True)
class FeatureRow:
    symbol: str
    fiscal_period_label: str
    normalized_fiscal_period_label: str
    earnings_ai_analysis_id: int
    overall_tone: Optional[str]
    finbert_overall_tone: Optional[str]
    finbert_aggregate_score: Optional[Decimal]
    segment_count: Optional[int]
    positive_segment_count: Optional[int]
    mixed_segment_count: Optional[int]
    negative_segment_count: Optional[int]
    positive_segment_ratio: Optional[Decimal]
    mixed_segment_ratio: Optional[Decimal]
    negative_segment_ratio: Optional[Decimal]
    avg_positive_score: Optional[Decimal]
    avg_neutral_score: Optional[Decimal]
    avg_negative_score: Optional[Decimal]
    avg_pos_minus_neg_score: Optional[Decimal]
    avg_confidence: Optional[Decimal]
    avg_risk_signal_score: Optional[Decimal]
    max_risk_signal_score: Optional[Decimal]
    avg_guidance_signal_score: Optional[Decimal]
    max_guidance_signal_score: Optional[Decimal]
    avg_cautious_guidance_signal_score: Optional[Decimal]
    max_cautious_guidance_signal_score: Optional[Decimal]
    positive_signal_count: Optional[int]
    negative_signal_count: Optional[int]
    guidance_signal_count: Optional[int]
    cautious_guidance_signal_count: Optional[int]
    source_tone_analyzer: Optional[str]
    source_model_name: Optional[str]
    source_prompt_version: Optional[str]
    source_analysis_updated_at: Any
    computed_at: datetime

    def to_params(self) -> Tuple:
        return (
            self.symbol,
            self.fiscal_period_label,
            self.normalized_fiscal_period_label,
            self.earnings_ai_analysis_id,
            self.overall_tone,
            self.finbert_overall_tone,
            self.finbert_aggregate_score,
            self.segment_count,
            self.positive_segment_count,
            self.mixed_segment_count,
            self.negative_segment_count,
            self.positive_segment_ratio,
            self.mixed_segment_ratio,
            self.negative_segment_ratio,
            self.avg_positive_score,
            self.avg_neutral_score,
            self.avg_negative_score,
            self.avg_pos_minus_neg_score,
            self.avg_confidence,
            self.avg_risk_signal_score,
            self.max_risk_signal_score,
            self.avg_guidance_signal_score,
            self.max_guidance_signal_score,
            self.avg_cautious_guidance_signal_score,
            self.max_cautious_guidance_signal_score,
            self.positive_signal_count,
            self.negative_signal_count,
            self.guidance_signal_count,
            self.cautious_guidance_signal_count,
            self.source_tone_analyzer,
            self.source_model_name,
            self.source_prompt_version,
            self.source_analysis_updated_at,
            self.computed_at,
        )


@dataclass(frozen=True)
class ExtractionResult:
    row: Optional[FeatureRow]
    warnings: Tuple[str, ...]


def _normalize_period(value: Optional[str]) -> Optional[str]:
    normalized = normalize_fiscal_period_label(value)
    if normalized is None or not PERIOD_RE.match(normalized):
        return None
    return normalized


def _short_text(value: Any, limit: int) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text[:limit]


def _safe_decimal(value: Any, field_name: str, warnings: List[str]) -> Optional[Decimal]:
    if value is None:
        return None
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        warnings.append(f"{field_name}: invalid numeric value {value!r}; storing NULL")
        return None
    if not number.is_finite():
        warnings.append(f"{field_name}: non-finite numeric value {value!r}; storing NULL")
        return None
    return number.quantize(DECIMAL_SCALE, rounding=ROUND_HALF_UP)


def _safe_int(value: Any, field_name: str, warnings: List[str]) -> Optional[int]:
    number = _safe_decimal(value, field_name, warnings)
    if number is None:
        return None
    return int(number)


def _ratio(numerator: Optional[int], denominator: Optional[int]) -> Optional[Decimal]:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return (Decimal(numerator) / Decimal(denominator)).quantize(
        DECIMAL_SCALE,
        rounding=ROUND_HALF_UP,
    )


def _mean(values: Iterable[Decimal]) -> Optional[Decimal]:
    items = list(values)
    if not items:
        return None
    return (sum(items) / Decimal(len(items))).quantize(DECIMAL_SCALE, rounding=ROUND_HALF_UP)


def _max(values: Iterable[Decimal]) -> Optional[Decimal]:
    items = list(values)
    if not items:
        return None
    return max(items).quantize(DECIMAL_SCALE, rounding=ROUND_HALF_UP)


def _count_list(value: Any) -> Optional[int]:
    return len(value) if isinstance(value, list) else None


def _load_tone_summary(raw_value: Any, warnings: List[str]) -> Optional[Dict[str, Any]]:
    if raw_value is None:
        warnings.append("tone_summary_json is missing; skipping row")
        return None
    if isinstance(raw_value, dict):
        return raw_value
    if isinstance(raw_value, str):
        try:
            parsed = json.loads(raw_value)
        except json.JSONDecodeError as exc:
            warnings.append(f"tone_summary_json is invalid JSON: {exc}; skipping row")
            return None
        if isinstance(parsed, dict):
            return parsed
    warnings.append("tone_summary_json is not a JSON object; skipping row")
    return None


def _segment_values(
    segments: List[Any],
    field_name: str,
    warnings: List[str],
) -> List[Decimal]:
    values: List[Decimal] = []
    for index, item in enumerate(segments):
        if not isinstance(item, dict):
            warnings.append(f"segments[{index}] is not an object; ignored")
            continue
        value = _safe_decimal(item.get(field_name), f"segments[{index}].{field_name}", warnings)
        if value is not None:
            values.append(value)
    return values


def extract_features(source: SourceAnalysisRow, computed_at: datetime) -> ExtractionResult:
    warnings: List[str] = []
    normalized_period = _normalize_period(source.fiscal_period_label)
    if normalized_period is None:
        return ExtractionResult(
            row=None,
            warnings=(f"{source.symbol} {source.fiscal_period_label}: invalid fiscal period label",),
        )

    summary = _load_tone_summary(source.tone_summary_json, warnings)
    if summary is None:
        return ExtractionResult(row=None, warnings=tuple(warnings))

    segment_count = _safe_int(summary.get("segmentCount"), "segmentCount", warnings)
    positive_count = _safe_int(summary.get("positiveSegmentCount"), "positiveSegmentCount", warnings)
    mixed_count = _safe_int(summary.get("mixedSegmentCount"), "mixedSegmentCount", warnings)
    negative_count = _safe_int(summary.get("negativeSegmentCount"), "negativeSegmentCount", warnings)

    if segment_count == 0:
        warnings.append("segmentCount is 0; segment ratios set to NULL")

    segments_raw = summary.get("segments")
    segments = segments_raw if isinstance(segments_raw, list) else []
    if segments_raw is None:
        warnings.append("segments array is missing; segment averages set to NULL")
    elif not isinstance(segments_raw, list):
        warnings.append("segments value is not an array; segment averages set to NULL")
    elif not segments:
        warnings.append("segments array is empty; segment averages set to NULL")
    elif segment_count is not None and segment_count != len(segments):
        warnings.append(
            f"segmentCount={segment_count} differs from actual segments={len(segments)}"
        )

    positive_scores = _segment_values(segments, "positiveScore", warnings)
    neutral_scores = _segment_values(segments, "neutralScore", warnings)
    negative_scores = _segment_values(segments, "negativeScore", warnings)
    score_values = _segment_values(segments, "score", warnings)
    confidence_values = _segment_values(segments, "confidence", warnings)
    risk_values = _segment_values(segments, "riskSignalScore", warnings)
    guidance_values = _segment_values(segments, "guidanceSignalScore", warnings)
    cautious_guidance_values = _segment_values(
        segments,
        "cautiousGuidanceSignalScore",
        warnings,
    )

    row = FeatureRow(
        symbol=source.symbol.strip().upper(),
        fiscal_period_label=source.fiscal_period_label,
        normalized_fiscal_period_label=normalized_period,
        earnings_ai_analysis_id=source.id,
        overall_tone=_short_text(source.overall_tone, 32),
        finbert_overall_tone=_short_text(summary.get("overallTone"), 32),
        finbert_aggregate_score=_safe_decimal(
            summary.get("aggregateScore"),
            "aggregateScore",
            warnings,
        ),
        segment_count=segment_count,
        positive_segment_count=positive_count,
        mixed_segment_count=mixed_count,
        negative_segment_count=negative_count,
        positive_segment_ratio=_ratio(positive_count, segment_count),
        mixed_segment_ratio=_ratio(mixed_count, segment_count),
        negative_segment_ratio=_ratio(negative_count, segment_count),
        avg_positive_score=_mean(positive_scores),
        avg_neutral_score=_mean(neutral_scores),
        avg_negative_score=_mean(negative_scores),
        avg_pos_minus_neg_score=_mean(score_values),
        avg_confidence=_mean(confidence_values),
        avg_risk_signal_score=_mean(risk_values),
        max_risk_signal_score=_max(risk_values),
        avg_guidance_signal_score=_mean(guidance_values),
        max_guidance_signal_score=_max(guidance_values),
        avg_cautious_guidance_signal_score=_mean(cautious_guidance_values),
        max_cautious_guidance_signal_score=_max(cautious_guidance_values),
        positive_signal_count=_count_list(summary.get("topPositiveSignals")),
        negative_signal_count=_count_list(summary.get("topNegativeSignals")),
        guidance_signal_count=_count_list(summary.get("topGuidanceSignals")),
        cautious_guidance_signal_count=_count_list(summary.get("topCautiousGuidanceSignals")),
        source_tone_analyzer=_short_text(source.tone_analyzer, 64),
        source_model_name=_short_text(source.model_name or summary.get("modelName"), 128),
        source_prompt_version=_short_text(source.prompt_version, 32),
        source_analysis_updated_at=source.updated_at,
        computed_at=computed_at,
    )
    return ExtractionResult(row=row, warnings=tuple(warnings))


def _ensure_table(db) -> None:
    db.execute(CREATE_TABLE_SQL)


def _list_all_symbols(db) -> List[str]:
    rows = db.execute(
        "SELECT DISTINCT symbol FROM earnings_ai_analysis ORDER BY symbol"
    ) or []
    return [row[0] for row in rows]


def _select_source_rows(
    db,
    symbols: Sequence[str],
    start_period: Optional[str],
    end_period: Optional[str],
) -> List[SourceAnalysisRow]:
    where = []
    params: List[Any] = []
    if symbols:
        placeholders = ", ".join(["%s"] * len(symbols))
        where.append(f"symbol IN ({placeholders})")
        params.extend(symbols)

    sql = """
        SELECT
            id, symbol, fiscal_period_label, tone_summary_json, overall_tone,
            tone_analyzer, model_name, prompt_version, updated_at
        FROM earnings_ai_analysis
    """
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY symbol, fiscal_period_label"

    normalized_start = _normalize_period(start_period) if start_period else None
    normalized_end = _normalize_period(end_period) if end_period else None

    rows = db.execute(sql, tuple(params)) or []
    result: List[SourceAnalysisRow] = []
    for row in rows:
        source = SourceAnalysisRow(
            id=row[0],
            symbol=str(row[1]).strip().upper(),
            fiscal_period_label=str(row[2]).strip(),
            tone_summary_json=row[3],
            overall_tone=row[4],
            tone_analyzer=row[5],
            model_name=row[6],
            prompt_version=row[7],
            updated_at=row[8],
        )
        normalized_period = _normalize_period(source.fiscal_period_label)
        if normalized_period is None:
            continue
        if normalized_start and normalized_period < normalized_start:
            continue
        if normalized_end and normalized_period > normalized_end:
            continue
        result.append(source)
    return result


def _persist(db, rows: Sequence[FeatureRow]) -> int:
    if not rows:
        return 0
    return db.executemany(UPSERT_SQL, [row.to_params() for row in rows])


def run_for_symbols(
    symbols: Sequence[str],
    start_period: Optional[str] = None,
    end_period: Optional[str] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    db = get_db_manager()
    _ensure_table(db)

    normalized_symbols = [symbol.strip().upper() for symbol in symbols if symbol.strip()]
    source_rows = _select_source_rows(db, normalized_symbols, start_period, end_period)
    computed_at = datetime.now()

    feature_rows: List[FeatureRow] = []
    warnings_count = 0
    skipped = 0
    by_symbol: Dict[str, Dict[str, int]] = {}

    for source in source_rows:
        result = extract_features(source, computed_at)
        symbol_summary = by_symbol.setdefault(
            source.symbol,
            {"read": 0, "computed": 0, "skipped": 0, "warnings": 0},
        )
        symbol_summary["read"] += 1
        for warning in result.warnings:
            warnings_count += 1
            symbol_summary["warnings"] += 1
            logger.warning("%s %s: %s", source.symbol, source.fiscal_period_label, warning)
        if result.row is None:
            skipped += 1
            symbol_summary["skipped"] += 1
            continue
        feature_rows.append(result.row)
        symbol_summary["computed"] += 1

    if dry_run:
        written = 0
        logger.info(
            "[DRY RUN] %d source rows read, %d feature rows computed, %d skipped",
            len(source_rows),
            len(feature_rows),
            skipped,
        )
    else:
        written = _persist(db, feature_rows)
        logger.info(
            "%d source rows read, %d feature rows computed, %d skipped, rowcount=%d",
            len(source_rows),
            len(feature_rows),
            skipped,
            written,
        )

    return {
        "read": len(source_rows),
        "computed": len(feature_rows),
        "written": written,
        "skipped": skipped,
        "warnings": warnings_count,
        "symbols": by_symbol,
    }


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Derive numeric FinBERT sentiment features from earnings_ai_analysis."
    )
    parser.add_argument(
        "--symbol", action="append", dest="symbols",
        help="Symbol to process (repeatable). Use --all-symbols for everything.",
    )
    parser.add_argument(
        "--all-symbols", action="store_true",
        help="Process every distinct symbol present in earnings_ai_analysis.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Compute and log counts without writing.",
    )
    parser.add_argument("--start-period", help="Optional lower fiscal period bound, e.g. 2025Q1.")
    parser.add_argument("--end-period", help="Optional upper fiscal period bound, e.g. 2026Q1.")
    args = parser.parse_args()

    for label, value in (("--start-period", args.start_period), ("--end-period", args.end_period)):
        if value and _normalize_period(value) is None:
            parser.error(f"{label} must be YYYYQn or FY2025Qn style, got {value!r}")

    db = get_db_manager()
    if args.all_symbols:
        symbols = _list_all_symbols(db)
    elif args.symbols:
        symbols = [symbol.strip().upper() for symbol in args.symbols if symbol.strip()]
    else:
        symbols = list(PIPELINE_SYMBOLS)
        logger.info(
            "No --symbol or --all-symbols given; defaulting to PIPELINE_SYMBOLS=%s",
            symbols,
        )

    if not symbols:
        parser.error("No symbols to process.")

    summary = run_for_symbols(
        symbols=symbols,
        start_period=args.start_period,
        end_period=args.end_period,
        dry_run=args.dry_run,
    )

    print(f"\n{'=' * 64}")
    print(f"earnings_sentiment_features {'(dry run) ' if args.dry_run else ''}complete.")
    print(f"  Symbols:      {len(summary['symbols'])}")
    print(f"  Source rows:  {summary['read']}")
    print(f"  Computed:     {summary['computed']}")
    print(f"  Skipped:      {summary['skipped']}")
    print(f"  Warnings:     {summary['warnings']}")
    if not args.dry_run:
        print(f"  Rowcount:     {summary['written']}")
    print(f"{'=' * 64}\n")


if __name__ == "__main__":
    main()
