"""
Alpha Vantage API client for news and financial data ingestion.
"""
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import requests

from .config import AlphaVantageConfig, load_config

logger = logging.getLogger(__name__)


@dataclass
class AlphaVantageNewsItem:
    """Data model for a single Alpha Vantage news item."""
    symbol: str
    title: str
    summary: str
    url: str
    source: str
    published_at: str
    relevance_score: Optional[float] = None
    raw_ticker_match: bool = False
    overall_sentiment_score: Optional[float] = None
    overall_sentiment_label: Optional[str] = None


class AlphaVantageClient:
    """Client for interacting with Alpha Vantage endpoints."""

    def __init__(self, config: Optional[AlphaVantageConfig] = None):
        if config is None:
            config = load_config().alpha_vantage
        self.config = config

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        try:
            if value is None or value == "":
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    # Minimum Alpha Vantage relevance_score to keep an article.
    # AV scores range 0.0–1.0; articles where the target ticker is only
    # tangentially mentioned typically score below 0.15.
    MIN_RELEVANCE_SCORE = 0.15

    @staticmethod
    def _contains_etf_style_title_text(title: str) -> bool:
        text = title.lower()
        etf_style_keywords = [
            "etf",
            "fund",
            "watchlist",
            "portfolio",
            "holdings",
            "yield",
            "dividend",
            "buy sell or hold",
        ]
        return any(keyword in text for keyword in etf_style_keywords)

    @staticmethod
    def _contains_generic_roundup_title(title: str) -> bool:
        """Detect generic market-roundup / multi-stock titles."""
        text = title.lower()
        roundup_phrases = [
            "what you need to know",
            "what investors need to know",
            "stocks surged",
            "stocks plunged",
            "stocks skyrocket",
            "market movers",
            "morning commentary",
            "price target roundup",
            "price today,",
            "shares skyrocket",
        ]
        return any(phrase in text for phrase in roundup_phrases)

    # Known share-class aliases (map variant → canonical).
    # Both directions are checked so GOOGL target accepts $GOOG and vice versa.
    _SHARE_CLASS_ALIASES: Dict[str, str] = {
        "GOOG": "GOOGL",
        "GOOGL": "GOOG",
        "BRK.A": "BRK.B",
        "BRK.B": "BRK.A",
    }

    @classmethod
    def _ticker_matches_target(cls, tick: str, target: str) -> bool:
        """Return True if *tick* is the same company as *target* (including share-class aliases)."""
        t = tick.upper()
        if t == target:
            return True
        return cls._SHARE_CLASS_ALIASES.get(target, "") == t

    @classmethod
    def _title_features_different_ticker(cls, title: str, target_ticker: str) -> bool:
        """Return True when the title prominently names a *different* stock ticker.

        Pattern: "CompanyName Stock (OTHER)" or "$OTHER" in the title where
        OTHER != target_ticker.  This catches articles like
        "HCA Healthcare Inc Stock (HCA) Closed Up" that AV tags with AAPL
        only because Apple is mentioned in the body or ticker_sentiment list.
        """
        target = target_ticker.upper()

        # Match "Stock (TICK)" or "Shares (TICK)" pattern
        stock_paren = re.findall(r'(?:stock|shares)\s*\(([A-Z]{1,5})\)', title, re.IGNORECASE)
        for tick in stock_paren:
            if not cls._ticker_matches_target(tick, target):
                return True

        # Match "$TICK" cashtag pattern — only flag if target cashtag is absent
        cashtags = re.findall(r'\$([A-Z]{1,5})\b', title)
        if cashtags:
            has_target = any(cls._ticker_matches_target(t, target) for t in cashtags)
            has_other = any(not cls._ticker_matches_target(t, target) for t in cashtags)
            if has_other and not has_target:
                return True

        return False

    def _extract_ticker_relevance(self, raw: Dict[str, Any], ticker: str) -> Tuple[bool, Optional[float]]:
        ticker_sentiment = raw.get("ticker_sentiment", [])
        if not isinstance(ticker_sentiment, list):
            return False, None

        target = ticker.upper()
        best_score: Optional[float] = None
        matched = False

        for row in ticker_sentiment:
            if not isinstance(row, Dict):
                continue
            symbol = str(row.get("ticker", "")).upper().strip()
            if symbol != target:
                continue
            matched = True
            score = self._safe_float(row.get("relevance_score"))
            if score is None:
                continue
            if best_score is None or score > best_score:
                best_score = score

        return matched, best_score

    def _request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self.config.api_key:
            raise ValueError(
                "Missing ALPHA_VANTAGE_API_KEY. Set it in python_ingestion/.env before running ingestion."
            )

        request_params = dict(params)
        request_params["apikey"] = self.config.api_key

        try:
            response = requests.get(self.config.base_url, params=request_params, timeout=self.config.timeout)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            logger.error("Alpha Vantage request failed: %s", e)
            raise
        except ValueError as e:
            logger.error("Alpha Vantage response is not valid JSON: %s", e)
            raise

        if not isinstance(data, dict):
            raise ValueError("Alpha Vantage response has invalid format")

        if "Error Message" in data:
            raise ValueError(f"Alpha Vantage error: {data['Error Message']}")
        if "Note" in data:
            raise ValueError(f"Alpha Vantage note: {data['Note']}")
        if "Information" in data:
            raise ValueError(f"Alpha Vantage information: {data['Information']}")

        return data

    def get_income_statement(self, symbol: str) -> Dict[str, Any]:
        """Fetch INCOME_STATEMENT for a symbol."""
        return self._request(
            {
                "function": "INCOME_STATEMENT",
                "symbol": symbol,
            }
        )

    def get_earnings(self, symbol: str) -> Dict[str, Any]:
        """Fetch EARNINGS for a symbol."""
        return self._request(
            {
                "function": "EARNINGS",
                "symbol": symbol,
            }
        )

    def get_earnings_call_transcript(self, symbol: str, quarter: str) -> Dict[str, Any]:
        """Fetch EARNINGS_CALL_TRANSCRIPT for a symbol and quarter (e.g. 2025Q1)."""
        return self._request(
            {
                "function": "EARNINGS_CALL_TRANSCRIPT",
                "symbol": symbol,
                "quarter": quarter,
            }
        )

    def get_news_sentiment(self, ticker: str, limit: int = 20) -> List[AlphaVantageNewsItem]:
        """
        Fetch NEWS_SENTIMENT for a single ticker.
        """
        params = {
            "function": "NEWS_SENTIMENT",
            "tickers": ticker,
            "sort": "LATEST",
            "limit": max(1, min(limit, 1000)),
        }
        data = self._request(params)

        feed = data.get("feed", [])
        result: List[AlphaVantageNewsItem] = []

        dropped_no_ticker_match = 0
        dropped_low_relevance = 0
        dropped_etf_style = 0
        dropped_roundup = 0
        dropped_other_ticker = 0

        for raw in feed:
            if not isinstance(raw, Dict):
                continue

            title = str(raw.get("title", "")).strip()
            url = str(raw.get("url", "")).strip()
            published_at = str(raw.get("time_published", "")).strip()
            if not title or not url or not published_at:
                continue

            summary = str(raw.get("summary", "")).strip()
            source = str(raw.get("source", "")).strip()
            raw_ticker_match, relevance_score = self._extract_ticker_relevance(raw, ticker)

            # 1. Require structured ticker relevance from Alpha Vantage
            if not raw_ticker_match:
                dropped_no_ticker_match += 1
                continue

            # 2. Require minimum relevance score
            if relevance_score is not None and relevance_score < self.MIN_RELEVANCE_SCORE:
                dropped_low_relevance += 1
                continue

            # 3. Drop generic ETF/watchlist/portfolio articles
            if self._contains_etf_style_title_text(title):
                dropped_etf_style += 1
                continue

            # 4. Drop generic roundup / multi-stock articles
            if self._contains_generic_roundup_title(title):
                dropped_roundup += 1
                continue

            # 5. Drop articles whose title prominently features a different ticker
            if self._title_features_different_ticker(title, ticker):
                dropped_other_ticker += 1
                continue

            result.append(
                AlphaVantageNewsItem(
                    symbol=ticker,
                    title=title,
                    summary=summary,
                    url=url,
                    source=source,
                    published_at=published_at,
                    relevance_score=relevance_score,
                    raw_ticker_match=raw_ticker_match,
                    overall_sentiment_score=self._safe_float(raw.get("overall_sentiment_score")),
                    overall_sentiment_label=str(raw.get("overall_sentiment_label", "")).strip() or None,
                )
            )

            if len(result) >= limit:
                break

        logger.info(
            "%s news filtering: kept=%d, dropped_no_ticker=%d, dropped_low_relevance=%d, "
            "dropped_etf=%d, dropped_roundup=%d, dropped_other_ticker=%d, raw_feed=%d",
            ticker,
            len(result),
            dropped_no_ticker_match,
            dropped_low_relevance,
            dropped_etf_style,
            dropped_roundup,
            dropped_other_ticker,
            len(feed),
        )
        return result
