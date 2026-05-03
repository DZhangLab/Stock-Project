"""
HAR-RV analytics helpers for Phase 3.

Target definition
-----------------
This module does NOT use next-day realized_vol_5d as the supervised
target. That field is a smoothed backward-looking statistic and would
blur the one-day-ahead forecasting task.

Instead we define a one-day realized-variance proxy directly from
`daily_returns`:

    rv1_t = (log_return_t)^2

This is the standard daily realized-variance proxy when only one
close-to-close return is available per day. The HAR model is fit on
variance scale:

    E[rv1_{t+1}] = beta0 + beta_d * RV_d_t + beta_w * RV_w_t + beta_m * RV_m_t

where:
    RV_d_t = rv1_t
    RV_w_t = mean(rv1_t, ..., rv1_{t-4})
    RV_m_t = mean(rv1_t, ..., rv1_{t-21})

For storage in daily_volatility.har_rv_forecast_1d we convert the
predicted next-day variance proxy into an annualized volatility
magnitude:

    forecast_vol_annualized = sqrt(max(predicted_variance, 0) * 252)

This keeps the stored forecast on the same annualized-volatility scale
as the existing realized_vol_* fields, while preserving the model fit on
variance scale where HAR-style aggregation is most natural.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np


TRADING_DAYS_PER_YEAR = 252.0
EPSILON = 1e-12
WEEKLY_WINDOW = 5
MONTHLY_WINDOW = 22
ROLLING21_WINDOW = 21

HAR_MODEL_NAME = "har_rv_v1"
BASELINE_YESTERDAY_NAME = "baseline_yesterday_rv"
BASELINE_ROLLING21_NAME = "baseline_rolling21"


@dataclass(frozen=True)
class HarObservation:
    """Feature row keyed by date t with target on t+1."""

    as_of_date: date
    target_date: date
    rv_d: float
    rv_w: float
    rv_m: float
    baseline_rolling21: float
    target_variance: float
    target_vol_annualized: float


@dataclass(frozen=True)
class ModelForecast:
    """One out-of-sample one-day-ahead forecast."""

    model_name: str
    as_of_date: date
    target_date: date
    forecast_variance: float
    forecast_vol_annualized: float
    actual_variance: float
    actual_vol_annualized: float


@dataclass(frozen=True)
class ModelEvaluation:
    """Summary metrics over a walk-forward evaluation window."""

    model_name: str
    eval_window_start: date
    eval_window_end: date
    eval_window_days: int
    mae: Optional[float]
    rmse: Optional[float]
    qlike: Optional[float]
    n_observations: int


@dataclass(frozen=True)
class HarModelFit:
    """OLS parameters for the HAR model on variance scale."""

    intercept: float
    beta_d: float
    beta_w: float
    beta_m: float


@dataclass(frozen=True)
class SymbolModelResult:
    """Complete Phase 3 output for one symbol."""

    symbol: str
    model_version: str
    eligible: bool
    reason: Optional[str]
    observations_total: int
    forecasts_har: List[ModelForecast]
    evaluations: List[ModelEvaluation]
    latest_fit: Optional[HarModelFit]


def variance_proxy_from_log_return(log_return: float) -> float:
    """Return the daily realized-variance proxy from one log return."""
    x = float(log_return)
    return x * x


def annualized_vol_from_variance_proxy(variance_proxy: float) -> float:
    """Convert a daily variance proxy into annualized volatility magnitude."""
    return math.sqrt(max(float(variance_proxy), 0.0) * TRADING_DAYS_PER_YEAR)


def build_har_observations(
    returns_by_date: Sequence[Tuple[date, float]],
) -> List[HarObservation]:
    """
    Build HAR observations from daily log returns.

    Each observation is keyed by date t and forecasts the next trading
    day's realized-variance proxy rv1_{t+1}. Features only use returns
    available through date t.
    """
    if len(returns_by_date) < MONTHLY_WINDOW + 1:
        return []

    dates = [d for d, _ in returns_by_date]
    rv1 = [variance_proxy_from_log_return(r) for _, r in returns_by_date]

    observations: List[HarObservation] = []
    for i in range(MONTHLY_WINDOW - 1, len(rv1) - 1):
        rv_d = rv1[i]
        rv_w = float(np.mean(rv1[i + 1 - WEEKLY_WINDOW: i + 1]))
        rv_m = float(np.mean(rv1[i + 1 - MONTHLY_WINDOW: i + 1]))
        rv_21 = float(np.mean(rv1[i + 1 - ROLLING21_WINDOW: i + 1]))
        target_variance = rv1[i + 1]
        observations.append(HarObservation(
            as_of_date=dates[i],
            target_date=dates[i + 1],
            rv_d=rv_d,
            rv_w=rv_w,
            rv_m=rv_m,
            baseline_rolling21=rv_21,
            target_variance=target_variance,
            target_vol_annualized=annualized_vol_from_variance_proxy(
                target_variance
            ),
        ))
    return observations


def _fit_har_model(train_obs: Sequence[HarObservation]) -> HarModelFit:
    """Fit OLS on variance scale using only past observations."""
    x = np.asarray([
        [1.0, obs.rv_d, obs.rv_w, obs.rv_m]
        for obs in train_obs
    ], dtype=float)
    y = np.asarray([obs.target_variance for obs in train_obs], dtype=float)
    beta, *_ = np.linalg.lstsq(x, y, rcond=None)
    return HarModelFit(
        intercept=float(beta[0]),
        beta_d=float(beta[1]),
        beta_w=float(beta[2]),
        beta_m=float(beta[3]),
    )


def _predict_har_variance(model: HarModelFit, obs: HarObservation) -> float:
    """Predict next-day variance proxy from a fitted HAR model."""
    return (
        model.intercept
        + model.beta_d * obs.rv_d
        + model.beta_w * obs.rv_w
        + model.beta_m * obs.rv_m
    )


def _make_forecast(
    model_name: str,
    obs: HarObservation,
    forecast_variance: float,
) -> ModelForecast:
    safe_variance = max(float(forecast_variance), 0.0)
    return ModelForecast(
        model_name=model_name,
        as_of_date=obs.as_of_date,
        target_date=obs.target_date,
        forecast_variance=safe_variance,
        forecast_vol_annualized=annualized_vol_from_variance_proxy(
            safe_variance
        ),
        actual_variance=obs.target_variance,
        actual_vol_annualized=obs.target_vol_annualized,
    )


def _evaluate_forecasts(
    model_name: str,
    forecasts: Sequence[ModelForecast],
) -> Optional[ModelEvaluation]:
    """Compute MAE, RMSE, and QLIKE over the provided forecasts."""
    if not forecasts:
        return None

    abs_errors = [
        abs(f.forecast_vol_annualized - f.actual_vol_annualized)
        for f in forecasts
    ]
    sq_errors = [
        (f.forecast_vol_annualized - f.actual_vol_annualized) ** 2
        for f in forecasts
    ]
    qlikes = [
        math.log(max(f.forecast_variance, EPSILON))
        + (f.actual_variance / max(f.forecast_variance, EPSILON))
        for f in forecasts
    ]
    return ModelEvaluation(
        model_name=model_name,
        eval_window_start=forecasts[0].target_date,
        eval_window_end=forecasts[-1].target_date,
        eval_window_days=len(forecasts),
        mae=float(np.mean(abs_errors)),
        rmse=float(math.sqrt(float(np.mean(sq_errors)))),
        qlike=float(np.mean(qlikes)),
        n_observations=len(forecasts),
    )


def run_symbol_har_evaluation(
    symbol: str,
    returns_by_date: Sequence[Tuple[date, float]],
    train_window: int,
    eval_window: int,
    model_version: str = HAR_MODEL_NAME,
) -> SymbolModelResult:
    """
    Run HAR-RV walk-forward forecasting and evaluation for one symbol.

    Eligibility requires at least `train_window + eval_window`
    observation rows after feature construction, where each observation
    predicts one next-day realized-variance proxy.
    """
    observations = build_har_observations(returns_by_date)
    min_obs = train_window + eval_window
    if len(observations) < min_obs:
        return SymbolModelResult(
            symbol=symbol,
            model_version=model_version,
            eligible=False,
            reason=(
                f"insufficient_history: need at least {min_obs} HAR observations, "
                f"found {len(observations)}"
            ),
            observations_total=len(observations),
            forecasts_har=[],
            evaluations=[],
            latest_fit=None,
        )

    har_forecasts: List[ModelForecast] = []
    baseline_yday: List[ModelForecast] = []
    baseline_roll21: List[ModelForecast] = []
    latest_fit: Optional[HarModelFit] = None

    for i in range(train_window, len(observations)):
        train_obs = observations[i - train_window: i]
        current = observations[i]

        latest_fit = _fit_har_model(train_obs)
        har_forecasts.append(_make_forecast(
            HAR_MODEL_NAME,
            current,
            _predict_har_variance(latest_fit, current),
        ))
        baseline_yday.append(_make_forecast(
            BASELINE_YESTERDAY_NAME,
            current,
            current.rv_d,
        ))
        baseline_roll21.append(_make_forecast(
            BASELINE_ROLLING21_NAME,
            current,
            current.baseline_rolling21,
        ))

    eval_har = har_forecasts[-eval_window:]
    eval_yday = baseline_yday[-eval_window:]
    eval_roll21 = baseline_roll21[-eval_window:]

    evaluations = [
        _evaluate_forecasts(HAR_MODEL_NAME, eval_har),
        _evaluate_forecasts(BASELINE_YESTERDAY_NAME, eval_yday),
        _evaluate_forecasts(BASELINE_ROLLING21_NAME, eval_roll21),
    ]

    return SymbolModelResult(
        symbol=symbol,
        model_version=model_version,
        eligible=True,
        reason=None,
        observations_total=len(observations),
        forecasts_har=har_forecasts,
        evaluations=[e for e in evaluations if e is not None],
        latest_fit=latest_fit,
    )


def summarize_evaluations(
    evaluations: Iterable[ModelEvaluation],
) -> Dict[str, ModelEvaluation]:
    """Convenience lookup keyed by model_name."""
    return {evaluation.model_name: evaluation for evaluation in evaluations}
