"""
AAPL-only earnings call AI analysis job.
Phase 2 MVP: transcript segmentation + tone signals + LLM structured summary.
"""
import argparse
import json
import logging
import re
import time
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from ..config import load_config
from ..db import get_db_manager
from ..openai_responses_client import OpenAIResponsesClient
from .aapl_earnings_commentary import AppleEarningsCommentaryCollector

logger = logging.getLogger(__name__)


class EarningsToneAnalyzer:
    """Clean FinBERT integration point with a deterministic placeholder fallback."""

    POSITIVE_KEYWORDS = [
        "record", "strong", "improved", "growth", "grew", "accelerated", "expanding",
        "momentum", "confidence", "healthy", "resilient", "outperformed", "beat",
        "above", "up", "strength", "opportunity", "efficient", "disciplined",
    ]
    NEGATIVE_KEYWORDS = [
        "risk", "risks", "concern", "concerns", "pressure", "headwind", "headwinds",
        "decline", "declined", "down", "weakness", "softness", "constraint",
        "constraints", "challenging", "uncertain", "uncertainty", "difficult",
        "volatile", "slowdown", "lower", "below",
    ]

    def __init__(self, mode: str = "placeholder_finbert_v1"):
        self.mode = mode

    def analyze_segments(self, segments: List[str]) -> Dict[str, Any]:
        analyzed_segments: List[Dict[str, Any]] = []
        positive_count = 0
        negative_count = 0
        mixed_count = 0

        for index, segment in enumerate(segments):
            result = self._score_segment(segment)
            result["index"] = index
            analyzed_segments.append(result)

            label = result["toneLabel"]
            if label == "positive":
                positive_count += 1
            elif label == "negative":
                negative_count += 1
            else:
                mixed_count += 1

        overall_tone = "mixed"
        if positive_count > negative_count and positive_count >= max(2, mixed_count):
            overall_tone = "positive"
        elif negative_count > positive_count and negative_count >= max(2, mixed_count):
            overall_tone = "negative"

        return {
            "analyzer": self.mode,
            "overallTone": overall_tone,
            "segmentCount": len(analyzed_segments),
            "positiveSegmentCount": positive_count,
            "mixedSegmentCount": mixed_count,
            "negativeSegmentCount": negative_count,
            "segments": analyzed_segments,
        }

    def _score_segment(self, segment: str) -> Dict[str, Any]:
        text = segment.lower()
        positive_hits = sum(1 for keyword in self.POSITIVE_KEYWORDS if keyword in text)
        negative_hits = sum(1 for keyword in self.NEGATIVE_KEYWORDS if keyword in text)
        score = positive_hits - negative_hits

        if score >= 2:
            label = "positive"
        elif score <= -2:
            label = "negative"
        else:
            label = "mixed"

        return {
            "toneLabel": label,
            "score": score,
            "positiveHits": positive_hits,
            "negativeHits": negative_hits,
            "excerpt": segment[:280],
        }


class AppleEarningsAIAnalysisCollector:
    SYMBOL = "AAPL"
    SOURCE = "ALPHA_VANTAGE"
    PROMPT_VERSION = "earnings_ai_analysis_v1"
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
        self.tone_analyzer = EarningsToneAnalyzer()

    def ensure_table(self) -> bool:
        return self.db.ensure_earnings_ai_analysis_table()

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

        time.sleep(self.REQUEST_DELAY_SECONDS)
        transcript_payload = self.transcript_collector.api_client.get_earnings_call_transcript(
            self.SYMBOL,
            fiscal_period_label,
        )
        if not isinstance(transcript_payload, dict):
            logger.warning("Transcript payload is not a dict for %s %s", self.SYMBOL, fiscal_period_label)
            transcript_payload = {}

        transcript_text = AppleEarningsCommentaryCollector._extract_transcript_text(transcript_payload)
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

    @staticmethod
    def _normalize_whitespace(value: str) -> str:
        return re.sub(r"\s+", " ", value or "").strip()

    def _prepare_segments(self, transcript_text: str) -> List[str]:
        cleaned = transcript_text.replace("\r", "\n")
        cleaned = re.sub(r"\n{2,}", "\n", cleaned)

        raw_parts = re.split(r"\n(?=[A-Z][A-Za-z .'-]{1,80}:)", cleaned)
        parts = raw_parts if len(raw_parts) > 1 else re.split(r"(?<=[.!?])\s+", self._normalize_whitespace(cleaned))

        segments: List[str] = []
        current = ""
        for part in parts:
            text = self._normalize_whitespace(part)
            if len(text) < 40:
                continue
            if not current:
                current = text
                continue
            if len(current) + 1 + len(text) <= self.MAX_SEGMENT_CHARS:
                current = current + " " + text
                continue
            segments.append(current)
            current = text

        if current:
            segments.append(current)

        return segments

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

    def _build_prompt(
        self,
        fiscal_period_label: str,
        call_date: Optional[date],
        transcript_segments: List[str],
        tone_summary: Dict[str, Any],
    ) -> Tuple[str, str]:
        instructions = (
            "You are a financial earnings-call analyst. "
            "Analyze the latest AAPL earnings call transcript using the provided transcript excerpts and tone summary. "
            "Keep the answer grounded in transcript evidence, avoid speculation, and return valid JSON matching the schema exactly. "
            "Tone labels must be one of positive, mixed, or negative. "
            "Each bullet should be concise and decision-useful."
        )

        prioritized_segments = sorted(
            tone_summary.get("segments", []),
            key=lambda item: (abs(int(item.get("score", 0))), -int(item.get("index", 0))),
            reverse=True,
        )
        selected_indexes = sorted(
            {item.get("index") for item in prioritized_segments[: self.MAX_PROMPT_SEGMENTS // 2]}
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
            "toneSummary": {
                "analyzer": tone_summary.get("analyzer"),
                "overallTone": tone_summary.get("overallTone"),
                "segmentCount": tone_summary.get("segmentCount"),
                "positiveSegmentCount": tone_summary.get("positiveSegmentCount"),
                "mixedSegmentCount": tone_summary.get("mixedSegmentCount"),
                "negativeSegmentCount": tone_summary.get("negativeSegmentCount"),
                "topToneExcerpts": [
                    {
                        "toneLabel": item.get("toneLabel"),
                        "score": item.get("score"),
                        "excerpt": item.get("excerpt"),
                    }
                    for item in prioritized_segments[:4]
                ],
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

        def clean_array(value: Any, field_name: str, minimum: int, maximum: int) -> List[str]:
            if not isinstance(value, list):
                raise ValueError("Model output %s must be an array" % field_name)
            cleaned: List[str] = []
            seen = set()
            for item in value:
                text = self._normalize_whitespace(str(item))
                if not text:
                    continue
                key = text.lower()
                if key in seen:
                    continue
                seen.add(key)
                cleaned.append(text[:220])
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
            str(tone_summary.get("analyzer", "placeholder_finbert_v1"))[:64],
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
        if not self.ensure_table():
            logger.error("Failed to ensure earnings_ai_analysis table")
            return 0

        try:
            context = self._load_latest_transcript_context()
            if context is None:
                return 0

            transcript_text = self._normalize_whitespace(context["transcriptText"])
            if len(transcript_text) < self.MIN_TRANSCRIPT_CHAR_COUNT:
                logger.warning(
                    "Transcript text is insufficient for AI analysis: chars=%s period=%s",
                    len(transcript_text),
                    context["fiscalPeriodLabel"],
                )
                return 0

            transcript_segments = self._prepare_segments(transcript_text)
            if len(transcript_segments) < self.MIN_SEGMENT_COUNT:
                logger.warning(
                    "Transcript segmentation is insufficient for AI analysis: segments=%s period=%s",
                    len(transcript_segments),
                    context["fiscalPeriodLabel"],
                )
                return 0

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
                "Saved AAPL earnings AI analysis: period=%s call_date=%s tone=%s",
                context["fiscalPeriodLabel"],
                context["callDate"],
                structured_output["overallTone"],
            )
            return 1
        except ValueError as e:
            logger.error("%s", e)
            return 0
        except Exception as e:
            logger.error("Error collecting AAPL earnings AI analysis: %s", e)
            return 0


def run_aapl_earnings_ai_analysis_once() -> int:
    collector = AppleEarningsAIAnalysisCollector()
    return collector.collect_latest_analysis()


def main():
    parser = argparse.ArgumentParser(
        description="Collect latest AAPL earnings call transcript and store AI earnings analysis"
    )
    parser.parse_args()
    rows = run_aapl_earnings_ai_analysis_once()
    print(f"AAPL earnings AI analysis complete. Affected rows: {rows}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    main()
