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

    # Company name aliases used to detect primary-subject presence in titles.
    # Keys are uppercase tickers; values are lowercase names to match.
    _COMPANY_NAME_ALIASES: Dict[str, List[str]] = {
        "AAPL": ["apple"],
        "GOOGL": ["google", "alphabet"],
        "GOOG": ["google", "alphabet"],
        "MSFT": ["microsoft"],
        "AMZN": ["amazon"],
        "META": ["meta platforms", "facebook"],
        "TSLA": ["tesla"],
        "NVDA": ["nvidia"],
        "NFLX": ["netflix"],
        "BRK.A": ["berkshire"],
        "BRK.B": ["berkshire"],
    }

    # Patterns in titles that indicate the target company is a secondary party,
    # not the primary subject.  The placeholder {} is replaced with the company
    # name/ticker at match time.
    _SECONDARY_MENTION_PATTERNS: List[str] = [
        r"\bwith\s+{}",
        r"\bbacked\s+by\s+{}",
        r"\bpowered\s+by\s+{}",
        r"\bdeal\s+with\s+{}",
        r"\bpartnership\s+with\s+{}",
        r"\bpartner(?:s|ing)?\s+with\s+{}",
        r"\bcontract\s+with\s+{}",
        r"\blease[sd]?\s+(?:from|to|with)\s+{}",
        r"\busing\s+{}",
    ]

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

        # Match "(TICK)" pattern — a parenthesized all-caps ticker in the title
        # typically identifies the article's primary subject.  Only flag when
        # the ticker belongs to a *different* company.
        paren_tickers = re.findall(r'\(([A-Z]{1,5})\)', title)
        for tick in paren_tickers:
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

    @classmethod
    def _get_company_names(cls, ticker: str) -> List[str]:
        """Return lowercase company names/aliases for a ticker, plus the ticker itself."""
        target = ticker.upper()
        names = list(cls._COMPANY_NAME_ALIASES.get(target, []))
        # Always include the ticker itself (lowercase for matching)
        names.append(target.lower())
        # Include share-class alias ticker if present
        alias_tick = cls._SHARE_CLASS_ALIASES.get(target)
        if alias_tick:
            names.append(alias_tick.lower())
        return names

    @classmethod
    def _title_mentions_company(cls, title: str, ticker: str) -> bool:
        """Return True if the title explicitly contains the target company name or ticker."""
        text = title.lower()
        for name in cls._get_company_names(ticker):
            if name in text:
                return True
        return False

    @classmethod
    def _is_secondary_mention(cls, title: str, ticker: str) -> bool:
        """Return True when the target company appears only as a secondary party in the title.

        Checks whether the company name appears exclusively inside a
        "with X" / "backed by X" / "deal with X" style phrase, suggesting
        the article is about *another* entity's relationship with the target.
        """
        text = title.lower()
        names = cls._get_company_names(ticker)

        for name in names:
            for pat_template in cls._SECONDARY_MENTION_PATTERNS:
                pattern = pat_template.format(re.escape(name))
                if re.search(pattern, text, re.IGNORECASE):
                    return True
        return False

    def _target_has_highest_relevance(self, raw: Dict[str, Any], ticker: str) -> bool:
        """Return True if the target ticker has the highest relevance_score among all tickers."""
        ticker_sentiment = raw.get("ticker_sentiment", [])
        if not isinstance(ticker_sentiment, list):
            return False

        target = ticker.upper()
        target_score: Optional[float] = None
        max_other_score: Optional[float] = None

        for row in ticker_sentiment:
            if not isinstance(row, Dict):
                continue
            symbol = str(row.get("ticker", "")).upper().strip()
            score = self._safe_float(row.get("relevance_score"))
            if score is None:
                continue

            if self._ticker_matches_target(symbol, target):
                if target_score is None or score > target_score:
                    target_score = score
            else:
                if max_other_score is None or score > max_other_score:
                    max_other_score = score

        if target_score is None:
            return False
        if max_other_score is None:
            return True
        return target_score >= max_other_score

    def _is_primary_subject(self, raw: Dict[str, Any], title: str, ticker: str) -> bool:
        """Determine if the target company is the primary subject of the article.

        The target must have the highest (or tied-for-highest) relevance_score
        among all tickers in the article.  Title mention alone is not sufficient
        because the company name can appear as context for another company's story
        (e.g. "Hut 8 surges on Google data-center lease").
        """
        highest_relevance = self._target_has_highest_relevance(raw, ticker)

        # Secondary-mention pattern ("with X", "backed by X") and not highest → drop
        if self._is_secondary_mention(title, ticker) and not highest_relevance:
            return False

        # The core gate: the target ticker must have the highest relevance score
        return highest_relevance

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
        dropped_secondary_mention = 0
        kept_primary_subject = 0

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

            # 6. Primary-subject filter: keep only when the target company
            #    is the main subject, not merely a secondary participant.
            if not self._is_primary_subject(raw, title, ticker):
                dropped_secondary_mention += 1
                continue
            kept_primary_subject += 1

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
            "dropped_etf=%d, dropped_roundup=%d, dropped_other_ticker=%d, "
            "dropped_secondary_mention=%d, kept_primary_subject=%d, raw_feed=%d",
            ticker,
            len(result),
            dropped_no_ticker_match,
            dropped_low_relevance,
            dropped_etf_style,
            dropped_roundup,
            dropped_other_ticker,
            dropped_secondary_mention,
            kept_primary_subject,
            len(feed),
        )
        return result
