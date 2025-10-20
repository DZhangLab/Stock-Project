"""HTTP client wrappers for the Twelve Data API."""
from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, Optional

import requests

from .config import Settings, get_settings


LOGGER = logging.getLogger(__name__)


class TwelveDataClient:
    """Thin wrapper around Twelve Data's REST API."""

    BASE_URL = "https://api.twelvedata.com"

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self.session = requests.Session()
        self.session.params = {"apikey": self.settings.twelve_api_key}
        self.timeout = self.settings.request_timeout

    def fetch_intraday(self, symbol: str, interval: str = "1min", outputsize: int = 390) -> Dict[str, Any]:
        """Return the JSON payload for an intraday time series."""

        params = {"symbol": symbol, "interval": interval, "outputsize": outputsize}
        return self._request("/time_series", params=params)

    def fetch_intraday_range(
        self, symbol: str, start_date: str, end_date: str, interval: str = "1min"
    ) -> Dict[str, Any]:
        params = {
            "symbol": symbol,
            "interval": interval,
            "start_date": start_date,
            "end_date": end_date,
        }
        return self._request("/time_series", params=params)

    def fetch_quote(self, symbol: str) -> Dict[str, Any]:
        """Return quote metadata for *symbol*."""

        return self._request("/quote", params={"symbol": symbol})

    def _request(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.BASE_URL}{path}"
        LOGGER.debug("Requesting %s params=%s", url, params)
        response = self.session.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        if "status" in data and data.get("status") == "error":
            message = data.get("message", "Unknown error")
            raise RuntimeError(f"Twelve Data error: {message}")
        return data


def extract_time_series(payload: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    """Normalise the ``values`` list from the Twelve Data response."""

    values = payload.get("values") or []
    for entry in values:
        yield {
            "datetime": entry["datetime"],
            "open": entry.get("open"),
            "high": entry.get("high"),
            "low": entry.get("low"),
            "close": entry.get("close"),
            "volume": entry.get("volume"),
        }


def extract_quote(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Normalise quote payload to a flat dictionary."""

    return {
        "symbol": payload.get("symbol"),
        "name": _safe_str(payload.get("name")),
        "exchange": payload.get("exchange"),
        "currency": payload.get("currency"),
        "datetime": payload.get("datetime"),
        "open": payload.get("open"),
        "high": payload.get("high"),
        "low": payload.get("low"),
        "close": payload.get("close"),
        "previous_close": payload.get("previous_close"),
        "change": payload.get("change"),
        "percent_change": payload.get("percent_change"),
        "fifty_two_week_high": payload.get("fifty_two_week_high"),
        "fifty_two_week_low": payload.get("fifty_two_week_low"),
    }


def _safe_str(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    return value.replace("'", "’’")

