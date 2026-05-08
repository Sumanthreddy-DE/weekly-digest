from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

from discovery.models import Company, SourceRef
from discovery.sources.base import SourceBase

log = logging.getLogger(__name__)


class HNHiringSource(SourceBase):
    name = "hn_who_is_hiring"
    geo_tier = "GLOBAL"
    extractor = "custom-hn-hiring"
    SEARCH_URL = "https://hn.algolia.com/api/v1/search"
    ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{}.json"

    RELEVANT_KEYWORDS = [
        "ai", "machine learning", "ml", "simulation", "engineering",
        "cae", "cad", "fea", "digital twin", "computational",
    ]

    def iter_pages(self, start_page: int):
        if start_page > 1:
            return

        post_id = self._find_latest_hiring_post()
        if not post_id:
            log.warning("Could not find latest 'Who is Hiring?' post")
            return

        post_data = requests.get(self.ITEM_URL.format(post_id), timeout=30).json()
        if not post_data or "kids" not in post_data:
            return

        companies = []
        now = datetime.now(timezone.utc).isoformat()
        comment_ids = post_data["kids"][:200]

        for idx, comment_id in enumerate(comment_ids):
            try:
                comment = requests.get(
                    self.ITEM_URL.format(comment_id), timeout=10
                ).json()
                if not comment or comment.get("deleted") or not comment.get("text"):
                    continue

                text = BeautifulSoup(comment["text"], "html.parser").get_text(separator="\n")
                company = self._parse_comment(text, comment_id, now)
                if company:
                    companies.append(company)
            except Exception as exc:
                log.debug("HN comment %s failed: %s", comment_id, exc)

            if idx % 10 == 0:
                time.sleep(0.5)

        yield 1, f"https://news.ycombinator.com/item?id={post_id}", companies

    def _find_latest_hiring_post(self) -> str | None:
        params = {
            "query": "Ask HN: Who is hiring?",
            "tags": "story",
            "hitsPerPage": 5,
        }
        resp = requests.get(self.SEARCH_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        hits = data.get("hits", [])
        if not hits:
            return None
        return str(hits[0]["objectID"])

    @staticmethod
    def _matches_any_keyword(text: str, keywords: list[str]) -> bool:
        lowered = text.lower()
        for kw in keywords:
            pattern = r'\b' + re.escape(kw.lower()) + r'\b'
            if re.search(pattern, lowered):
                return True
        return False

    def _parse_comment(self, text: str, comment_id: int, now: str) -> Company | None:
        lines = text.strip().split("\n")
        if not lines:
            return None

        if not self._matches_any_keyword(text, self.RELEVANT_KEYWORDS):
            return None

        first_line = lines[0].strip()
        match = re.match(r"^([^|:\-–—]+)", first_line)
        if not match:
            return None

        name = match.group(1).strip()
        if not name or len(name) < 2 or len(name) > 80:
            return None

        url_match = re.search(r"https?://[^\s<>\"{}|\\^`\[\]]+", text)
        homepage = url_match.group(0) if url_match else None

        location_match = re.search(
            r"\b(Berlin|Munich|Hamburg|Cologne|Frankfurt|Stuttgart|"
            r"Düsseldorf|Leipzig|Dresden|Nuremberg|Germany)\b",
            text,
            re.IGNORECASE,
        )
        country = "DE" if location_match else None
        city = None
        if location_match:
            city = location_match.group(1).title()
            if city.lower() == "germany":
                city = None

        lowered = text.lower()
        sectors = []
        if re.search(r'\bai\b', lowered):
            sectors.append("ai_engineering")

        return Company(
            name=name,
            homepage=homepage,
            country=country,
            city=city,
            geo_tier="DE" if country == "DE" else "GLOBAL",
            sectors=sectors,
            ai_focus=text[:300],
            stage=None,
            size=None,
            sources=[
                SourceRef(
                    url=f"https://news.ycombinator.com/item?id={comment_id}",
                    fetched_at=now,
                    extractor=self.extractor,
                )
            ],
            last_seen_at=now,
            notes=None,
        )
