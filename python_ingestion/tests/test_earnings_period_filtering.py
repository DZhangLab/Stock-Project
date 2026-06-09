"""Tests for fiscal-period selection used by earnings backfill jobs."""
from python_ingestion.jobs.earnings_commentary import EarningsCommentaryCollector


def _payload():
    return {
        "quarterlyEarnings": [
            {"fiscalDateEnding": "2025-03-29", "reportedDate": "2025-05-01"},
            {"fiscalDateEnding": "2024-12-28", "reportedDate": "2025-01-30"},
            {"fiscalDateEnding": "2024-09-28", "reportedDate": "2024-10-31"},
            {"fiscalDateEnding": "2024-06-29", "reportedDate": "2024-08-01"},
            {"fiscalDateEnding": "2024-03-30", "reportedDate": "2024-05-02"},
            {"fiscalDateEnding": "2023-12-30", "reportedDate": "2024-02-01"},
        ]
    }


def test_normalize_period_label():
    assert EarningsCommentaryCollector._normalize_period_label("2024Q1") == "2024Q1"
    assert EarningsCommentaryCollector._normalize_period_label("fy2024q4") == "2024Q4"
    assert EarningsCommentaryCollector._normalize_period_label("2024Q5") is None
    assert EarningsCommentaryCollector._normalize_period_label("2024-01") is None


def test_default_selection_remains_latest_four():
    rows = EarningsCommentaryCollector._select_earnings_rows(_payload())
    assert [row["fiscalDateEnding"] for row in rows] == [
        "2025-03-29",
        "2024-12-28",
        "2024-09-28",
        "2024-06-29",
    ]


def test_selection_uses_inclusive_period_range():
    rows = EarningsCommentaryCollector._select_earnings_rows(
        _payload(),
        start_period="2024Q1",
        end_period="2024Q4",
    )
    assert [row["fiscalDateEnding"] for row in rows] == [
        "2024-12-28",
        "2024-09-28",
        "2024-06-29",
        "2024-03-30",
    ]


def test_selection_supports_single_open_bound():
    rows = EarningsCommentaryCollector._select_earnings_rows(
        _payload(),
        end_period="2023Q4",
    )
    assert [row["fiscalDateEnding"] for row in rows] == ["2023-12-30"]
