import logging
import urllib.parse

import feedparser

log = logging.getLogger(__name__)

_GOOGLE_NEWS = "https://news.google.com/rss/search?q={query}&hl=en&gl=US&ceid=US:en"


def _feed_urls(config: dict) -> list:
    return [
        _GOOGLE_NEWS.format(query=urllib.parse.quote(f"{sector} {signal}"))
        for sector in config["keywords"]["sectors"]
        for signal in config["keywords"]["signals"]
    ]


def fetch_via_rss(config: dict) -> list:
    seen = set()
    results = []
    for url in _feed_urls(config):
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                link = entry.get("link", "")
                if not link or link in seen:
                    continue
                seen.add(link)
                results.append({
                    "url": link,
                    "title": entry.get("title", ""),
                    "summary": entry.get("summary", ""),
                    "source": "rss",
                })
        except Exception as e:
            log.warning("RSS error for %s: %s", url, e)
    log.info("RSS fallback: %d items", len(results))
    return results
