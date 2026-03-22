"""
Apple (AAPL) latest earnings call management commentary summarization job.
MVP scope: latest call only, single symbol only.
"""
import argparse
import json
import logging
import re
import time
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from ..alpha_vantage import AlphaVantageClient
from ..db import get_db_manager

logger = logging.getLogger(__name__)


class AppleEarningsCommentaryCollector:
    SYMBOL = "AAPL"
    SOURCE = "ALPHA_VANTAGE"
    REQUEST_DELAY_SECONDS = 1.3

    MANAGEMENT_KEYWORDS = [
        "ceo",
        "cfo",
        "tim cook",
        "luca maestri",
        "guidance",
        "outlook",
        "demand",
        "growth",
        "revenue",
        "margin",
        "services",
        "iphone",
        "mac",
        "ipad",
        "wearables",
        "china",
        "supply chain",
        "capital return",
    ]

    EXCLUDE_HINTS = [
        "operator:",
        "question-and-answer",
        "question and answer",
        "q&a",
    ]

    BOILERPLATE_PATTERNS = [
        "welcome to",
        "my name is",
        "director of investor relations",
        "today's call is being recorded",
        "forward-looking statements",
        "without limitation",
        "actual results could differ",
        "actual results or trends to differ materially",
        "risks and uncertainties that may cause actual results",
        "please refer to",
        "prepared remarks",
        "we'll open the call to questions",
    ]

    HIGHLIGHT_KEYWORDS = [
        "revenue", "eps", "margin", "demand", "growth", "record",
        "services", "iphone", "mac", "ipad", "wearables", "cash flow",
    ]
    RISK_KEYWORDS = [
        "risk", "weakness", "constraint", "constraints", "softness",
        "headwind", "pressure", "decline", "down", "tempered", "challenging",
    ]
    OUTLOOK_KEYWORDS = [
        "outlook", "guidance", "expect", "expected", "forecast", "next quarter",
        "future", "will continue", "we believe", "we anticipate",
    ]
    BUSINESS_CONTEXT_KEYWORDS = [
        "revenue", "eps", "margin", "demand", "growth", "sales", "tariff",
        "supply", "cost", "pricing", "china", "services", "iphone", "mac", "ipad",
        "wearables", "quarter", "fiscal", "gross margin",
    ]

    def __init__(self):
        self.db = get_db_manager()
        self.api_client = AlphaVantageClient()

    def ensure_table(self) -> bool:
        return self.db.ensure_earnings_call_summary_table()

    @staticmethod
    def _parse_date(value: Any) -> Optional[date]:
        if value is None:
            return None
        raw = str(value).strip()
        if not raw:
            return None
        for pattern in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
            try:
                return datetime.strptime(raw, pattern).date()
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
        except ValueError:
            return None

    @staticmethod
    def _derive_period_label(fiscal_date: date) -> str:
        quarter = ((fiscal_date.month - 1) // 3) + 1
        return f"{fiscal_date.year}Q{quarter}"

    @staticmethod
    def _latest_earnings_row(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        rows = payload.get("quarterlyEarnings", [])
        if not isinstance(rows, list):
            return None
        valid_rows = [row for row in rows if isinstance(row, dict)]
        valid_rows.sort(key=lambda row: str(row.get("fiscalDateEnding", "")), reverse=True)
        return valid_rows[0] if valid_rows else None

    @staticmethod
    def _extract_transcript_text(payload: Dict[str, Any]) -> str:
        def _collect_chunks(rows: List[Any]) -> List[str]:
            chunks: List[str] = []
            for row in rows:
                if isinstance(row, dict):
                    for key in ("transcript", "content", "text", "body"):
                        value = row.get(key)
                        if isinstance(value, str) and value.strip():
                            chunks.append(value.strip())
                            break
                elif isinstance(row, str) and row.strip():
                    chunks.append(row.strip())
            return chunks

        # Alpha Vantage payload shape may vary over time.
        candidates = [
            payload.get("transcript"),
            payload.get("content"),
            payload.get("text"),
            payload.get("fullTranscript"),
            payload.get("body"),
        ]

        for item in candidates:
            if isinstance(item, str) and item.strip():
                return item.strip()
            if isinstance(item, list):
                chunks = _collect_chunks(item)
                if chunks:
                    return "\n".join(chunks)

        if isinstance(payload.get("data"), dict):
            data = payload.get("data")
            for key in ("transcript", "content", "text", "fullTranscript", "body"):
                value = data.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()

        if isinstance(payload.get("data"), list):
            chunks = _collect_chunks(payload.get("data"))
            if chunks:
                return "\n".join(chunks)

        return ""

    def _generate_summary(self, transcript_text: str) -> Tuple[str, List[str]]:
        def normalize_sentence(line: str) -> str:
            return re.sub(r"\s+", " ", line).strip()

        def trim_for_bullet(line: str, limit: int = 260) -> str:
            normalized = normalize_sentence(line)
            if len(normalized) <= limit:
                return normalized
            return normalized[:limit].rstrip() + "..."

        def is_boilerplate(line: str) -> bool:
            lower = line.lower()
            if any(hint in lower for hint in self.EXCLUDE_HINTS):
                return True
            if "?" in line:
                return True
            if lower.startswith("can you ") or lower.startswith("could you ") or lower.startswith("what about "):
                return True
            return any(pattern in lower for pattern in self.BOILERPLATE_PATTERNS)

        def contains_any(line: str, keywords: List[str]) -> bool:
            lower = line.lower()
            return any(keyword in lower for keyword in keywords)

        def classify(line: str) -> str:
            lower = line.lower()
            has_risk = any(keyword in lower for keyword in self.RISK_KEYWORDS)
            has_business_context = any(keyword in lower for keyword in self.BUSINESS_CONTEXT_KEYWORDS)
            if has_risk and has_business_context:
                return "risk"
            if any(keyword in lower for keyword in self.OUTLOOK_KEYWORDS):
                return "outlook"
            return "highlight"

        def score_sentence(line: str) -> int:
            lower = line.lower()
            score = 0
            score += sum(3 for keyword in self.HIGHLIGHT_KEYWORDS if keyword in lower)
            has_business_context = any(keyword in lower for keyword in self.BUSINESS_CONTEXT_KEYWORDS)
            if has_business_context:
                score += sum(3 for keyword in self.RISK_KEYWORDS if keyword in lower)
            score += sum(3 for keyword in self.OUTLOOK_KEYWORDS if keyword in lower)
            score += sum(1 for keyword in self.MANAGEMENT_KEYWORDS if keyword in lower)
            if "$" in line:
                score += 2
            if "%" in line:
                score += 2
            return score

        cleaned = re.sub(r"\s+", " ", transcript_text).strip()
        if not cleaned:
            return "No transcript text is available for this earnings call yet.", []

        sentences = re.split(r"(?<=[.!?])\s+", cleaned)
        scored: List[Tuple[int, int, str, str]] = []

        for idx, sentence in enumerate(sentences):
            line = normalize_sentence(sentence)
            if len(line) < 60 or len(line) > 520:
                continue
            if is_boilerplate(line):
                continue
            if not (
                contains_any(line, self.HIGHLIGHT_KEYWORDS)
                or (contains_any(line, self.RISK_KEYWORDS) and contains_any(line, self.BUSINESS_CONTEXT_KEYWORDS))
                or contains_any(line, self.OUTLOOK_KEYWORDS)
            ):
                continue
            score = score_sentence(line)
            if score <= 0:
                continue
            scored.append((score, idx, line, classify(line)))

        if not scored:
            fallback = sentences[:3]
            fallback_text = " ".join([s.strip() for s in fallback if s.strip()])
            if not fallback_text:
                fallback_text = cleaned[:1200]
            return fallback_text, []

        # Main summary: keep strongest 3 lines and preserve transcript order.
        summary_pick = sorted(scored, key=lambda row: (-row[0], row[1]))[:3]
        summary_pick = sorted(summary_pick, key=lambda row: row[1])
        summary_sentences = [row[2] for row in summary_pick]
        summary_text = " ".join(summary_sentences)
        if len(summary_text) > 3000:
            summary_text = summary_text[:3000].rstrip() + "..."

        # Build 3-5 concise takeaways, dedup against summary sentences.
        summary_set = {normalize_sentence(line).lower() for line in summary_sentences}
        remaining = [row for row in scored if normalize_sentence(row[2]).lower() not in summary_set]
        by_priority = sorted(remaining, key=lambda row: (-row[0], row[1]))

        highlight_pool = [row for row in by_priority if row[3] == "highlight"]
        risk_pool = [row for row in by_priority if row[3] == "risk"]
        outlook_pool = [row for row in by_priority if row[3] == "outlook"]

        takeaways: List[str] = []

        def append_labeled(pool: List[Tuple[int, int, str, str]], label: str, max_items: int = 1):
            count = 0
            for row in pool:
                if count >= max_items:
                    break
                bullet = f"{label}: {trim_for_bullet(row[2])}"
                if bullet not in takeaways:
                    takeaways.append(bullet)
                    count += 1

        append_labeled(highlight_pool, "Key Highlights", max_items=2)
        append_labeled(risk_pool, "Main Risks / Concerns", max_items=2)
        append_labeled(outlook_pool, "Outlook / Guidance", max_items=2)

        # Fill remaining slots to reach at least 3 bullets.
        if len(takeaways) < 3:
            for row in by_priority:
                label = (
                    "Main Risks / Concerns"
                    if row[3] == "risk"
                    else "Outlook / Guidance"
                    if row[3] == "outlook"
                    else "Key Highlights"
                )
                bullet = f"{label}: {trim_for_bullet(row[2])}"
                if bullet in takeaways:
                    continue
                takeaways.append(bullet)
                if len(takeaways) >= 5:
                    break

        takeaways = takeaways[:5]
        return summary_text, takeaways

    def _build_params(
        self,
        fiscal_period_label: str,
        call_date: Optional[date],
        summary_text: str,
        key_takeaways: List[str],
        transcript_url: Optional[str],
        raw_payload: Dict[str, Any],
    ) -> Tuple:
        return (
            self.SYMBOL,
            fiscal_period_label,
            call_date,
            self.SOURCE,
            summary_text,
            json.dumps(key_takeaways, ensure_ascii=True),
            transcript_url,
            json.dumps(raw_payload, ensure_ascii=True),
        )

    def persist_summary(self, params: Tuple) -> int:
        sql = """
        INSERT INTO earnings_call_summary (
            symbol, fiscal_period_label, call_date, source, summary_text,
            key_takeaways_json, transcript_url, raw_payload_json
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON DUPLICATE KEY UPDATE
            call_date = VALUES(call_date),
            source = VALUES(source),
            summary_text = VALUES(summary_text),
            key_takeaways_json = VALUES(key_takeaways_json),
            transcript_url = VALUES(transcript_url),
            raw_payload_json = VALUES(raw_payload_json),
            updated_at = CURRENT_TIMESTAMP
        """
        self.db.execute(sql, params)
        return 1

    def collect_latest_commentary(self) -> int:
        if not self.ensure_table():
            logger.error("Failed to ensure earnings_call_summary table")
            return 0

        try:
            earnings_payload = self.api_client.get_earnings(self.SYMBOL)
            latest = self._latest_earnings_row(earnings_payload)
            if latest is None:
                logger.warning("No quarterly earnings row found for AAPL")
                return 0

            fiscal_date = self._parse_date(latest.get("fiscalDateEnding"))
            if fiscal_date is None:
                logger.warning("Invalid fiscalDateEnding in latest earnings row")
                return 0

            fiscal_period_label = self._derive_period_label(fiscal_date)
            call_date = self._parse_date(latest.get("reportedDate"))

            # Free-tier safety: spread Alpha Vantage requests to avoid 1 req/s limit.
            time.sleep(self.REQUEST_DELAY_SECONDS)
            transcript_payload = self.api_client.get_earnings_call_transcript(
                self.SYMBOL,
                fiscal_period_label
            )
            if not isinstance(transcript_payload, dict):
                logger.warning("Transcript payload is not a dict for %s %s", self.SYMBOL, fiscal_period_label)
                transcript_payload = {}

            transcript_text = self._extract_transcript_text(transcript_payload)
            summary_text, takeaways = self._generate_summary(transcript_text)
            transcript_url = transcript_payload.get("url")
            if transcript_url is not None:
                transcript_url = str(transcript_url).strip()[:1024] or None

            params = self._build_params(
                fiscal_period_label=fiscal_period_label,
                call_date=call_date,
                summary_text=summary_text,
                key_takeaways=takeaways,
                transcript_url=transcript_url,
                raw_payload=transcript_payload,
            )
            self.persist_summary(params)
            logger.info(
                "Saved latest AAPL earnings commentary summary: period=%s call_date=%s",
                fiscal_period_label,
                call_date,
            )
            return 1
        except ValueError as e:
            logger.error("%s", e)
            return 0
        except Exception as e:
            logger.error("Error collecting earnings commentary summary: %s", e)
            return 0


def run_aapl_earnings_commentary_once() -> int:
    collector = AppleEarningsCommentaryCollector()
    return collector.collect_latest_commentary()


def main():
    parser = argparse.ArgumentParser(
        description="Collect latest AAPL earnings call transcript and store management summary"
    )
    parser.parse_args()
    rows = run_aapl_earnings_commentary_once()
    print(f"AAPL earnings commentary ingestion complete. Affected rows: {rows}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    main()
