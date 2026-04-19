"""
Tone analyzers for earnings transcript analysis (symbol-agnostic).
"""
import os
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
except ImportError:  # pragma: no cover - dependency availability is environment-specific
    torch = None
    AutoModelForSequenceClassification = None
    AutoTokenizer = None


class EarningsToneAnalysisError(RuntimeError):
    """Raised when tone analysis cannot proceed safely."""


class BaseEarningsToneAnalyzer:
    MIN_SENTENCE_LENGTH = 35
    MAX_SENTENCE_LENGTH = 420
    BUSINESS_PRIORITY_KEYWORDS = {
        "iphone": 3.0,
        "services": 3.0,
        "revenue": 2.5,
        "gross margin": 2.5,
        "margin": 1.8,
        "eps": 2.0,
        "china": 2.5,
        "greater china": 2.5,
        "mac": 2.0,
        "ipad": 1.5,
        "wearables": 1.5,
        "installed base": 2.5,
        "tariff": 2.2,
        "demand": 2.0,
        "channel inventory": 2.2,
        "supply chain": 2.0,
        "cash flow": 1.6,
        "product mix": 1.5,
    }
    GUIDANCE_KEYWORDS = [
        "guidance", "outlook", "expect", "expects", "expected", "anticipate",
        "anticipates", "forecast", "future", "next quarter", "remain confident",
        "we believe", "we expect", "we continue", "going forward", "pipeline",
    ]
    RISK_KEYWORDS = [
        "risk", "risks", "concern", "concerns", "pressure", "headwind", "headwinds",
        "constraint", "constraints", "softness", "uncertain", "uncertainty",
        "challenging", "volatile", "slowdown", "weakness", "decline", "down",
        "lower", "macroeconomic", "tariff", "competition", "supply", "foreign exchange",
    ]
    STRONG_RISK_KEYWORDS = [
        "fell", "decline", "declined", "pressure", "headwind", "constraint",
        "constraints", "weakness", "softness", "tariff", "macroeconomic",
        "regulatory", "legal proceedings", "lower", "slower",
    ]
    EMPHASIS_KEYWORDS = [
        "record", "best", "strong", "accelerated", "double-digit", "all-time high",
        "material", "meaningful", "significant", "well above", "well below",
    ]
    BOILERPLATE_PATTERNS = [
        "welcome to",
        "today's call is being recorded",
        "forward-looking statements",
        "actual results could differ",
        "please refer to",
        "question-and-answer",
        "question and answer",
        "operator instructions",
        "turn the call over",
    ]

    analyzer_label = "base"

    @staticmethod
    def normalize_whitespace(value: str) -> str:
        return re.sub(r"\s+", " ", value or "").strip()

    def prepare_segments(self, transcript_text: str) -> List[str]:
        cleaned = transcript_text.replace("\r", "\n")
        cleaned = re.sub(r"\n{2,}", "\n", cleaned)

        speaker_blocks = re.split(r"\n(?=[A-Z][A-Za-z .'-]{1,80}:)", cleaned)
        raw_sentences: List[str] = []
        for block in speaker_blocks:
            normalized_block = self.normalize_whitespace(block)
            if not normalized_block:
                continue
            raw_sentences.extend(re.split(r"(?<=[.!?])\s+", normalized_block))

        prepared: List[str] = []
        for sentence in raw_sentences:
            text = self.normalize_whitespace(sentence)
            if not self._is_usable_sentence(text):
                continue
            prepared.append(text)
        return prepared

    def _is_usable_sentence(self, text: str) -> bool:
        if len(text) < self.MIN_SENTENCE_LENGTH or len(text) > self.MAX_SENTENCE_LENGTH:
            return False
        lower = text.lower()
        if any(pattern in lower for pattern in self.BOILERPLATE_PATTERNS):
            return False
        if lower.startswith("operator:") or lower.startswith("analyst:"):
            return False
        if lower.count(" ") < 5:
            return False
        alpha_chars = sum(1 for char in text if char.isalpha())
        if alpha_chars < 20:
            return False
        return True

    @classmethod
    def is_guidance_relevant(cls, text: str) -> bool:
        lower = text.lower()
        return any(keyword in lower for keyword in cls.GUIDANCE_KEYWORDS)

    @classmethod
    def is_risk_relevant(cls, text: str) -> bool:
        lower = text.lower()
        return any(keyword in lower for keyword in cls.RISK_KEYWORDS)

    def analyze_segments(self, segments: List[str]) -> Dict[str, Any]:
        raise NotImplementedError

    @classmethod
    def business_priority_score(cls, text: str) -> float:
        lower = text.lower()
        score = 0.0
        for keyword, weight in cls.BUSINESS_PRIORITY_KEYWORDS.items():
            if keyword in lower:
                score += weight
        return round(score, 3)

    @classmethod
    def emphasis_score(cls, text: str) -> float:
        lower = text.lower()
        score = 0.0
        for keyword in cls.EMPHASIS_KEYWORDS:
            if keyword in lower:
                score += 1.0
        if "%" in text:
            score += 0.6
        if "$" in text:
            score += 0.8
        if any(char.isdigit() for char in text):
            score += 0.4
        return round(score, 3)

    @classmethod
    def risk_signal_score(cls, text: str) -> float:
        lower = text.lower()
        score = 0.0
        for keyword in cls.STRONG_RISK_KEYWORDS:
            if keyword in lower:
                score += 1.2
        for keyword in cls.RISK_KEYWORDS:
            if keyword in lower:
                score += 0.6
        if "flat" in lower and ("demand" in lower or "revenue" in lower or "sales" in lower):
            score += 0.4
        return round(score, 3)

    @classmethod
    def guidance_signal_score(cls, text: str) -> float:
        lower = text.lower()
        score = 0.0
        for keyword in cls.GUIDANCE_KEYWORDS:
            if keyword in lower:
                score += 1.0
        if "will" in lower:
            score += 0.4
        if "next quarter" in lower or "december quarter" in lower:
            score += 0.8
        return round(score, 3)

    @classmethod
    def infer_themes(cls, text: str) -> List[str]:
        lower = text.lower()
        themes: List[str] = []
        mappings = [
            ("iphone", "iPhone demand"),
            ("services", "Services growth"),
            ("greater china", "China performance"),
            ("china", "China performance"),
            ("gross margin", "Margin profile"),
            ("margin", "Margin profile"),
            ("tariff", "Tariff exposure"),
            ("channel inventory", "Channel inventory"),
            ("installed base", "Installed base"),
            ("mac", "Mac demand"),
            ("ipad", "iPad demand"),
            ("revenue", "Revenue trajectory"),
        ]
        for keyword, label in mappings:
            if keyword in lower and label not in themes:
                themes.append(label)
        return themes[:3]


class PlaceholderEarningsToneAnalyzer(BaseEarningsToneAnalyzer):
    """Fallback analyzer retained for explicit non-production use."""

    analyzer_label = "placeholder_finbert_v1"
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

    def analyze_segments(self, segments: List[str]) -> Dict[str, Any]:
        analyzed_segments: List[Dict[str, Any]] = []
        for index, segment in enumerate(segments):
            lower = segment.lower()
            positive_hits = sum(1 for keyword in self.POSITIVE_KEYWORDS if keyword in lower)
            negative_hits = sum(1 for keyword in self.NEGATIVE_KEYWORDS if keyword in lower)
            score = float(positive_hits - negative_hits)
            if score >= 2:
                label = "positive"
            elif score <= -2:
                label = "negative"
            else:
                label = "mixed"
            analyzed_segments.append(
                {
                    "index": index,
                    "toneLabel": label,
                    "rawLabel": label,
                    "confidence": min(0.99, 0.5 + (abs(score) * 0.1)),
                    "score": score,
                    "excerpt": segment[:280],
                    "text": segment,
                    "isGuidanceRelevant": self.is_guidance_relevant(segment),
                    "isRiskRelevant": self.is_risk_relevant(segment),
                    "businessPriorityScore": self.business_priority_score(segment),
                    "emphasisScore": self.emphasis_score(segment),
                    "riskSignalScore": self.risk_signal_score(segment),
                    "guidanceSignalScore": self.guidance_signal_score(segment),
                    "themes": self.infer_themes(segment),
                }
            )
        return _aggregate_tone_summary(self.analyzer_label, "heuristic", analyzed_segments)


class FinBertEarningsToneAnalyzer(BaseEarningsToneAnalyzer):
    MODEL_NAME = "ProsusAI/finbert"
    analyzer_label = "prosusai_finbert_v1"

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = (model_name or os.getenv("FINBERT_MODEL_NAME", self.MODEL_NAME)).strip() or self.MODEL_NAME
        self.tokenizer = None
        self.model = None

    def _ensure_model_loaded(self):
        if AutoTokenizer is None or AutoModelForSequenceClassification is None or torch is None:
            raise EarningsToneAnalysisError(
                "FinBERT dependencies are unavailable. Install transformers and torch before running earnings AI analysis."
            )
        if self.tokenizer is not None and self.model is not None:
            return

        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
            self.model.eval()
        except Exception as e:
            raise EarningsToneAnalysisError("Failed to load FinBERT model %s: %s" % (self.model_name, e))

    def analyze_segments(self, segments: List[str]) -> Dict[str, Any]:
        if len(segments) < 3:
            raise EarningsToneAnalysisError("Usable FinBERT sentence count is too small")

        self._ensure_model_loaded()

        analyzed_segments: List[Dict[str, Any]] = []
        batch_size = 12
        for batch_start in range(0, len(segments), batch_size):
            batch = segments[batch_start: batch_start + batch_size]
            try:
                tokenized = self.tokenizer(
                    batch,
                    padding=True,
                    truncation=True,
                    max_length=256,
                    return_tensors="pt",
                )
                with torch.no_grad():
                    logits = self.model(**tokenized).logits
                    probabilities = torch.softmax(logits, dim=1)
            except Exception as e:
                raise EarningsToneAnalysisError("FinBERT inference failed: %s" % e)

            for offset, segment in enumerate(batch):
                row = probabilities[offset].detach().cpu().tolist()
                labels = self.model.config.id2label
                score_by_label = {
                    str(labels[index]).lower(): float(value)
                    for index, value in enumerate(row)
                }
                positive_score = score_by_label.get("positive", 0.0)
                negative_score = score_by_label.get("negative", 0.0)
                neutral_score = score_by_label.get("neutral", 0.0)
                raw_label = max(score_by_label, key=score_by_label.get)
                tone_label = "mixed" if raw_label == "neutral" else raw_label
                confidence = float(score_by_label.get(raw_label, 0.0))
                analyzed_segments.append(
                    {
                        "index": batch_start + offset,
                        "toneLabel": tone_label,
                        "rawLabel": raw_label,
                        "confidence": round(confidence, 6),
                        "score": round(positive_score - negative_score, 6),
                        "positiveScore": round(positive_score, 6),
                        "neutralScore": round(neutral_score, 6),
                        "negativeScore": round(negative_score, 6),
                        "excerpt": segment[:280],
                        "text": segment,
                        "isGuidanceRelevant": self.is_guidance_relevant(segment),
                        "isRiskRelevant": self.is_risk_relevant(segment),
                        "businessPriorityScore": self.business_priority_score(segment),
                        "emphasisScore": self.emphasis_score(segment),
                        "riskSignalScore": self.risk_signal_score(segment),
                        "guidanceSignalScore": self.guidance_signal_score(segment),
                        "themes": self.infer_themes(segment),
                    }
                )

        return _aggregate_tone_summary(self.analyzer_label, self.model_name, analyzed_segments)


def _aggregate_tone_summary(analyzer_label: str, model_name: str, analyzed_segments: List[Dict[str, Any]]) -> Dict[str, Any]:
    positive_count = 0
    negative_count = 0
    mixed_count = 0
    aggregate_score = 0.0

    for result in analyzed_segments:
        label = result.get("toneLabel")
        confidence = float(result.get("confidence", 0.0))
        score = float(result.get("score", 0.0))
        business_priority = float(result.get("businessPriorityScore", 0.0))
        aggregate_score += score * max(confidence, 0.25) * max(1.0, business_priority / 2.5)
        if label == "positive":
            positive_count += 1
        elif label == "negative":
            negative_count += 1
        else:
            mixed_count += 1

    overall_tone = "mixed"
    if aggregate_score >= 0.35 and positive_count >= max(negative_count, 2):
        overall_tone = "positive"
    elif aggregate_score <= -0.35 and negative_count >= max(positive_count, 2):
        overall_tone = "negative"

    top_positive_signals = sorted(
        [
            item for item in analyzed_segments
            if item.get("toneLabel") == "positive" and float(item.get("businessPriorityScore", 0.0)) >= 1.5
        ],
        key=lambda item: (
            float(item.get("businessPriorityScore", 0.0)),
            float(item.get("emphasisScore", 0.0)),
            float(item.get("score", 0.0)),
            float(item.get("confidence", 0.0)),
        ),
        reverse=True,
    )[:3]
    top_negative_signals = sorted(
        [
            item for item in analyzed_segments
            if float(item.get("riskSignalScore", 0.0)) >= 1.6
            or (
                item.get("toneLabel") == "negative"
                and float(item.get("businessPriorityScore", 0.0)) >= 1.5
            )
        ],
        key=lambda item: (
            float(item.get("riskSignalScore", 0.0)),
            float(item.get("businessPriorityScore", 0.0)),
            abs(float(item.get("score", 0.0))),
            float(item.get("confidence", 0.0)),
        ),
        reverse=True,
    )[:3]
    top_guidance_signals = sorted(
        [
            item for item in analyzed_segments
            if float(item.get("guidanceSignalScore", 0.0)) >= 1.4
            and float(item.get("businessPriorityScore", 0.0)) >= 1.0
        ],
        key=lambda item: (
            float(item.get("guidanceSignalScore", 0.0)),
            float(item.get("businessPriorityScore", 0.0)),
            float(item.get("emphasisScore", 0.0)),
            float(item.get("confidence", 0.0)),
        ),
        reverse=True,
    )[:3]
    top_cautious_guidance_signals = sorted(
        [
            item for item in top_guidance_signals
            if float(item.get("riskSignalScore", 0.0)) >= 1.0 or float(item.get("score", 0.0)) < 0.0
        ],
        key=lambda item: (
            float(item.get("riskSignalScore", 0.0)),
            abs(float(item.get("score", 0.0))),
            float(item.get("confidence", 0.0)),
        ),
        reverse=True,
    )[:2]

    return {
        "analyzer": analyzer_label,
        "modelName": model_name,
        "overallTone": overall_tone,
        "segmentCount": len(analyzed_segments),
        "usableSegmentCount": len(analyzed_segments),
        "positiveSegmentCount": positive_count,
        "mixedSegmentCount": mixed_count,
        "negativeSegmentCount": negative_count,
        "aggregateScore": round(aggregate_score, 6),
        "segments": analyzed_segments,
        "topPositiveSignals": _serialize_signal_list(top_positive_signals),
        "topNegativeSignals": _serialize_signal_list(top_negative_signals),
        "topGuidanceSignals": _serialize_signal_list(top_guidance_signals),
        "topCautiousGuidanceSignals": _serialize_signal_list(top_cautious_guidance_signals),
    }


def _serialize_signal_list(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    serialized: List[Dict[str, Any]] = []
    seen = set()
    for item in items:
        excerpt = BaseEarningsToneAnalyzer.normalize_whitespace(str(item.get("excerpt", "")))[:280]
        if not excerpt:
            continue
        key = excerpt.lower()
        if key in seen:
            continue
        seen.add(key)
        serialized.append(
            {
                "index": item.get("index"),
                "toneLabel": item.get("toneLabel"),
                "rawLabel": item.get("rawLabel"),
                "confidence": item.get("confidence"),
                "score": item.get("score"),
                "businessPriorityScore": item.get("businessPriorityScore"),
                "emphasisScore": item.get("emphasisScore"),
                "riskSignalScore": item.get("riskSignalScore"),
                "guidanceSignalScore": item.get("guidanceSignalScore"),
                "themes": item.get("themes", []),
                "excerpt": excerpt,
            }
        )
    return serialized


def build_earnings_tone_analyzer() -> BaseEarningsToneAnalyzer:
    mode = os.getenv("EARNINGS_TONE_ANALYZER", "finbert").strip().lower()
    if mode in {"placeholder", "heuristic"}:
        logger.warning("Using placeholder earnings tone analyzer; not recommended for production")
        return PlaceholderEarningsToneAnalyzer()
    return FinBertEarningsToneAnalyzer()
