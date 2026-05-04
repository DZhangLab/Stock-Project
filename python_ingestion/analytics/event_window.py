"""
Event-window return helpers for descriptive earnings reactions.

Pure functions; no database access and no API calls.  Trading days are
defined by the input price rows, which should come from the local
daily_returns/everydayAfterClose-derived data.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Dict, Iterable, List, Optional, Tuple


RETURN_WINDOWS = (1, 3, 5, 20)


@dataclass
class EventWindowResult:
    """Computed event-window returns for one earnings event."""

    first_reaction_date: Optional[date]
    pre_event_close: Optional[Decimal]
    returns: Dict[int, Optional[Decimal]]
    missing_windows: List[int]
    exclusion_reason: Optional[str]

    @property
    def has_full_return_window(self) -> bool:
        return not self.missing_windows and self.exclusion_reason is None


def normalize_fiscal_period_label(value: Optional[str]) -> Optional[str]:
    """Normalize labels such as FY2025Q1 and 2025Q1 to the same key."""
    if value is None:
        return None
    label = str(value).strip().upper()
    if not label:
        return None
    if label.startswith("FY"):
        label = label[2:]
    return label or None


def _to_positive_decimal(value) -> Optional[Decimal]:
    if value is None:
        return None
    try:
        dec = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    if not dec.is_finite() or dec <= 0:
        return None
    return dec


def _event_return(close: Decimal, pre_event_close: Decimal) -> Decimal:
    return close / pre_event_close - Decimal("1")


def compute_event_window_returns(
    event_date: Optional[date],
    bars: Iterable[Tuple[date, object]],
) -> EventWindowResult:
    """
    Compute PEAD-style descriptive post-event returns.

    Phase 4A uses a conservative unknown-release-time rule:
    first_reaction_date is the next observed trading day after event_date.

    Return window convention:
    ret_1d uses the close on first_reaction_date.  ret_3d, ret_5d, and
    ret_20d use the close on the 3rd, 5th, and 20th observed trading day
    starting at first_reaction_date, divided by pre_event_close minus 1.
    """
    empty_returns = {window: None for window in RETURN_WINDOWS}
    if event_date is None:
        return EventWindowResult(
            first_reaction_date=None,
            pre_event_close=None,
            returns=empty_returns,
            missing_windows=list(RETURN_WINDOWS),
            exclusion_reason="missing_event_date",
        )

    clean_bars = [
        (trade_date, close)
        for trade_date, raw_close in bars
        if (close := _to_positive_decimal(raw_close)) is not None
    ]
    clean_bars.sort(key=lambda item: item[0])

    if len(clean_bars) < 2:
        return EventWindowResult(
            first_reaction_date=None,
            pre_event_close=None,
            returns=empty_returns,
            missing_windows=list(RETURN_WINDOWS),
            exclusion_reason="insufficient_price_history",
        )

    reaction_index = None
    for idx, (trade_date, _close) in enumerate(clean_bars):
        if trade_date > event_date:
            reaction_index = idx
            break

    if reaction_index is None:
        return EventWindowResult(
            first_reaction_date=None,
            pre_event_close=None,
            returns=empty_returns,
            missing_windows=list(RETURN_WINDOWS),
            exclusion_reason="missing_post_event_price_window",
        )
    if reaction_index == 0:
        return EventWindowResult(
            first_reaction_date=clean_bars[reaction_index][0],
            pre_event_close=None,
            returns=empty_returns,
            missing_windows=list(RETURN_WINDOWS),
            exclusion_reason="missing_pre_event_close",
        )

    pre_event_close = clean_bars[reaction_index - 1][1]
    returns: Dict[int, Optional[Decimal]] = {}
    missing_windows: List[int] = []
    for window in RETURN_WINDOWS:
        target_index = reaction_index + window - 1
        if target_index >= len(clean_bars):
            returns[window] = None
            missing_windows.append(window)
            continue
        returns[window] = _event_return(clean_bars[target_index][1], pre_event_close)

    reason = "missing_post_event_price_window" if missing_windows else None
    return EventWindowResult(
        first_reaction_date=clean_bars[reaction_index][0],
        pre_event_close=pre_event_close,
        returns=returns,
        missing_windows=missing_windows,
        exclusion_reason=reason,
    )
