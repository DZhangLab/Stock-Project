"""
TwelveData API client module for fetching stock quotes and time series data.
"""
import logging
import time
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import APIConfig, load_config

logger = logging.getLogger(__name__)


@dataclass
class QuoteModel:
    """Data model for stock quote information."""
    symbol: str
    name: str
    exchange: str
    currency: str
    datetime: str
    timestamp: int
    open: Optional[float]
    high: Optional[float]
    low: Optional[float]
    close: Optional[float]
    volume: Optional[int]
    previous_close: Optional[float]
    change: Optional[float]
    percent_change: Optional[float]
    average_volume: Optional[int]
    rolling_1d_change: Optional[float]
    rolling_7d_change: Optional[float]
    rolling_period_change: Optional[float]
    is_market_open: bool
    fifty_two_week_low: Optional[float]
    fifty_two_week_high: Optional[float]
    fifty_two_week_low_change: Optional[float]
    fifty_two_week_high_change: Optional[float]
    fifty_two_week_low_change_percent: Optional[float]
    fifty_two_week_high_change_percent: Optional[float]
    fifty_two_week_range: Optional[str]


@dataclass
class TimeSeriesPoint:
    """Data model for a single time series data point."""
    datetime: str
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class NewsItem:
    """Data model for a single company news item."""
    symbol: str
    title: str
    summary: str
    url: str
    source: str
    published_at: str


class TwelveDataClient:
    """Client for interacting with TwelveData API."""
    
    def __init__(self, config: Optional[APIConfig] = None):
        """
        Initialize TwelveData API client.
        
        Args:
            config: API configuration. If None, loads from environment.
        """
        if config is None:
            config = load_config().api
        
        self.config = config
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """
        Create requests session with retry strategy.
        
        Returns:
            requests.Session: Configured session
        """
        session = requests.Session()
        
        retry_strategy = Retry(
            total=self.config.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        
        return session
    
    def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make HTTP request to API with error handling.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            Dict: JSON response data
            
        Raises:
            requests.RequestException: If request fails
            ValueError: If response is not valid JSON or contains errors
        """
        url = f"{self.config.base_url}/{endpoint}"
        params["apikey"] = self.config.api_key
        
        try:
            response = self.session.get(
                url,
                params=params,
                timeout=self.config.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Check for API errors
            if "code" in data and data.get("code") != 200:
                error_msg = data.get("message", "Unknown API error")
                logger.error(f"API error: {error_msg}")
                raise ValueError(f"API error: {error_msg}")
            
            return data
            
        except requests.exceptions.Timeout:
            logger.error(f"Request timeout for {url}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            raise
        except ValueError as e:
            logger.error(f"JSON decode error: {e}")
            raise
    
    def get_quote(self, symbol: str) -> QuoteModel:
        """
        Get current quote for a stock symbol.
        
        Args:
            symbol: Stock symbol (e.g., "AAPL")
            
        Returns:
            QuoteModel: Quote data model
            
        Raises:
            ValueError: If API returns error or missing required fields
        """
        params = {"symbol": symbol}
        data = self._make_request("quote", params)
        
        # Handle nested fifty_two_week field safely
        fifty_two_week = data.get("fifty_two_week", {})
        
        quote = QuoteModel(
            symbol=data.get("symbol", ""),
            name=data.get("name", ""),
            exchange=data.get("exchange", ""),
            currency=data.get("currency", ""),
            datetime=data.get("datetime", ""),
            timestamp=int(data.get("timestamp", 0)),
            open=self._safe_float(data.get("open")),
            high=self._safe_float(data.get("high")),
            low=self._safe_float(data.get("low")),
            close=self._safe_float(data.get("close")),
            volume=self._safe_int(data.get("volume")),
            previous_close=self._safe_float(data.get("previous_close")),
            change=self._safe_float(data.get("change")),
            percent_change=self._safe_float(data.get("percent_change")),
            average_volume=self._safe_int(data.get("average_volume")),
            rolling_1d_change=self._safe_float(data.get("rolling_1d_change")),
            rolling_7d_change=self._safe_float(data.get("rolling_7d_change")),
            rolling_period_change=self._safe_float(data.get("rolling_period_change")),
            is_market_open=bool(data.get("is_market_open", False)),
            fifty_two_week_low=self._safe_float(fifty_two_week.get("low")),
            fifty_two_week_high=self._safe_float(fifty_two_week.get("high")),
            fifty_two_week_low_change=self._safe_float(fifty_two_week.get("low_change")),
            fifty_two_week_high_change=self._safe_float(fifty_two_week.get("high_change")),
            fifty_two_week_low_change_percent=self._safe_float(fifty_two_week.get("low_change_percent")),
            fifty_two_week_high_change_percent=self._safe_float(fifty_two_week.get("high_change_percent")),
            fifty_two_week_range=fifty_two_week.get("range")
        )
        
        return quote
    
    def get_intraday(
        self,
        symbol: str,
        interval: str = "1min",
        outputsize: int = 390
    ) -> List[TimeSeriesPoint]:
        """
        Get intraday time series data for a stock symbol.
        
        Args:
            symbol: Stock symbol (e.g., "AAPL")
            interval: Time interval (default: "1min")
            outputsize: Number of data points to return (default: 390)
            
        Returns:
            List[TimeSeriesPoint]: List of time series data points
        """
        params = {
            "symbol": symbol,
            "interval": interval,
            "outputsize": outputsize
        }
        
        data = self._make_request("time_series", params)
        
        values = data.get("values", [])
        time_series = []
        
        for value in values:
            point = TimeSeriesPoint(
                datetime=value.get("datetime", ""),
                open=float(value.get("open", 0)),
                high=float(value.get("high", 0)),
                low=float(value.get("low", 0)),
                close=float(value.get("close", 0)),
                volume=float(value.get("volume", 0))
            )
            time_series.append(point)
        
        return time_series
    
    def get_time_series_range(
        self,
        symbol: str,
        interval: str = "1min",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[TimeSeriesPoint]:
        """
        Get time series data for a specific date range.
        
        Args:
            symbol: Stock symbol (e.g., "AAPL")
            interval: Time interval (default: "1min")
            start_date: Start date in format "YYYY-MM-DD HH:MM:SS"
            end_date: End date in format "YYYY-MM-DD HH:MM:SS"
            
        Returns:
            List[TimeSeriesPoint]: List of time series data points
        """
        params = {
            "symbol": symbol,
            "interval": interval
        }
        
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        
        data = self._make_request("time_series", params)
        
        values = data.get("values", [])
        time_series = []
        
        for value in values:
            point = TimeSeriesPoint(
                datetime=value.get("datetime", ""),
                open=float(value.get("open", 0)),
                high=float(value.get("high", 0)),
                low=float(value.get("low", 0)),
                close=float(value.get("close", 0)),
                volume=float(value.get("volume", 0))
            )
            time_series.append(point)
        
        return time_series

    def get_news(self, symbol: str, limit: int = 20) -> List[NewsItem]:
        """
        Get company news for a stock symbol.

        Args:
            symbol: Stock symbol (e.g., "AAPL")
            limit: Maximum number of news items to fetch

        Returns:
            List[NewsItem]: List of company news items
        """
        params = {
            "symbol": symbol,
            "outputsize": limit
        }

        data = self._make_request("news", params)

        if isinstance(data, list):
            raw_items = data
        else:
            raw_items = data.get("data") or data.get("news") or []

        news_items: List[NewsItem] = []
        for item in raw_items:
            if not isinstance(item, dict):
                continue

            title = str(item.get("title", "")).strip()
            url = str(item.get("url", "")).strip()

            if not title or not url:
                continue

            summary = str(item.get("description") or item.get("summary") or "").strip()
            source = str(item.get("source") or item.get("site") or "").strip()
            published_at = str(
                item.get("datetime")
                or item.get("published_at")
                or item.get("published")
                or ""
            ).strip()

            if not published_at:
                continue

            news_items.append(
                NewsItem(
                    symbol=symbol,
                    title=title,
                    summary=summary,
                    url=url,
                    source=source,
                    published_at=published_at
                )
            )

            if len(news_items) >= limit:
                break

        return news_items
    
    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        """Safely convert value to float."""
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def _safe_int(value: Any) -> Optional[int]:
        """Safely convert value to int."""
        if value is None or value == "":
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None


