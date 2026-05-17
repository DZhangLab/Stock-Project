from datetime import datetime
from decimal import Decimal

from python_ingestion.jobs.earnings_sentiment_features import (
    SourceAnalysisRow,
    _normalize_period,
    _ratio,
    _safe_decimal,
    extract_features,
)


def _source_row(tone_summary):
    return SourceAnalysisRow(
        id=123,
        symbol="aapl",
        fiscal_period_label="FY2025Q4",
        tone_summary_json=tone_summary,
        overall_tone="positive",
        tone_analyzer="prosusai_finbert_v1",
        model_name="gpt-test",
        prompt_version="earnings_ai_analysis_v3",
        updated_at=datetime(2026, 1, 1, 12, 0, 0),
    )


def test_normalize_period_strips_fy_prefix():
    assert _normalize_period("FY2025Q4") == "2025Q4"
    assert _normalize_period("2025q4") == "2025Q4"
    assert _normalize_period("bad") is None


def test_safe_decimal_rejects_invalid_and_non_finite_values():
    warnings = []
    assert _safe_decimal("1.234567895", "field", warnings) == Decimal("1.23456790")
    assert _safe_decimal("nan", "field", warnings) is None
    assert _safe_decimal("not-a-number", "field", warnings) is None
    assert len(warnings) == 2


def test_ratio_returns_null_when_segment_count_is_zero():
    assert _ratio(1, 0) is None
    assert _ratio(1, None) is None
    assert _ratio(1, 4) == Decimal("0.25000000")


def test_extract_features_from_minimal_valid_fixture():
    tone_summary = {
        "overallTone": "positive",
        "aggregateScore": 3.5,
        "segmentCount": 2,
        "positiveSegmentCount": 1,
        "mixedSegmentCount": 1,
        "negativeSegmentCount": 0,
        "segments": [
            {
                "positiveScore": 0.8,
                "neutralScore": 0.1,
                "negativeScore": 0.1,
                "score": 0.7,
                "confidence": 0.8,
                "riskSignalScore": 0.0,
                "guidanceSignalScore": 1.0,
            },
            {
                "positiveScore": 0.2,
                "neutralScore": 0.7,
                "negativeScore": 0.1,
                "score": 0.1,
                "confidence": 0.7,
                "riskSignalScore": 2.0,
                "guidanceSignalScore": 0.0,
            },
        ],
        "topPositiveSignals": [{}],
        "topNegativeSignals": [{}, {}],
        "topGuidanceSignals": [],
        "topCautiousGuidanceSignals": [{}],
    }

    result = extract_features(_source_row(tone_summary), datetime(2026, 1, 2))

    assert result.row is not None
    assert result.warnings == ()
    assert result.row.symbol == "AAPL"
    assert result.row.normalized_fiscal_period_label == "2025Q4"
    assert result.row.positive_segment_ratio == Decimal("0.50000000")
    assert result.row.avg_positive_score == Decimal("0.50000000")
    assert result.row.avg_negative_score == Decimal("0.10000000")
    assert result.row.avg_pos_minus_neg_score == Decimal("0.40000000")
    assert result.row.max_risk_signal_score == Decimal("2.00000000")
    assert result.row.negative_signal_count == 2


def test_extract_features_persists_top_level_fields_with_empty_segments():
    tone_summary = {
        "overallTone": "positive",
        "aggregateScore": 1.25,
        "segmentCount": 0,
        "positiveSegmentCount": 0,
        "mixedSegmentCount": 0,
        "negativeSegmentCount": 0,
        "segments": [],
    }

    result = extract_features(_source_row(tone_summary), datetime(2026, 1, 2))

    assert result.row is not None
    assert result.row.finbert_aggregate_score == Decimal("1.25000000")
    assert result.row.positive_segment_ratio is None
    assert result.row.avg_positive_score is None
    assert any("segments array is empty" in warning for warning in result.warnings)
