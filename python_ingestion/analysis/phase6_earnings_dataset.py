"""
Read-only Phase 6 earnings analysis dataset checkpoint.

This module builds an in-memory exploratory dataset by joining
earnings_event_outcome to earnings_sentiment_features. It prints diagnostics,
descriptive statistics, correlations, and bucket summaries. It does not write
to the database, create files, call external APIs, run ingestion jobs, or
implement regression/LOSO validation.
"""
from __future__ import annotations

import argparse
import math
import statistics
from collections import Counter, defaultdict
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from ..db import get_db_manager


RETURN_COLUMNS = ("ret_1d", "ret_3d", "ret_5d", "ret_20d")
TONE_COLUMNS = ("ai_overall_tone_at_event", "overall_tone", "finbert_overall_tone")
CORE_FEATURE_COLUMNS = (
    "surprise_pct_at_event",
    "finbert_aggregate_score",
    "positive_segment_ratio",
    "mixed_segment_ratio",
    "negative_segment_ratio",
    "avg_positive_score",
    "avg_negative_score",
    "avg_pos_minus_neg_score",
    "avg_confidence",
    "avg_risk_signal_score",
    "max_risk_signal_score",
    "avg_guidance_signal_score",
    "max_guidance_signal_score",
    "guidance_signal_count",
    "cautious_guidance_signal_count",
)
CORRELATION_FEATURE_COLUMNS = (
    "surprise_pct_at_event",
    "surprise_pct_capped",
    "finbert_aggregate_score",
    "positive_segment_ratio",
    "mixed_segment_ratio",
    "negative_segment_ratio",
    "avg_positive_score",
    "avg_negative_score",
    "avg_pos_minus_neg_score",
    "avg_confidence",
    "avg_risk_signal_score",
    "max_risk_signal_score",
    "avg_guidance_signal_score",
    "max_guidance_signal_score",
    "guidance_signal_count",
    "cautious_guidance_signal_count",
)
TERCILE_FEATURE_COLUMNS = (
    "positive_segment_ratio",
    "negative_segment_ratio",
    "avg_pos_minus_neg_score",
    "avg_risk_signal_score",
    "guidance_signal_count",
    "cautious_guidance_signal_count",
)

BASE_SELECT_SQL = """
SELECT
    e.symbol,
    e.fiscal_period_label,
    e.normalized_fiscal_period_label,
    e.event_date,
    e.quality_flag,
    e.ret_1d,
    e.ret_3d,
    e.ret_5d,
    e.ret_20d,
    e.surprise_pct_at_event,
    e.ai_overall_tone_at_event,
    f.overall_tone,
    f.finbert_overall_tone,
    f.finbert_aggregate_score,
    f.positive_segment_ratio,
    f.mixed_segment_ratio,
    f.negative_segment_ratio,
    f.avg_positive_score,
    f.avg_negative_score,
    f.avg_pos_minus_neg_score,
    f.avg_confidence,
    f.avg_risk_signal_score,
    f.max_risk_signal_score,
    f.avg_guidance_signal_score,
    f.max_guidance_signal_score,
    f.guidance_signal_count,
    f.cautious_guidance_signal_count
FROM earnings_event_outcome e
JOIN earnings_sentiment_features f
  ON e.symbol = f.symbol
 AND e.normalized_fiscal_period_label = f.normalized_fiscal_period_label
WHERE {quality_filter}
  AND e.ret_1d IS NOT NULL
  AND e.ret_3d IS NOT NULL
  AND e.ret_5d IS NOT NULL
  AND e.ret_20d IS NOT NULL
ORDER BY e.symbol, e.normalized_fiscal_period_label
"""


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, Decimal):
        value = float(value)
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _fmt(value: Any, digits: int = 6) -> str:
    number = _to_float(value)
    if number is None:
        return "NULL"
    return f"{number:.{digits}f}"


def _mean(values: Iterable[Any]) -> Optional[float]:
    numbers = [_to_float(value) for value in values]
    numbers = [value for value in numbers if value is not None]
    if not numbers:
        return None
    return sum(numbers) / len(numbers)


def _stats(values: Iterable[Any]) -> Dict[str, Any]:
    numbers = [_to_float(value) for value in values]
    numbers = [value for value in numbers if value is not None]
    if not numbers:
        return {"n": 0, "min": None, "mean": None, "max": None, "stddev": None}
    return {
        "n": len(numbers),
        "min": min(numbers),
        "mean": sum(numbers) / len(numbers),
        "max": max(numbers),
        "stddev": statistics.pstdev(numbers) if len(numbers) > 1 else 0.0,
    }


def _pearson(xs: Sequence[Any], ys: Sequence[Any]) -> Tuple[int, Optional[float]]:
    pairs = [(_to_float(x), _to_float(y)) for x, y in zip(xs, ys)]
    pairs = [(x, y) for x, y in pairs if x is not None and y is not None]
    n = len(pairs)
    if n < 3:
        return n, None

    x_mean = sum(x for x, _ in pairs) / n
    y_mean = sum(y for _, y in pairs) / n
    x_ss = sum((x - x_mean) ** 2 for x, _ in pairs)
    y_ss = sum((y - y_mean) ** 2 for _, y in pairs)
    if x_ss == 0 or y_ss == 0:
        return n, None

    covariance = sum((x - x_mean) * (y - y_mean) for x, y in pairs)
    return n, covariance / math.sqrt(x_ss * y_ss)


def _surprise_bucket(value: Any) -> Optional[str]:
    surprise = _to_float(value)
    if surprise is None:
        return None
    if surprise < 0:
        return "negative_surprise"
    if surprise < 5:
        return "small_positive_surprise"
    if surprise < 10:
        return "medium_positive_surprise"
    return "large_positive_surprise"


def _surprise_direction(value: Any) -> Optional[str]:
    surprise = _to_float(value)
    if surprise is None:
        return None
    return "negative" if surprise < 0 else "nonnegative"


def _cap(value: Any, low: float, high: float) -> Optional[float]:
    number = _to_float(value)
    if number is None:
        return None
    return max(low, min(high, number))


def _table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> None:
    print("| " + " | ".join(headers) + " |")
    print("| " + " | ".join(["---"] * len(headers)) + " |")
    if not rows:
        print("| " + " | ".join(["(none)"] + [""] * (len(headers) - 1)) + " |")
        print()
        return
    for row in rows:
        print("| " + " | ".join(str(value) for value in row) + " |")
    print()


def _fetch_dataset(include_non_excluded: bool) -> List[Dict[str, Any]]:
    quality_filter = "e.quality_flag <> 'excluded'" if include_non_excluded else "e.quality_flag = 'full'"
    sql = BASE_SELECT_SQL.format(quality_filter=quality_filter)
    rows = get_db_manager().execute(sql) or []
    columns = (
        "symbol",
        "fiscal_period_label",
        "normalized_fiscal_period_label",
        "event_date",
        "quality_flag",
        *RETURN_COLUMNS,
        "surprise_pct_at_event",
        *TONE_COLUMNS,
        "finbert_aggregate_score",
        "positive_segment_ratio",
        "mixed_segment_ratio",
        "negative_segment_ratio",
        "avg_positive_score",
        "avg_negative_score",
        "avg_pos_minus_neg_score",
        "avg_confidence",
        "avg_risk_signal_score",
        "max_risk_signal_score",
        "avg_guidance_signal_score",
        "max_guidance_signal_score",
        "guidance_signal_count",
        "cautious_guidance_signal_count",
    )
    return [dict(zip(columns, row)) for row in rows]


def _apply_transforms(rows: List[Dict[str, Any]]) -> None:
    for row in rows:
        surprise = _to_float(row.get("surprise_pct_at_event"))
        row["surprise_bucket"] = _surprise_bucket(surprise)
        row["surprise_direction"] = _surprise_direction(surprise)
        row["is_surprise_outlier"] = surprise is not None and abs(surprise) >= 100
        row["surprise_pct_capped"] = _cap(surprise, -100, 100)


def _tercile_labels(rows: Sequence[Dict[str, Any]], feature: str) -> Dict[Tuple[str, str], str]:
    valid_rows = [row for row in rows if _to_float(row.get(feature)) is not None]
    valid_rows.sort(
        key=lambda row: (
            _to_float(row.get(feature)),
            str(row.get("symbol")),
            str(row.get("normalized_fiscal_period_label")),
        )
    )

    labels: Dict[Tuple[str, str], str] = {}
    if not valid_rows:
        return labels

    names = ("low", "middle", "high")
    total = len(valid_rows)
    for index, row in enumerate(valid_rows):
        tile = min(math.floor(index * 3 / total), 2)
        key = (str(row.get("symbol")), str(row.get("normalized_fiscal_period_label")))
        labels[key] = names[tile]
    return labels


def _grouped_average_rows(
    grouped_rows: Dict[str, List[Dict[str, Any]]],
    return_columns: Sequence[str],
) -> List[List[Any]]:
    output: List[List[Any]] = []
    for bucket, rows in grouped_rows.items():
        output.append(
            [
                bucket,
                len(rows),
                *[_fmt(_mean(row.get(column) for row in rows)) for column in return_columns],
            ]
        )
    return output


def print_preview(rows: Sequence[Dict[str, Any]], max_rows: int) -> None:
    preview_rows = rows[: max(0, max_rows)]
    _table(
        [
            "symbol",
            "period",
            "event_date",
            "surprise",
            "surprise_bucket",
            "ret_5d",
            "ret_20d",
        ],
        [
            [
                row.get("symbol"),
                row.get("normalized_fiscal_period_label"),
                row.get("event_date"),
                _fmt(row.get("surprise_pct_at_event")),
                row.get("surprise_bucket"),
                _fmt(row.get("ret_5d")),
                _fmt(row.get("ret_20d")),
            ]
            for row in preview_rows
        ],
    )


def print_diagnostics(rows: Sequence[Dict[str, Any]], max_rows_preview: int) -> None:
    print("## Diagnostics")
    _table(
        ["metric", "value"],
        [
            ["primary_rows", len(rows)],
            ["surprise_outlier_rows", sum(1 for row in rows if row["is_surprise_outlier"])],
        ],
    )

    by_symbol = Counter(str(row.get("symbol")) for row in rows)
    _table(["symbol", "rows"], sorted(by_symbol.items()))

    by_period = Counter(str(row.get("normalized_fiscal_period_label")) for row in rows)
    _table(["fiscal_period", "rows"], sorted(by_period.items(), reverse=True))

    duplicate_counts = Counter(
        (str(row.get("symbol")), str(row.get("normalized_fiscal_period_label"))) for row in rows
    )
    duplicate_groups = [
        (symbol, period, count)
        for (symbol, period), count in duplicate_counts.items()
        if count > 1
    ]
    _table(["symbol", "period", "rows"], sorted(duplicate_groups))

    null_fields = (*RETURN_COLUMNS, *CORE_FEATURE_COLUMNS, "surprise_pct_capped")
    _table(
        ["field", "null_rows"],
        [[field, sum(1 for row in rows if row.get(field) is None)] for field in null_fields],
    )

    ratio_columns = ("positive_segment_ratio", "mixed_segment_ratio", "negative_segment_ratio")
    invalid_ratio_rows = 0
    ratio_sum_far_rows = 0
    for row in rows:
        ratios = [_to_float(row.get(column)) for column in ratio_columns]
        if any(value is not None and (value < 0 or value > 1) for value in ratios):
            invalid_ratio_rows += 1
        if all(value is not None for value in ratios) and abs(sum(ratios) - 1.0) > 0.01:
            ratio_sum_far_rows += 1
    _table(
        ["check", "rows"],
        [
            ["ratio values outside [0, 1]", invalid_ratio_rows],
            ["ratio sum far from 1 (>0.01)", ratio_sum_far_rows],
        ],
    )

    tone_rows: List[List[Any]] = []
    for column in TONE_COLUMNS:
        for tone, count in sorted(Counter(row.get(column) for row in rows).items()):
            tone_rows.append([column, tone, count])
    _table(["tone_field", "tone", "rows"], tone_rows)

    if all(len(Counter(row.get(column) for row in rows)) == 1 for column in TONE_COLUMNS):
        print(
            "Categorical tone has no variation and should remain diagnostic-only, "
            "not a main explanatory variable.\n"
        )

    outliers = sorted(
        [row for row in rows if row["is_surprise_outlier"]],
        key=lambda row: abs(_to_float(row.get("surprise_pct_at_event")) or 0),
        reverse=True,
    )
    _table(
        ["symbol", "period", "event_date", "surprise", "ret_5d", "ret_20d"],
        [
            [
                row.get("symbol"),
                row.get("normalized_fiscal_period_label"),
                row.get("event_date"),
                _fmt(row.get("surprise_pct_at_event")),
                _fmt(row.get("ret_5d")),
                _fmt(row.get("ret_20d")),
            ]
            for row in outliers[:max_rows_preview]
        ],
    )


def print_descriptive_statistics(rows: Sequence[Dict[str, Any]]) -> None:
    print("## Descriptive Statistics")
    fields = (*RETURN_COLUMNS, *CORE_FEATURE_COLUMNS, "surprise_pct_capped")
    output = []
    for field in fields:
        values = _stats(row.get(field) for row in rows)
        output.append(
            [
                field,
                values["n"],
                _fmt(values["min"]),
                _fmt(values["mean"]),
                _fmt(values["max"]),
                _fmt(values["stddev"]),
            ]
        )
    _table(["field", "n", "min", "mean", "max", "stddev"], output)


def correlation_rows(rows: Sequence[Dict[str, Any]]) -> List[List[Any]]:
    output: List[List[Any]] = []
    for feature in CORRELATION_FEATURE_COLUMNS:
        for return_column in RETURN_COLUMNS:
            n, value = _pearson(
                [row.get(feature) for row in rows],
                [row.get(return_column) for row in rows],
            )
            output.append([feature, return_column, n, _fmt(value) if value is not None else "NULL"])
    return output


def print_correlations(rows: Sequence[Dict[str, Any]]) -> None:
    print("## Exploratory Correlations")
    output = correlation_rows(rows)
    _table(["feature", "return", "n", "pearson_corr"], output)

    valid = [
        (feature, return_column, n, _to_float(value))
        for feature, return_column, n, value in output
        if _to_float(value) is not None
    ]
    if not valid:
        return

    strongest_positive = max(valid, key=lambda item: item[3])
    strongest_negative = min(valid, key=lambda item: item[3])
    strongest_absolute = max(valid, key=lambda item: abs(item[3]))
    _table(
        ["relationship", "feature", "return", "n", "pearson_corr"],
        [
            [
                "strongest_positive",
                strongest_positive[0],
                strongest_positive[1],
                strongest_positive[2],
                _fmt(strongest_positive[3]),
            ],
            [
                "strongest_negative",
                strongest_negative[0],
                strongest_negative[1],
                strongest_negative[2],
                _fmt(strongest_negative[3]),
            ],
            [
                "strongest_absolute",
                strongest_absolute[0],
                strongest_absolute[1],
                strongest_absolute[2],
                _fmt(strongest_absolute[3]),
            ],
        ],
    )
    print("These are exploratory correlations only, not predictive or causal evidence.\n")


def print_bucket_summaries(rows: Sequence[Dict[str, Any]], min_bucket_size: int) -> None:
    print("## Bucket Summaries")

    ordered_surprise_buckets = (
        "negative_surprise",
        "small_positive_surprise",
        "medium_positive_surprise",
        "large_positive_surprise",
    )
    surprise_groups: Dict[str, List[Dict[str, Any]]] = {
        bucket: [] for bucket in ordered_surprise_buckets
    }
    for row in rows:
        bucket = row.get("surprise_bucket")
        if bucket in surprise_groups:
            surprise_groups[bucket].append(row)
    _table(
        ["surprise_bucket", "n", "avg_ret_1d", "avg_ret_3d", "avg_ret_5d", "avg_ret_20d"],
        _grouped_average_rows(surprise_groups, RETURN_COLUMNS),
    )

    for feature in TERCILE_FEATURE_COLUMNS:
        labels = _tercile_labels(rows, feature)
        groups: Dict[str, List[Dict[str, Any]]] = {"low": [], "middle": [], "high": []}
        for row in rows:
            key = (str(row.get("symbol")), str(row.get("normalized_fiscal_period_label")))
            label = labels.get(key)
            if label:
                groups[label].append(row)

        print(f"### Terciles: {feature}")
        summary = _grouped_average_rows(groups, ("ret_5d", "ret_20d"))
        _table(["bucket", "n", "avg_ret_5d", "avg_ret_20d"], summary)

    labels = _tercile_labels(rows, "avg_pos_minus_neg_score")
    two_dimensional: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = (str(row.get("symbol")), str(row.get("normalized_fiscal_period_label")))
        tercile = labels.get(key)
        direction = row.get("surprise_direction")
        if tercile and direction:
            two_dimensional[f"{direction} / {tercile}"].append(row)

    print("### Two-dimensional: surprise direction x avg_pos_minus_neg_score tercile")
    two_dimensional_rows = []
    for bucket in sorted(two_dimensional):
        bucket_rows = two_dimensional[bucket]
        note = "" if len(bucket_rows) >= min_bucket_size else "small_n"
        two_dimensional_rows.append(
            [
                bucket,
                len(bucket_rows),
                _fmt(_mean(row.get("ret_5d") for row in bucket_rows)),
                _fmt(_mean(row.get("ret_20d") for row in bucket_rows)),
                note,
            ]
        )
    _table(["bucket", "n", "avg_ret_5d", "avg_ret_20d", "note"], two_dimensional_rows)


def print_robustness(rows: Sequence[Dict[str, Any]]) -> None:
    print("## Surprise Robustness")
    without_outliers = [row for row in rows if not row["is_surprise_outlier"]]

    raw_n_5d, raw_5d = _pearson(
        [row.get("surprise_pct_at_event") for row in rows],
        [row.get("ret_5d") for row in rows],
    )
    capped_n_5d, capped_5d = _pearson(
        [row.get("surprise_pct_capped") for row in rows],
        [row.get("ret_5d") for row in rows],
    )
    excluded_n_5d, excluded_5d = _pearson(
        [row.get("surprise_pct_at_event") for row in without_outliers],
        [row.get("ret_5d") for row in without_outliers],
    )

    raw_n_20d, raw_20d = _pearson(
        [row.get("surprise_pct_at_event") for row in rows],
        [row.get("ret_20d") for row in rows],
    )
    capped_n_20d, capped_20d = _pearson(
        [row.get("surprise_pct_capped") for row in rows],
        [row.get("ret_20d") for row in rows],
    )
    excluded_n_20d, excluded_20d = _pearson(
        [row.get("surprise_pct_at_event") for row in without_outliers],
        [row.get("ret_20d") for row in without_outliers],
    )

    _table(
        ["mode", "n_ret_5d", "corr_ret_5d", "n_ret_20d", "corr_ret_20d"],
        [
            ["raw_surprise", raw_n_5d, _fmt(raw_5d) if raw_5d is not None else "NULL", raw_n_20d, _fmt(raw_20d) if raw_20d is not None else "NULL"],
            ["capped_surprise", capped_n_5d, _fmt(capped_5d) if capped_5d is not None else "NULL", capped_n_20d, _fmt(capped_20d) if capped_20d is not None else "NULL"],
            ["exclude_outliers", excluded_n_5d, _fmt(excluded_5d) if excluded_5d is not None else "NULL", excluded_n_20d, _fmt(excluded_20d) if excluded_20d is not None else "NULL"],
        ],
    )

    if raw_5d is not None and capped_5d is not None and abs(raw_5d - capped_5d) > 0.05:
        print("Surprise correlation is sensitive to extreme surprise handling.\n")
    else:
        print("Surprise correlation is not materially changed by capping in this checkpoint.\n")


def run_report(
    min_bucket_size: int,
    include_non_excluded: bool,
    exclude_surprise_outliers: bool,
    max_rows_preview: int,
) -> List[Dict[str, Any]]:
    rows = _fetch_dataset(include_non_excluded=include_non_excluded)
    _apply_transforms(rows)

    if exclude_surprise_outliers:
        rows = [row for row in rows if not row["is_surprise_outlier"]]

    dataset_label = "non-excluded" if include_non_excluded else "full-only"
    if exclude_surprise_outliers:
        dataset_label += ", surprise outliers excluded"

    print("\n# Phase 6 Earnings Analysis Dataset")
    print(f"Dataset mode: {dataset_label}")
    print("This report is structured exploratory analysis only, not regression or LOSO validation.\n")

    print("## Dataset Preview")
    print_preview(rows, max_rows_preview)
    print_diagnostics(rows, max_rows_preview)
    print_descriptive_statistics(rows)
    print_correlations(rows)
    print_bucket_summaries(rows, min_bucket_size)
    print_robustness(rows)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build and report the read-only Phase 6 earnings analysis dataset."
    )
    parser.add_argument(
        "--min-bucket-size",
        type=int,
        default=10,
        help="Minimum bucket size for interpretation notes.",
    )
    parser.add_argument(
        "--include-non-excluded",
        action="store_true",
        help="Use quality_flag <> 'excluded' instead of full-only rows.",
    )
    parser.add_argument(
        "--exclude-surprise-outliers",
        action="store_true",
        help="Exclude rows where abs(surprise_pct_at_event) >= 100.",
    )
    parser.add_argument(
        "--max-rows-preview",
        type=int,
        default=10,
        help="Maximum rows to show in preview and outlier tables.",
    )
    args = parser.parse_args()

    run_report(
        min_bucket_size=args.min_bucket_size,
        include_non_excluded=args.include_non_excluded,
        exclude_surprise_outliers=args.exclude_surprise_outliers,
        max_rows_preview=args.max_rows_preview,
    )


if __name__ == "__main__":
    main()
