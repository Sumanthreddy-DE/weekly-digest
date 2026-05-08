from __future__ import annotations

import json
import logging

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

log = logging.getLogger(__name__)

EXTRACT_PROMPT = """You are a data extraction tool. Given the text below, extract any companies that blend AI/ML with mechanical, structural, composite, aerospace, packaging, hydraulics, CAE, CAD, or FEA.

Return STRICT JSON, no prose. Schema:
{
  \"companies\": [
    {
      \"name\": \"string\",
      \"homepage\": \"string or null\",
      \"country\": \"ISO 3166-1 alpha-2 or null\",
      \"city\": \"string or null\",
      \"ai_focus\": \"string (1-2 sentences)\",
      \"sectors\": [\"list of sector tags\"]
    }
  ]
}

If no companies found, return {\"companies\": []}.

TEXT:
"""


class OllamaExtractError(Exception):
    pass


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=2, min=2, max=8),
    retry=retry_if_exception_type((requests.exceptions.RequestException, OllamaExtractError)),
)
def _call_ollama(base_url: str, model: str, prompt: str, timeout: int) -> str:
    response = requests.post(
        f"{base_url}/api/generate",
        json={"model": model, "prompt": prompt, "format": "json", "stream": False},
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json().get("response", "")


def extract_companies(text: str, config: dict) -> list[dict]:
    cfg = config["discovery"]["ollama_extractor"]
    prompt = EXTRACT_PROMPT + text[:8000]
    try:
        raw = _call_ollama(
            config["openclaw"]["base_url"],
            cfg["model"],
            prompt,
            cfg["timeout_seconds"],
        )
        parsed = json.loads(raw)
        return parsed.get("companies", [])
    except json.JSONDecodeError as exc:
        log.warning("Ollama returned invalid JSON: %s", exc)
        return []
    except Exception as exc:
        log.warning("Ollama extract failed: %s", exc)
        return []
