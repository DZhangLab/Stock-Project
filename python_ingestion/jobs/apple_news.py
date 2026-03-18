"""
Apple (AAPL) company news ingestion job.
Phase 1 MVP scope: database + Python ingestion only.
"""
import argparse
import hashlib
import logging
from datetime import datetime
from typing import List, Optional, Tuple

from ..alpha_vantage import AlphaVantageClient, AlphaVantageNewsItem
from ..db import get_db_manager

logger = logging.getLogger(__name__)


class AppleNewsCollector:
    """Collects and persists AAPL company news."""

    SYMBOL = "AAPL"

    def __init__(self):
        self.db = get_db_manager()
        self.api_client = AlphaVantageClient()

    def ensure_table(self) -> bool:
        """Ensure company_news table exists."""
        return self.db.ensure_company_news_table()

    def _parse_published_at(self, value: str) -> Optional[datetime]:
        """Parse API published time into a datetime acceptable by MySQL."""
        if not value:
            return None

        raw = value.strip()
        patterns = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y%m%dT%H%M%S",
        ]

        for pattern in patterns:
            try:
                dt = datetime.strptime(raw, pattern)
                if dt.tzinfo is not None:
                    return dt.replace(tzinfo=None)
                return dt
            except ValueError:
                continue

        try:
            iso_value = raw.replace("Z", "+00:00")
            dt = datetime.fromisoformat(iso_value)
            if dt.tzinfo is not None:
                return dt.replace(tzinfo=None)
            return dt
        except ValueError:
            return None

    def _build_insert_params(self, items: List[AlphaVantageNewsItem]) -> List[Tuple]:
        """Build insert parameters, skipping invalid rows."""
        params_list: List[Tuple] = []

        for item in items:
            published_at = self._parse_published_at(item.published_at)
            if published_at is None:
                logger.warning("Skipping news item with invalid published_at: %s", item.published_at)
                continue

            normalized_url = item.url.strip()
            if len(normalized_url) > 1024:
                logger.warning("Skipping news item with url length > 1024")
                continue
            url_hash = hashlib.sha256(normalized_url.encode("utf-8")).hexdigest()

            params_list.append(
                (
                    self.SYMBOL,
                    item.title[:512],
                    item.summary or None,
                    normalized_url,
                    url_hash,
                    (item.source[:128] if item.source else None),
                    published_at,
                )
            )

        return params_list

    def persist_news(self, items: List[AlphaVantageNewsItem]) -> int:
        """Persist news items into company_news with dedup by (symbol, url_hash)."""
        if not items:
            return 0

        params_list = self._build_insert_params(items)
        if not params_list:
            return 0

        insert_sql = """
        INSERT INTO company_news (symbol, title, summary, url, url_hash, source, published_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            title = VALUES(title),
            summary = VALUES(summary),
            url = VALUES(url),
            source = VALUES(source),
            published_at = VALUES(published_at),
            ingestion_time = CURRENT_TIMESTAMP
        """

        try:
            affected_rows = self.db.executemany(insert_sql, params_list)
            logger.info(
                "Apple news persisted: %s rows attempted, %s rows affected",
                len(params_list),
                affected_rows
            )
            return affected_rows
        except Exception as e:
            logger.error("Error persisting Apple news: %s", e)
            return 0

    def collect_news(self, limit: int = 20) -> int:
        """Collect and persist Apple news."""
        if not self.ensure_table():
            logger.error("Failed to ensure company_news table")
            return 0

        try:
            items = self.api_client.get_news_sentiment(self.SYMBOL, limit=limit)
            if not items:
                logger.warning("No Apple news returned from API")
                return 0

            return self.persist_news(items)
        except ValueError as e:
            logger.error("%s", e)
            return 0
        except Exception as e:
            logger.error("Error collecting Apple news: %s", e)
            return 0


def run_apple_news_once(limit: int = 20) -> int:
    """Manual entry function for one-time Apple news ingestion."""
    collector = AppleNewsCollector()
    return collector.collect_news(limit=limit)


def main():
    """CLI entry point for manual Apple news ingestion."""
    parser = argparse.ArgumentParser(description="Collect and store AAPL company news")
    parser.add_argument("--limit", type=int, default=20, help="Maximum number of news items to fetch")
    args = parser.parse_args()

    rows = run_apple_news_once(limit=args.limit)
    print(f"Apple news ingestion complete. Affected rows: {rows}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    main()
