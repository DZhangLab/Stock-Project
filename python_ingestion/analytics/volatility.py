"""
Realized volatility analytics (Phase 2 MVP).

Pure functions; no database access, no API calls.  Used by the
daily_volatility job and reusable by future analytics.

What this module computes:
    - Rolling realized volatility over N trading days, annualized by
      sqrt(252).  Uses sample standard deviation (ddof=1) to match
      the standard finance convention; population stdev would bias
      down for small windows.
    - Volatility regime tercile label (low / medium / high) computed
      against the symbol's own historical realized_vol_21d distribution.
      Requires at least MIN_REGIME_OBSERVATIONS observations to assign
      a label; otherwise the label is None.
    - Descriptive ±1-sigma close envelope.  This is *not* a forecast
      and *not* a probabilistic confidence band; the realized vol_band_*
      values are derived from past dispersion only.  The empirical
      hit-rate field (computed elsewhere) reports how often next-day
      close fell inside the band, which is the honest validation.
    - Trailing 90-day band hit-rate, computed from prior bands and the
      next trading day's close.
"""
import math
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np


# Trading-day annualization factor.  Standard finance convention.
TRADING_DAYS_PER_YEAR = 252
SQRT_TRADING_DAYS = math.sqrt(TRADING_DAYS_PER_YEAR)

# Minimum number of historical realized_vol_21d observations required
# before a tercile regime label can be assigned for a symbol.
MIN_REGIME_OBSERVATIONS = 126

# Minimum number of (band, next-day close) pairs required before a
# trailing-90d hit-rate can be reported.  Below this, the field is
# None and the job logs the count.
MIN_HIT_RATE_OBSERVATIONS = 30

# Trailing window length for the empirical band hit-rate, in trading
# days.  Each prior day t' contributes one observation if both the band
# at t' and the close at the next trading day after t' are known.
HIT_RATE_TRAILING_DAYS = 90


@dataclass
class DailyVolatilityRow:
    """One computed volatility row, ready to be persisted."""
    symbol: str
    as_of_date: date
    realized_vol_5d: Optional[float]
    realized_vol_21d: Optional[float]
    realized_vol_63d: Optional[float]
    volatility_regime: Optional[str]
    vol_band_low: Optional[Decimal]
    vol_band_high: Optional[Decimal]
    band_hit_rate_trailing_90d: Optional[float]


def _annualized_realized_vol(window: Sequence[float]) -> Optional[float]:
    """Sample stdev * sqrt(252) for a window of log returns; None if too short."""
    if len(window) < 2:
        return None
    arr = np.asarray(window, dtype=float)
    # ddof=1 -> sample stdev.  This matches the standard PEAD/RV literature
    # and keeps the stdev unbiased for small windows.
    daily_std = float(np.std(arr, ddof=1))
    return daily_std * SQRT_TRADING_DAYS


def _tercile_regime(current: Optional[float],
                    history: Sequence[float]) -> Optional[str]:
    """
    Return 'low' / 'medium' / 'high' based on tercile cutoffs of `history`.

    Args:
        current: The current realized_vol_21d value.  If None the regime
            is None.
        history: All non-None realized_vol_21d observations up to and
            including the current one (chronological order does not
            matter for tercile computation).

    Returns:
        The regime label, or None if there is no `current` value or
        fewer than MIN_REGIME_OBSERVATIONS in history.
    """
    if current is None:
        return None
    valid = [v for v in history if v is not None]
    if len(valid) < MIN_REGIME_OBSERVATIONS:
        return None
    arr = np.asarray(valid, dtype=float)
    low_cut, high_cut = np.quantile(arr, [1.0 / 3.0, 2.0 / 3.0])
    if current <= low_cut:
        return "low"
    if current >= high_cut:
        return "high"
    return "medium"


def _band(close: Optional[Decimal],
          realized_vol_21d_annualized: Optional[float]
          ) -> Tuple[Optional[Decimal], Optional[Decimal]]:
    """
    Compute the descriptive ±1-sigma daily band around close.

    daily_vol = realized_vol_21d / sqrt(252)
    low  = close * (1 - daily_vol)
    high = close * (1 + daily_vol)

    Returns (None, None) if either input is missing.  The band is a
    descriptive volatility envelope, not a forecast; users of the
    band must rely on the empirical hit-rate field for validation.
    """
    if close is None or realized_vol_21d_annualized is None:
        return None, None
    daily_vol = Decimal(str(realized_vol_21d_annualized)) / Decimal(str(SQRT_TRADING_DAYS))
    low = close * (Decimal("1") - daily_vol)
    high = close * (Decimal("1") + daily_vol)
    return low, high


def compute_for_symbol(
    symbol: str,
    returns_by_date: Sequence[Tuple[date, float]],
    closes_by_date: Dict[date, Decimal],
) -> List[DailyVolatilityRow]:
    """
    Compute the full per-day volatility output for one symbol.

    Args:
        symbol: Ticker.
        returns_by_date: (trade_date, log_return) pairs sorted ascending
            by trade_date.  Must come from the daily_returns table.
        closes_by_date: dict mapping trade_date -> close (Decimal) from
            everydayAfterClose.  Used for the volatility band only.

    Returns:
        A DailyVolatilityRow for every trade_date where at least one
        non-NULL output field can be produced.  Symbols with too few
        returns to compute realized_vol_5d return an empty list.
    """
    n = len(returns_by_date)
    if n < 5:
        # Cannot compute even RV5; emit no rows so we never write fake
        # NULL-only entries for short-history symbols (CDAY, IPG, CMA, K).
        return []

    log_returns = [r for _, r in returns_by_date]
    dates = [d for d, _ in returns_by_date]

    # First pass: compute RVs, regime input, and band per day.
    rv5: List[Optional[float]] = [None] * n
    rv21: List[Optional[float]] = [None] * n
    rv63: List[Optional[float]] = [None] * n
    band_low: List[Optional[Decimal]] = [None] * n
    band_high: List[Optional[Decimal]] = [None] * n
    regime: List[Optional[str]] = [None] * n

    for i in range(n):
        if i + 1 >= 5:
            rv5[i] = _annualized_realized_vol(log_returns[i + 1 - 5: i + 1])
        if i + 1 >= 21:
            rv21[i] = _annualized_realized_vol(log_returns[i + 1 - 21: i + 1])
        if i + 1 >= 63:
            rv63[i] = _annualized_realized_vol(log_returns[i + 1 - 63: i + 1])

        close_i = closes_by_date.get(dates[i])
        band_low[i], band_high[i] = _band(close_i, rv21[i])

        # Regime: history is all non-None rv21 values seen up to and
        # including position i.
        history = [v for v in rv21[: i + 1] if v is not None]
        regime[i] = _tercile_regime(rv21[i], history)

    # Second pass: trailing-90d hit-rate.  At date i, examine prior days
    # j in [i-90, i-1] (clamped at 0) and check whether the close on
    # day j+1 falls inside the band on day j.  A pair (j, j+1) only
    # counts if band[j] exists AND closes_by_date[dates[j+1]] exists.
    hit_rate: List[Optional[float]] = [None] * n
    for i in range(n):
        start = max(0, i - HIT_RATE_TRAILING_DAYS)
        # j ranges over previous days; we need j+1 <= i so j <= i-1.
        hits = 0
        observations = 0
        for j in range(start, i):
            if band_low[j] is None or band_high[j] is None:
                continue
            next_close = closes_by_date.get(dates[j + 1])
            if next_close is None:
                continue
            observations += 1
            if band_low[j] <= next_close <= band_high[j]:
                hits += 1
        if observations >= MIN_HIT_RATE_OBSERVATIONS:
            hit_rate[i] = hits / observations

    # Emit rows only where at least one field is populated.  Since we
    # already returned early for n < 5, every row from i=4 onward has
    # at least rv5[i] populated.  Earlier rows (i < 4) are NULL-only
    # and would just be wasted rows; skip them.
    out: List[DailyVolatilityRow] = []
    for i in range(n):
        if (rv5[i] is None and rv21[i] is None and rv63[i] is None
                and band_low[i] is None and band_high[i] is None
                and regime[i] is None and hit_rate[i] is None):
            continue
        out.append(DailyVolatilityRow(
            symbol=symbol,
            as_of_date=dates[i],
            realized_vol_5d=rv5[i],
            realized_vol_21d=rv21[i],
            realized_vol_63d=rv63[i],
            volatility_regime=regime[i],
            vol_band_low=band_low[i],
            vol_band_high=band_high[i],
            band_hit_rate_trailing_90d=hit_rate[i],
        ))
    return out
