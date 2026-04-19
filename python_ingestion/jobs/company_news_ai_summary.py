"""
Symbol-aware company news AI summary job.
Generic per-symbol structure; current rollout scope is AAPL-first by default.
"""
import argparse
import json
import logging
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from ..config import load_config
from ..db import get_db_manager
from ..openai_responses_client import OpenAIResponsesClient

logger = logging.getLogger(__name__)


class CompanyNewsAISummaryCollector:
    """Collects symbol news from MySQL, summarizes with an LLM, and persists the result."""

    MIN_USABLE_NEWS_ROWS = 3
    MAX_NEWS_ROWS = 10
    ALLOWED_SENTIMENT_LABELS = {"positive", "mixed", "negative"}
    SENTIMENT_NORMALIZATION_MAP = {
        "bullish": "positive",
        "bearish": "negative",
        "constructive": "positive",
        "cautious": "mixed",
        "neutral": "mixed",
    }

    def __init__(self):
        self.config = load_config()
        self.db = get_db_manager()
        self.ai_client = OpenAIResponsesClient(self.config.ai)

    def ensure_table(self) -> bool:
        return self.db.ensure_company_news_ai_summary_table()

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        return (symbol or "").strip().upper()

    def _fetch_recent_news_rows(self, symbol: str, limit: int) -> List[Dict[str, Any]]:
        sql = """
        SELECT
            id,
            symbol,
            title,
            summary,
            url,
            source,
            published_at,
            av_overall_sentiment_score,
            av_overall_sentiment_label
        FROM company_news
        WHERE symbol = %s
        ORDER BY published_at DESC, id DESC
        LIMIT %s
        """
        rows = self.db.execute(sql, (symbol, limit)) or []
        result: List[Dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, tuple) or len(row) != 9:
                continue
            result.append(
                {
                    "id": row[0],
                    "symbol": row[1],
                    "title": row[2],
                    "summary": row[3],
                    "url": row[4],
                    "source": row[5],
                    "published_at": row[6],
                    "av_overall_sentiment_score": row[7],
                    "av_overall_sentiment_label": row[8],
                }
            )
        return result

    @staticmethod
    def _build_usable_news(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        usable: List[Dict[str, Any]] = []
        for row in rows:
            title = str(row.get("title", "")).strip()
            summary = str(row.get("summary", "")).strip()
            published_at = row.get("published_at")
            if not title or not published_at:
                continue
            usable.append(
                {
                    "title": title[:512],
                    "summary": summary[:1500] if summary else "",
                    "source": str(row.get("source", "")).strip()[:128],
                    "publishedAt": str(published_at),
                    "url": str(row.get("url", "")).strip()[:1024],
                    "avOverallSentimentScore": (
                        None if row.get("av_overall_sentiment_score") is None
                        else float(row.get("av_overall_sentiment_score"))
                    ),
                    "avOverallSentimentLabel": (
                        str(row.get("av_overall_sentiment_label", "")).strip() or None
                    ),
                }
            )
        return usable

    @staticmethod
    def _response_schema() -> Dict[str, Any]:
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "overallSentimentLabel": {
                    "type": "string",
                    "enum": ["positive", "mixed", "negative"],
                },
                "overallSentimentSummary": {"type": "string"},
                "mainThemes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 2,
                    "maxItems": 4,
                },
                "topPositiveDriver": {"type": "string"},
                "topRiskConcern": {"type": "string"},
                "confidenceNote": {"type": "string"},
            },
            "required": [
                "overallSentimentLabel",
                "overallSentimentSummary",
                "mainThemes",
                "topPositiveDriver",
                "topRiskConcern",
                "confidenceNote",
            ],
        }

    def _build_prompt(self, symbol: str, source_window_label: str, articles: List[Dict[str, Any]]) -> Tuple[str, str]:
        instructions = (
            "You are a financial news summarization assistant. "
            "Summarize recent company news for one stock symbol using the provided article batch. "
            "Use the provided Alpha Vantage overall sentiment labels and scores as baseline signals, "
            "but synthesize the final answer yourself. "
            "Be concise, grounded, and avoid speculation beyond the article evidence. "
            "Return valid JSON matching the schema exactly."
        )
        payload = {
            "symbol": symbol,
            "sourceWindowLabel": source_window_label,
            "requiredOutputFields": [
                "overallSentimentLabel",
                "overallSentimentSummary",
                "mainThemes",
                "topPositiveDriver",
                "topRiskConcern",
                "confidenceNote",
            ],
            "articles": articles,
        }
        return instructions, json.dumps(payload, ensure_ascii=True)

    def _validate_model_output(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValueError("Model output must be a JSON object")

        sentiment_label = str(payload.get("overallSentimentLabel", "")).strip().lower()
        if not sentiment_label:
            raise ValueError("Model output missing overallSentimentLabel")
        sentiment_label = self.SENTIMENT_NORMALIZATION_MAP.get(sentiment_label, sentiment_label)
        if sentiment_label not in self.ALLOWED_SENTIMENT_LABELS:
            raise ValueError(f"Unsupported sentiment label: {sentiment_label}")

        summary = str(payload.get("overallSentimentSummary", "")).strip()
        top_positive = str(payload.get("topPositiveDriver", "")).strip()
        top_risk = str(payload.get("topRiskConcern", "")).strip()
        confidence_note = str(payload.get("confidenceNote", "")).strip()
        if not summary or not top_positive or not top_risk or not confidence_note:
            raise ValueError("Model output contains empty required text fields")

        themes = payload.get("mainThemes")
        if not isinstance(themes, list):
            raise ValueError("Model output mainThemes must be an array")

        cleaned_themes: List[str] = []
        seen = set()
        for item in themes:
            text = str(item).strip()
            if not text:
                continue
            key = text.lower()
            if key in seen:
                continue
            seen.add(key)
            cleaned_themes.append(text[:160])
        if len(cleaned_themes) < 2 or len(cleaned_themes) > 4:
            raise ValueError("Model output mainThemes must contain 2 to 4 unique items")

        return {
            "overallSentimentLabel": sentiment_label,
            "overallSentimentSummary": summary[:2000],
            "mainThemes": cleaned_themes,
            "topPositiveDriver": top_positive[:2000],
            "topRiskConcern": top_risk[:2000],
            "confidenceNote": confidence_note[:2000],
        }

    def _build_insert_params(
        self,
        symbol: str,
        analysis_date: date,
        source_window_label: str,
        source_articles: List[Dict[str, Any]],
        structured_output: Dict[str, Any],
        raw_model_response: Dict[str, Any],
    ) -> Tuple:
        return (
            symbol,
            analysis_date,
            source_window_label,
            len(source_articles),
            structured_output["overallSentimentLabel"],
            structured_output["overallSentimentSummary"],
            json.dumps(structured_output["mainThemes"], ensure_ascii=True),
            structured_output["topPositiveDriver"],
            structured_output["topRiskConcern"],
            structured_output["confidenceNote"],
            self.config.ai.provider,
            self.config.ai.model,
            self.config.ai.prompt_version,
            json.dumps(source_articles, ensure_ascii=True),
            json.dumps(raw_model_response, ensure_ascii=True),
        )

    def persist_summary(self, params: Tuple) -> int:
        sql = """
        INSERT INTO company_news_ai_summary (
            symbol, analysis_date, source_window_label, source_news_count,
            overall_sentiment_label, overall_sentiment_summary, main_themes_json,
            top_positive_driver, top_risk_concern, confidence_note,
            provider, model_name, prompt_version, source_articles_json, raw_model_response_json
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON DUPLICATE KEY UPDATE
            source_window_label = VALUES(source_window_label),
            source_news_count = VALUES(source_news_count),
            overall_sentiment_label = VALUES(overall_sentiment_label),
            overall_sentiment_summary = VALUES(overall_sentiment_summary),
            main_themes_json = VALUES(main_themes_json),
            top_positive_driver = VALUES(top_positive_driver),
            top_risk_concern = VALUES(top_risk_concern),
            confidence_note = VALUES(confidence_note),
            provider = VALUES(provider),
            model_name = VALUES(model_name),
            prompt_version = VALUES(prompt_version),
            source_articles_json = VALUES(source_articles_json),
            raw_model_response_json = VALUES(raw_model_response_json),
            updated_at = CURRENT_TIMESTAMP
        """
        self.db.execute(sql, params)
        return 1

    def collect_summary(self, symbol: str = "AAPL", limit: int = MAX_NEWS_ROWS) -> int:
        normalized_symbol = self._normalize_symbol(symbol)
        if not normalized_symbol:
            logger.error("Symbol is required")
            return 0
        if limit < self.MIN_USABLE_NEWS_ROWS:
            logger.error("Limit must be at least %s", self.MIN_USABLE_NEWS_ROWS)
            return 0
        limit = min(limit, self.MAX_NEWS_ROWS)

        if not self.ensure_table():
            logger.error("Failed to ensure company_news_ai_summary table")
            return 0

        try:
            raw_news_rows = self._fetch_recent_news_rows(normalized_symbol, limit)
            usable_articles = self._build_usable_news(raw_news_rows)
            if len(usable_articles) < self.MIN_USABLE_NEWS_ROWS:
                logger.warning(
                    "Too few usable news rows for %s: found=%s minimum=%s",
                    normalized_symbol,
                    len(usable_articles),
                    self.MIN_USABLE_NEWS_ROWS,
                )
                return 0

            source_window_label = f"latest_{len(usable_articles)}_articles"
            instructions, input_text = self._build_prompt(
                normalized_symbol,
                source_window_label,
                usable_articles,
            )
            raw_model_response = self.ai_client.create_structured_response(
                instructions=instructions,
                input_text=input_text,
                schema_name="company_news_ai_summary",
                schema=self._response_schema(),
            )
            structured_output = self.ai_client.extract_json_output(raw_model_response)
            validated_output = self._validate_model_output(structured_output)

            params = self._build_insert_params(
                symbol=normalized_symbol,
                analysis_date=date.today(),
                source_window_label=source_window_label,
                source_articles=usable_articles,
                structured_output=validated_output,
                raw_model_response=raw_model_response,
            )
            self.persist_summary(params)
            logger.info(
                "Saved company news AI summary: symbol=%s window=%s articles=%s",
                normalized_symbol,
                source_window_label,
                len(usable_articles),
            )
            return 1
        except Exception as e:
            logger.error("Error collecting company news AI summary for %s: %s", normalized_symbol, e)
            return 0


def run_company_news_ai_summary_once(symbol: str = "AAPL", limit: int = 10) -> int:
    collector = CompanyNewsAISummaryCollector()
    return collector.collect_summary(symbol=symbol, limit=limit)


def main():
    parser = argparse.ArgumentParser(description="Generate and store latest company news AI summary")
    parser.add_argument("--symbol", default="AAPL", help="Stock symbol, default: AAPL")
    parser.add_argument("--limit", type=int, default=10, help="Max recent news rows to analyze, default: 10")
    args = parser.parse_args()

    rows = run_company_news_ai_summary_once(symbol=args.symbol, limit=args.limit)
    print(f"Company news AI summary complete. Affected rows: {rows}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    main()
