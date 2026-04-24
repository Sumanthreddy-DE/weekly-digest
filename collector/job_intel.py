import logging

from collector.apify_scraper import ApifyFetchError, fetch_via_apify
from collector.rss_scraper import fetch_via_rss

log = logging.getLogger(__name__)

_DE = ["germany", "german", "berlin", "munich", "münchen", "hamburg", "frankfurt", "stuttgart", "cologne", ".de"]
_EU = ["europe", "european", "france", "french", "paris", "netherlands", "sweden", "uk", "britain", "spain", "italy", ".eu"]


def _location(text: str) -> str:
    t = text.lower()
    if any(k in t for k in _DE):
        return "DE"
    if any(k in t for k in _EU):
        return "EU"
    return "Global"


def _normalize(raw: dict) -> dict:
    url = raw.get("url") or raw.get("link") or ""
    title = raw.get("title") or ""
    summary = raw.get("summary") or raw.get("description") or ""
    return {
        "id": url,
        "type": "job_intel",
        "url": url,
        "title": title,
        "summary": summary,
        "location": _location(f"{title} {summary} {url}"),
    }


def fetch_job_intel(config: dict, state: dict) -> list:
    existing_ids = {i["id"] for i in state.get("items", [])}
    try:
        raw = fetch_via_apify(config)
        log.info("Job intel: Apify (%d raw)", len(raw))
    except ApifyFetchError as e:
        log.warning("Apify failed (%s), using RSS fallback", e)
        raw = fetch_via_rss(config)
        log.info("Job intel: RSS fallback (%d raw)", len(raw))

    normalized = [_normalize(r) for r in raw]
    result = [i for i in normalized if i["id"] and i["id"] not in existing_ids]
    log.info("Job intel: %d after dedup", len(result))
    return result
