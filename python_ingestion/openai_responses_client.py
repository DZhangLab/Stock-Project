"""
Minimal OpenAI Responses API client for structured JSON outputs.
"""
import json
import logging
from typing import Any, Dict, Optional

import requests

from .config import AIConfig, load_config

logger = logging.getLogger(__name__)


class OpenAIResponsesClient:
    """Client for OpenAI Responses API structured outputs."""

    def __init__(self, config: Optional[AIConfig] = None):
        if config is None:
            config = load_config().ai
        self.config = config

    def create_structured_response(
        self,
        instructions: str,
        input_text: str,
        schema_name: str,
        schema: Dict[str, Any],
    ) -> Dict[str, Any]:
        if self.config.provider != "openai":
            raise ValueError(f"Unsupported AI provider: {self.config.provider}")
        if not self.config.api_key:
            raise ValueError("Missing OPENAI_API_KEY. Set it in python_ingestion/.env before running AI summary.")

        payload = {
            "model": self.config.model,
            "instructions": instructions,
            "input": input_text,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "schema": schema,
                    "strict": True,
                }
            },
        }

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        response = requests.post(
            self.config.base_url,
            headers=headers,
            json=payload,
            timeout=self.config.timeout,
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("OpenAI response is not a JSON object")
        return data

    @staticmethod
    def extract_json_output(response_json: Dict[str, Any]) -> Dict[str, Any]:
        output_text = response_json.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            parsed = json.loads(output_text)
            if not isinstance(parsed, dict):
                raise ValueError("Structured model output must be a JSON object")
            return parsed

        output_items = response_json.get("output", [])
        if not isinstance(output_items, list):
            raise ValueError("OpenAI response output field is invalid")

        for item in output_items:
            if not isinstance(item, dict):
                continue
            content = item.get("content", [])
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict):
                    continue
                text_value = block.get("text")
                if isinstance(text_value, str) and text_value.strip():
                    parsed = json.loads(text_value)
                    if not isinstance(parsed, dict):
                        raise ValueError("Structured model output must be a JSON object")
                    return parsed

        raise ValueError("OpenAI response did not contain structured JSON output")
