"""
Daily return calculation helpers.

Pure functions; no database access, no API calls.  Used by Phase 1's
daily_returns job and reused later by Phase 2 volatility analytics.

Definitions:
    simple_return = close / prev_close - 1
    log_return    = ln(close / prev_close)

Both use close-to-close daily prices on consecutive observed trading
days (from the input order), not calendar days.  A bar is considered
invalid if its close is NULL, non-numeric, or non-positive; an invalid
bar breaks the chain so the next valid bar's return is also skipped.
"""
import math
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Iterable, List, Optional, Tuple


@dataclass
class DailyReturnRow:
    """One computed return row, ready to be persisted."""
    symbol: str
    trade_date: date
    prev_close: Decimal
    close: Decimal
    log_return: float
    simple_return: float


def _to_positive_decimal(value) -> Optional[Decimal]:
    """Return Decimal(value) if it is a positive finite number, else None."""
    if value is None:
        return None
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    if not d.is_finite() or d <= 0:
        return None
    return d


def compute_returns_for_symbol(
    symbol: str,
    bars: Iterable[Tuple[date, object]],
) -> List[DailyReturnRow]:
    """
    Compute close-to-close returns for one symbol.

    Args:
        symbol: Stock ticker.
        bars: Iterable of (trade_date, close) pairs sorted ascending by
            trade_date.  trade_date must be a datetime.date; close may
            be Decimal, float, int, str, or None.

    Returns:
        List of DailyReturnRow.  The first observed bar per symbol is
        skipped because it has no previous close.  Bars with a missing
        or non-positive close are also skipped, and they break the
        chain — the bar immediately after an invalid bar is skipped
        too, because its prev_close would be invalid.
    """
    out: List[DailyReturnRow] = []
    prev_close: Optional[Decimal] = None

    for trade_date, raw_close in bars:
        close_dec = _to_positive_decimal(raw_close)

        if close_dec is None:
            # Invalid bar: drop it and break the chain.
            prev_close = None
            continue

        if prev_close is not None:
            simple = float(close_dec / prev_close - Decimal("1"))
            log_ret = math.log(float(close_dec) / float(prev_close))
            out.append(DailyReturnRow(
                symbol=symbol,
                trade_date=trade_date,
                prev_close=prev_close,
                close=close_dec,
                log_return=log_ret,
                simple_return=simple,
            ))

        prev_close = close_dec

    return out


def count_invalid_bars(bars: Iterable[Tuple[date, object]]) -> int:
    """Return the number of bars with a missing or non-positive close."""
    return sum(1 for _, c in bars if _to_positive_decimal(c) is None)
