"""
AAPL-only earnings call AI analysis job.
Phase 2 MVP: transcript segmentation + tone signals + LLM structured summary.
"""
import argparse
import json
import logging
import time
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from ..config import load_config
from ..db import get_db_manager
from ..earnings_tone import build_earnings_tone_analyzer, EarningsToneAnalysisError
from ..openai_responses_client import OpenAIResponsesClient
from .aapl_earnings_commentary import AppleEarningsCommentaryCollector

logger = logging.getLogger(__name__)


class AppleEarningsAIAnalysisCollector:
    SYMBOL = "AAPL"
    SOURCE = "ALPHA_VANTAGE"
    PROMPT_VERSION = "earnings_ai_analysis_v3"
    REQUEST_DELAY_SECONDS = 1.3
    MIN_TRANSCRIPT_CHAR_COUNT = 600
    MIN_SEGMENT_COUNT = 3
    MAX_SEGMENT_CHARS = 1200
    MAX_PROMPT_SEGMENTS = 8
    ALLOWED_TONES = {"positive", "mixed", "negative"}

    def __init__(self):
        self.config = load_config()
        self.db = get_db_manager()
        self.ai_client = OpenAIResponsesClient(self.config.ai)
        self.transcript_collector = AppleEarningsCommentaryCollector()
        self.tone_analyzer = build_earnings_tone_analyzer()

    def ensure_table(self) -> bool:
        return self.db.ensure_earnings_ai_analysis_table()

    def _load_transcript_context_for_quarter(
        self,
        fiscal_period_label: str,
        call_date: Optional[date],
    ) -> Optional[Dict[str, Any]]:
        """Fetch transcript for a specific quarter and return context dict."""
        time.sleep(self.REQUEST_DELAY_SECONDS)
        transcript_payload = self.transcript_collector.api_client.get_earnings_call_transcript(
            self.SYMBOL,
            fiscal_period_label,
        )
        if not isinstance(transcript_payload, dict):
            logger.warning("Transcript payload is not a dict for %s %s", self.SYMBOL, fiscal_period_label)
            return None

        transcript_text = AppleEarningsCommentaryCollector._extract_transcript_text(transcript_payload)
        if not transcript_text.strip():
            logger.warning("Empty transcript for %s %s", self.SYMBOL, fiscal_period_label)
            return None

        transcript_url = transcript_payload.get("url")
        if transcript_url is not None:
            transcript_url = str(transcript_url).strip()[:1024] or None

        return {
            "fiscalPeriodLabel": fiscal_period_label,
            "callDate": call_date,
            "transcriptPayload": transcript_payload,
            "transcriptText": transcript_text,
            "transcriptUrl": transcript_url,
        }

    def _load_latest_transcript_context(self) -> Optional[Dict[str, Any]]:
        earnings_payload = self.transcript_collector.api_client.get_earnings(self.SYMBOL)
        latest = AppleEarningsCommentaryCollector._latest_earnings_row(earnings_payload)
        if latest is None:
            logger.warning("No quarterly earnings row found for %s", self.SYMBOL)
            return None

        fiscal_date = AppleEarningsCommentaryCollector._parse_date(latest.get("fiscalDateEnding"))
        if fiscal_date is None:
            logger.warning("Invalid fiscalDateEnding in latest earnings row for %s", self.SYMBOL)
            return None

        fiscal_period_label = AppleEarningsCommentaryCollector._derive_period_label(fiscal_date)
        call_date = AppleEarningsCommentaryCollector._parse_date(latest.get("reportedDate"))
        return self._load_transcript_context_for_quarter(fiscal_period_label, call_date)

    @staticmethod
    def _response_schema() -> Dict[str, Any]:
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "overallTone": {
                    "type": "string",
                    "enum": ["positive", "mixed", "negative"],
                },
                "keyHighlights": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 2,
                    "maxItems": 4,
                },
                "mainRisksConcerns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                    "maxItems": 4,
                },
                "outlookGuidance": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                    "maxItems": 4,
                },
            },
            "required": [
                "overallTone",
                "keyHighlights",
                "mainRisksConcerns",
                "outlookGuidance",
            ],
        }

    @staticmethod
    def _signal_prompt_view(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        for item in items[:3]:
            if not isinstance(item, dict):
                continue
            result.append(
                {
                    "excerpt": item.get("excerpt"),
                    "toneLabel": item.get("toneLabel"),
                    "confidence": item.get("confidence"),
                    "businessPriorityScore": item.get("businessPriorityScore"),
                    "riskSignalScore": item.get("riskSignalScore"),
                    "guidanceSignalScore": item.get("guidanceSignalScore"),
                    "themes": item.get("themes", []),
                }
            )
        return result

    def _build_prompt(
        self,
        fiscal_period_label: str,
        call_date: Optional[date],
        transcript_segments: List[str],
        tone_summary: Dict[str, Any],
    ) -> Tuple[str, str]:
        instructions = (
            "You are a financial earnings-call summary assistant. "
            "Use the transcript evidence and FinBERT signal ranking to produce a clean, factual summary of the latest AAPL earnings call. "
            "Keep the answer grounded in the supplied evidence only and return valid JSON matching the schema exactly. "
            "Use concise, readable bullets with complete thoughts. "
            "Prefer factual summary over interpretation, and avoid analyst-style phrasing. "
            "For highlights, focus on the most important business drivers. "
            "For risks, include real concerns or watchpoints, not simply slower-growing businesses. "
            "For outlook, focus on management's forward message and guidance. "
            "Only include numbers when they help make the point more clear."
        )

        prioritized_signals = (
            tone_summary.get("topPositiveSignals", [])
            + tone_summary.get("topNegativeSignals", [])
            + tone_summary.get("topGuidanceSignals", [])
            + tone_summary.get("topCautiousGuidanceSignals", [])
        )
        selected_indexes = sorted(
            {item.get("index") for item in prioritized_signals[: self.MAX_PROMPT_SEGMENTS // 2] if isinstance(item.get("index"), int)}
            | set(range(min(len(transcript_segments), self.MAX_PROMPT_SEGMENTS // 2)))
        )
        selected_segments = []
        for index in selected_indexes:
            if isinstance(index, int) and 0 <= index < len(transcript_segments):
                selected_segments.append(
                    {
                        "segmentIndex": index,
                        "text": transcript_segments[index],
                    }
                )

        payload = {
            "symbol": self.SYMBOL,
            "fiscalPeriodLabel": fiscal_period_label,
            "callDate": None if call_date is None else call_date.isoformat(),
            "requiredOutputFields": [
                "overallTone",
                "keyHighlights",
                "mainRisksConcerns",
                "outlookGuidance",
            ],
            "summaryStyle": {
                "keyHighlights": "Use short factual bullets about the main business positives or important developments.",
                "mainRisksConcerns": "Use short factual bullets about genuine concerns, pressures, or watchpoints.",
                "outlookGuidance": "Use short factual bullets about management's forward-looking message or guidance.",
            },
            "toneSummary": {
                "analyzer": tone_summary.get("analyzer"),
                "modelName": tone_summary.get("modelName"),
                "overallTone": tone_summary.get("overallTone"),
                "aggregateScore": tone_summary.get("aggregateScore"),
                "segmentCount": tone_summary.get("segmentCount"),
                "positiveSegmentCount": tone_summary.get("positiveSegmentCount"),
                "mixedSegmentCount": tone_summary.get("mixedSegmentCount"),
                "negativeSegmentCount": tone_summary.get("negativeSegmentCount"),
                "topPositiveSignals": self._signal_prompt_view(tone_summary.get("topPositiveSignals", [])),
                "topNegativeSignals": self._signal_prompt_view(tone_summary.get("topNegativeSignals", [])),
                "topGuidanceSignals": self._signal_prompt_view(tone_summary.get("topGuidanceSignals", [])),
                "topCautiousGuidanceSignals": self._signal_prompt_view(tone_summary.get("topCautiousGuidanceSignals", [])),
            },
            "transcriptSegments": selected_segments,
        }
        return instructions, json.dumps(payload, ensure_ascii=True)

    def _validate_model_output(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValueError("Model output must be a JSON object")

        overall_tone = str(payload.get("overallTone", "")).strip().lower()
        if overall_tone not in self.ALLOWED_TONES:
            raise ValueError("Model output overallTone is invalid")

        def shorten_complete_text(text: str, limit: int) -> str:
            if len(text) <= limit:
                return text
            sentence_matches = self.tone_analyzer.normalize_whitespace(text[:limit]).split(". ")
            if len(sentence_matches) > 1:
                candidate = ". ".join(sentence_matches[:-1]).strip()
                if candidate and len(candidate) >= max(60, limit // 2):
                    if not candidate.endswith("."):
                        candidate += "."
                    return candidate
            trimmed = text[:limit].rstrip(" ,;:")
            return trimmed + "..."

        def clean_array(value: Any, field_name: str, minimum: int, maximum: int) -> List[str]:
            if not isinstance(value, list):
                raise ValueError("Model output %s must be an array" % field_name)
            cleaned: List[str] = []
            seen = set()
            max_len = 170 if field_name == "keyHighlights" else 155
            for item in value:
                text = self.tone_analyzer.normalize_whitespace(str(item))
                if not text:
                    continue
                key = text.lower()
                if key in seen:
                    continue
                seen.add(key)
                cleaned.append(shorten_complete_text(text, max_len))
            if len(cleaned) < minimum or len(cleaned) > maximum:
                raise ValueError("Model output %s size is invalid" % field_name)
            return cleaned

        return {
            "overallTone": overall_tone,
            "keyHighlights": clean_array(payload.get("keyHighlights"), "keyHighlights", 2, 4),
            "mainRisksConcerns": clean_array(payload.get("mainRisksConcerns"), "mainRisksConcerns", 1, 4),
            "outlookGuidance": clean_array(payload.get("outlookGuidance"), "outlookGuidance", 1, 4),
        }

    def _build_insert_params(
        self,
        fiscal_period_label: str,
        call_date: Optional[date],
        transcript_url: Optional[str],
        transcript_text: str,
        transcript_segments: List[str],
        tone_summary: Dict[str, Any],
        structured_output: Dict[str, Any],
        raw_model_response: Dict[str, Any],
        raw_transcript_payload: Dict[str, Any],
    ) -> Tuple:
        return (
            self.SYMBOL,
            fiscal_period_label,
            call_date,
            self.SOURCE,
            transcript_url,
            len(transcript_text),
            len(transcript_segments),
            str(tone_summary.get("analyzer", "prosusai_finbert_v1"))[:64],
            json.dumps(tone_summary, ensure_ascii=True),
            structured_output["overallTone"],
            json.dumps(structured_output["keyHighlights"], ensure_ascii=True),
            json.dumps(structured_output["mainRisksConcerns"], ensure_ascii=True),
            json.dumps(structured_output["outlookGuidance"], ensure_ascii=True),
            self.config.ai.provider,
            self.config.ai.model,
            self.PROMPT_VERSION,
            json.dumps(raw_model_response, ensure_ascii=True),
            json.dumps(raw_transcript_payload, ensure_ascii=True),
        )

    def persist_analysis(self, params: Tuple) -> int:
        sql = """
        INSERT INTO earnings_ai_analysis (
            symbol, fiscal_period_label, call_date, source, transcript_url,
            transcript_char_count, transcript_segment_count, tone_analyzer, tone_summary_json,
            overall_tone, key_highlights_json, main_risks_concerns_json, outlook_guidance_json,
            provider, model_name, prompt_version, raw_model_response_json, raw_transcript_payload_json
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON DUPLICATE KEY UPDATE
            call_date = VALUES(call_date),
            source = VALUES(source),
            transcript_url = VALUES(transcript_url),
            transcript_char_count = VALUES(transcript_char_count),
            transcript_segment_count = VALUES(transcript_segment_count),
            tone_analyzer = VALUES(tone_analyzer),
            tone_summary_json = VALUES(tone_summary_json),
            overall_tone = VALUES(overall_tone),
            key_highlights_json = VALUES(key_highlights_json),
            main_risks_concerns_json = VALUES(main_risks_concerns_json),
            outlook_guidance_json = VALUES(outlook_guidance_json),
            provider = VALUES(provider),
            model_name = VALUES(model_name),
            prompt_version = VALUES(prompt_version),
            raw_model_response_json = VALUES(raw_model_response_json),
            raw_transcript_payload_json = VALUES(raw_transcript_payload_json),
            updated_at = CURRENT_TIMESTAMP
        """
        self.db.execute(sql, params)
        return 1

    def collect_latest_analysis(self) -> int:
        """Analyze only the latest quarter (legacy entry point)."""
        if not self.ensure_table():
            logger.error("Failed to ensure earnings_ai_analysis table")
            return 0
        try:
            context = self._load_latest_transcript_context()
            if context is None:
                return 0
            return 1 if self._analyze_single_quarter(context) else 0
        except EarningsToneAnalysisError as e:
            logger.error("%s", e)
            return 0
        except ValueError as e:
            logger.error("%s", e)
            return 0
        except Exception as e:
            logger.error("Error collecting AAPL earnings AI analysis: %s", e)
            return 0


    def _analyze_single_quarter(self, context: Dict[str, Any]) -> bool:
        """Run FinBERT + GPT analysis for a single quarter context. Returns True on success."""
        transcript_text = self.tone_analyzer.normalize_whitespace(context["transcriptText"])
        if len(transcript_text) < self.MIN_TRANSCRIPT_CHAR_COUNT:
            logger.warning(
                "Transcript too short for AI analysis: chars=%s period=%s",
                len(transcript_text), context["fiscalPeriodLabel"],
            )
            return False

        transcript_segments = self.tone_analyzer.prepare_segments(transcript_text)
        if len(transcript_segments) < self.MIN_SEGMENT_COUNT:
            logger.warning(
                "Too few segments for FinBERT: segments=%s period=%s",
                len(transcript_segments), context["fiscalPeriodLabel"],
            )
            return False

        tone_summary = self.tone_analyzer.analyze_segments(transcript_segments)
        instructions, prompt_input = self._build_prompt(
            fiscal_period_label=context["fiscalPeriodLabel"],
            call_date=context["callDate"],
            transcript_segments=transcript_segments,
            tone_summary=tone_summary,
        )
        raw_model_response = self.ai_client.create_structured_response(
            instructions=instructions,
            input_text=prompt_input,
            schema_name="earnings_ai_analysis",
            schema=self._response_schema(),
        )
        parsed_output = OpenAIResponsesClient.extract_json_output(raw_model_response)
        structured_output = self._validate_model_output(parsed_output)

        params = self._build_insert_params(
            fiscal_period_label=context["fiscalPeriodLabel"],
            call_date=context["callDate"],
            transcript_url=context["transcriptUrl"],
            transcript_text=transcript_text,
            transcript_segments=transcript_segments,
            tone_summary=tone_summary,
            structured_output=structured_output,
            raw_model_response=raw_model_response,
            raw_transcript_payload=context["transcriptPayload"],
        )
        self.persist_analysis(params)
        logger.info(
            "Saved AAPL earnings AI analysis: period=%s tone=%s",
            context["fiscalPeriodLabel"], structured_output["overallTone"],
        )
        return True

    def collect_recent_analyses(self, max_quarters: int = 4) -> int:
        """Fetch and persist AI analysis for the most recent *max_quarters* quarters."""
        if not self.ensure_table():
            logger.error("Failed to ensure earnings_ai_analysis table")
            return 0

        try:
            earnings_payload = self.transcript_collector.api_client.get_earnings(self.SYMBOL)
        except (ValueError, Exception) as e:
            logger.error("Error fetching earnings data: %s", e)
            return 0

        rows = AppleEarningsCommentaryCollector._recent_earnings_rows(earnings_payload, max_quarters)
        if not rows:
            logger.warning("No quarterly earnings rows found for %s", self.SYMBOL)
            return 0

        saved = 0
        for row in rows:
            fiscal_date = AppleEarningsCommentaryCollector._parse_date(row.get("fiscalDateEnding"))
            if fiscal_date is None:
                continue

            fiscal_period_label = AppleEarningsCommentaryCollector._derive_period_label(fiscal_date)
            call_date = AppleEarningsCommentaryCollector._parse_date(row.get("reportedDate"))

            if self.db.has_valid_earnings_ai_analysis(self.SYMBOL, fiscal_period_label):
                logger.debug("Skipping %s %s — valid AI analysis already exists", self.SYMBOL, fiscal_period_label)
                continue

            try:
                context = self._load_transcript_context_for_quarter(fiscal_period_label, call_date)
                if context is None:
                    continue
                if self._analyze_single_quarter(context):
                    saved += 1
            except EarningsToneAnalysisError as e:
                logger.error("FinBERT error for %s: %s", fiscal_period_label, e)
            except ValueError as e:
                logger.error("Validation error for %s: %s", fiscal_period_label, e)
            except Exception as e:
                logger.error("Error analyzing %s: %s", fiscal_period_label, e)

        logger.info("Saved %d AI analyses for %s", saved, self.SYMBOL)
        return saved


def run_aapl_earnings_ai_analysis_once() -> int:
    collector = AppleEarningsAIAnalysisCollector()
    return collector.collect_recent_analyses()


def main():
    parser = argparse.ArgumentParser(
        description="Collect AAPL earnings call transcripts and store AI earnings analyses"
    )
    parser.parse_args()
    rows = run_aapl_earnings_ai_analysis_once()
    print(f"AAPL earnings AI analysis complete. Affected rows: {rows}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    main()
