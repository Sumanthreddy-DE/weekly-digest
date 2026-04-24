import logging
import time

import requests

log = logging.getLogger(__name__)
DEGRADED_PREFIX = "[PARTIAL] "


def _call(prompt: str, config: dict) -> str:
    res = config["openclaw_resilience"]
    url = f"{config['openclaw']['base_url']}/api/generate"
    last_exc = None
    for attempt in range(res["max_retries"] + 1):
        try:
            r = requests.post(
                url,
                json={"model": "default", "prompt": prompt, "stream": False},
                timeout=res["timeout_seconds"],
            )
            r.raise_for_status()
            return r.json().get("response", "")
        except Exception as e:
            last_exc = e
            if attempt < res["max_retries"]:
                time.sleep(2 ** attempt)
    raise last_exc


def _extractive(text: str, chars: int) -> str:
    return DEGRADED_PREFIX + text[:chars].strip()


def summarize_newsletters(newsletters: list, config: dict) -> list:
    res = config["openclaw_resilience"]
    results = []
    for nl in newsletters:
        body = nl["body"][: res["max_input_chars"]]
        prompt = f"Summarize in 2-3 bullet point key takeaways.\n\nSubject: {nl['subject']}\n\n{body}"
        try:
            summary = _call(prompt, config)
        except Exception as e:
            log.warning("OpenClaw failed for '%s': %s", nl.get("subject"), e)
            summary = _extractive(nl["body"], res["degraded_extract_chars"])
        results.append({**nl, "summary": summary})
    return results


def summarize_job_intel(items: list, config: dict) -> list:
    res = config["openclaw_resilience"]
    results = []
    for item in items:
        text = f"{item.get('title', '')} , {item.get('summary', '')}"[: res["max_input_chars"]]
        prompt = (
            "In 1-3 sentences: what happened, who they are, where based, "
            f"relevance to computational engineering / AI / simulation.\n\n{text}"
        )
        try:
            summary = _call(prompt, config)
        except Exception as e:
            log.warning("OpenClaw failed for '%s': %s", item.get("url"), e)
            summary = _extractive(text, res["degraded_extract_chars"])
        results.append({**item, "summary": summary})
    return results
