"""
Phase 3 HAR-RV volatility forecasting and model evaluation job.

This job reads daily log returns from daily_returns, builds one-day-ahead
HAR-RV features from historical variance proxies only, writes eligible
HAR forecasts back to daily_volatility, and persists walk-forward
out-of-sample evaluation metrics into volatility_model_evaluation.

Target definition
-----------------
The supervised target is NOT next-day realized_vol_5d.

Instead the one-day realized-variance proxy is derived directly from
close-to-close log returns:

    rv1_t = (log_return_t)^2

The HAR model is fit on variance scale:

    E[rv1_{t+1}] = beta0 + beta_d * RV_d_t + beta_w * RV_w_t + beta_m * RV_m_t

with features available as of date t only:
    RV_d_t = rv1_t
    RV_w_t = mean(rv1_t, ..., rv1_{t-4})
    RV_m_t = mean(rv1_t, ..., rv1_{t-21})

For storage in daily_volatility.har_rv_forecast_1d the predicted next-day
variance proxy is converted to annualized volatility magnitude via:

    sqrt(max(predicted_variance, 0) * 252)

That keeps the stored forecast on the same annualized-volatility scale as
realized_vol_* while preserving the HAR fit on variance scale.
"""
import argparse
import logging
from datetime import datetime
from typing import Dict, List, Optional, Sequence, Tuple

from ..analytics.har_rv import (
    HAR_MODEL_NAME,
    SymbolModelResult,
    run_symbol_har_evaluation,
    summarize_evaluations,
)
from ..config import PIPELINE_SYMBOLS
from ..db import get_db_manager

logger = logging.getLogger(__name__)


CREATE_EVAL_TABLE_SQL = """
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

UPSERT_EVAL_SQL = """
INSERT INTO volatility_model_evaluation (
    symbol, model_name, eval_window_start, eval_window_end,
    eval_window_days, mae, rmse, qlike, n_observations, computed_at
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON DUPLICATE KEY UPDATE
    eval_window_start = VALUES(eval_window_start),
    eval_window_days = VALUES(eval_window_days),
    mae = VALUES(mae),
    rmse = VALUES(rmse),
    qlike = VALUES(qlike),
    n_observations = VALUES(n_observations),
    computed_at = VALUES(computed_at)
"""

CLEAR_HAR_SQL = """
UPDATE daily_volatility
SET har_rv_forecast_1d = NULL,
    har_rv_model_version = NULL
WHERE symbol = %s
"""

UPDATE_HAR_SQL = """
UPDATE daily_volatility
SET har_rv_forecast_1d = %s,
    har_rv_model_version = %s
WHERE symbol = %s AND as_of_date = %s
"""


def _select_returns(db, symbol: str) -> List[Tuple]:
    rows = db.execute(
        "SELECT trade_date, log_return FROM daily_returns "
        "WHERE symbol = %s ORDER BY trade_date ASC",
        (symbol,),
    ) or []
    return [(row[0], float(row[1])) for row in rows]


def _list_all_symbols(db) -> List[str]:
    rows = db.execute(
        "SELECT DISTINCT symbol FROM daily_returns ORDER BY symbol"
    ) or []
    return [row[0] for row in rows]


def _ensure_eval_table(db) -> None:
    db.execute(CREATE_EVAL_TABLE_SQL)


def _persist_evaluations(db, symbol: str, result: SymbolModelResult) -> int:
    if not result.evaluations:
        return 0
    now = datetime.now()
    params = [
        (
            symbol,
            evaluation.model_name,
            evaluation.eval_window_start,
            evaluation.eval_window_end,
            evaluation.eval_window_days,
            evaluation.mae,
            evaluation.rmse,
            evaluation.qlike,
            evaluation.n_observations,
            now,
        )
        for evaluation in result.evaluations
    ]
    return db.executemany(UPSERT_EVAL_SQL, params)


def _persist_har_forecasts(
    db,
    symbol: str,
    result: SymbolModelResult,
    model_version: str,
) -> Dict[str, int]:
    cleared = db.execute(CLEAR_HAR_SQL, (symbol,)) or 0
    if not result.forecasts_har:
        return {"cleared": int(cleared), "written": 0}

    params = [
        (
            forecast.forecast_vol_annualized,
            model_version,
            symbol,
            forecast.as_of_date,
        )
        for forecast in result.forecasts_har
    ]
    written = db.executemany(UPDATE_HAR_SQL, params)
    return {"cleared": int(cleared), "written": written}


def run_for_symbols(
    symbols: Sequence[str],
    train_window: int = 180,
    eval_window: int = 60,
    dry_run: bool = False,
    model_version: str = HAR_MODEL_NAME,
) -> Dict[str, dict]:
    db = get_db_manager()
    _ensure_eval_table(db)

    summary: Dict[str, dict] = {}
    for symbol in symbols:
        returns_by_date = _select_returns(db, symbol)
        result = run_symbol_har_evaluation(
            symbol=symbol,
            returns_by_date=returns_by_date,
            train_window=train_window,
            eval_window=eval_window,
            model_version=model_version,
        )

        metrics = summarize_evaluations(result.evaluations)
        har_eval = metrics.get(HAR_MODEL_NAME)

        if not result.eligible:
            logger.info(
                "%s: skipped (%s)",
                symbol,
                result.reason,
            )
            if dry_run:
                write_info = {"cleared": 0, "written": 0, "eval_rows": 0}
            else:
                clear_count = int(db.execute(CLEAR_HAR_SQL, (symbol,)) or 0)
                write_info = {"cleared": clear_count, "written": 0, "eval_rows": 0}
        else:
            if dry_run:
                write_info = {
                    "cleared": 0,
                    "written": len(result.forecasts_har),
                    "eval_rows": len(result.evaluations),
                }
            else:
                har_write = _persist_har_forecasts(db, symbol, result, model_version)
                eval_written = _persist_evaluations(db, symbol, result)
                write_info = {
                    "cleared": har_write["cleared"],
                    "written": har_write["written"],
                    "eval_rows": eval_written,
                }
            if har_eval is not None:
                logger.info(
                    "%s: %d HAR obs, %d forecasts, eval MAE=%.6f RMSE=%.6f QLIKE=%.6f",
                    symbol,
                    result.observations_total,
                    len(result.forecasts_har),
                    har_eval.mae if har_eval.mae is not None else float("nan"),
                    har_eval.rmse if har_eval.rmse is not None else float("nan"),
                    har_eval.qlike if har_eval.qlike is not None else float("nan"),
                )

        summary[symbol] = {
            "eligible": result.eligible,
            "reason": result.reason,
            "returns": len(returns_by_date),
            "har_observations": result.observations_total,
            "forecasts": len(result.forecasts_har),
            "evaluation_count": len(result.evaluations),
            "writes": write_info,
            "evaluations": {
                evaluation.model_name: {
                    "mae": evaluation.mae,
                    "rmse": evaluation.rmse,
                    "qlike": evaluation.qlike,
                    "n_observations": evaluation.n_observations,
                    "eval_window_start": evaluation.eval_window_start,
                    "eval_window_end": evaluation.eval_window_end,
                }
                for evaluation in result.evaluations
            },
        }
    return summary


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Run Phase 3 HAR-RV volatility forecasting and model evaluation."
    )
    parser.add_argument(
        "--symbol",
        action="append",
        dest="symbols",
        help="Symbol to process (repeatable). Use --all-symbols for everything.",
    )
    parser.add_argument(
        "--all-symbols",
        action="store_true",
        help="Process every distinct symbol present in daily_returns.",
    )
    parser.add_argument(
        "--train-window",
        type=int,
        default=180,
        help="Rolling training-window size in HAR observations (default: 180).",
    )
    parser.add_argument(
        "--eval-window",
        type=int,
        default=60,
        help="Walk-forward evaluation-window size in HAR observations (default: 60).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute and log counts/metrics without writing.",
    )
    parser.add_argument(
        "--model-version",
        default=HAR_MODEL_NAME,
        help="Model version string written into daily_volatility.har_rv_model_version.",
    )
    args = parser.parse_args()

    if args.train_window < 30:
        parser.error("--train-window must be at least 30")
    if args.eval_window < 1:
        parser.error("--eval-window must be positive")

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
        train_window=args.train_window,
        eval_window=args.eval_window,
        dry_run=args.dry_run,
        model_version=args.model_version,
    )

    eligible = sum(1 for item in summary.values() if item["eligible"])
    skipped = len(summary) - eligible
    total_forecasts = sum(item["forecasts"] for item in summary.values())

    print(f"\n{'=' * 60}")
    print(f"volatility_evaluation {'(dry run) ' if args.dry_run else ''}complete.")
    print(f"  Symbols:           {len(summary)}")
    print(f"  Eligible:          {eligible}")
    print(f"  Skipped:           {skipped}")
    print(f"  HAR forecasts:     {total_forecasts}")
    print(f"  Train window:      {args.train_window}")
    print(f"  Eval window:       {args.eval_window}")
    print(f"  Model version:     {args.model_version}")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
