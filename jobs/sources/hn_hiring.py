from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import Iterable

import requests
from bs4 import BeautifulSoup

from jobs.models import Job
from jobs.sources.base import JobSourceBase

log = logging.getLogger(__name__)


class HNHiringJobsSource(JobSourceBase):
    SEARCH_URL = "https://hn.algolia.com/api/v1/search"
    ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{}.json"
    RELEVANT_KEYWORDS = [
        "ai", "machine learning", "ml", "simulation", "engineering", "engineer",
        "cae", "cad", "fea", "digital twin", "computational",
    ]
    ROLE_KEYWORDS = [
        "engineer", "engineering", "machine learning", "ml", "ai",
        "simulation", "data scientist", "research engineer", "computational",
    ]
    GEO_KEYWORDS_DE = [
        "berlin", "munich", "hamburg", "cologne", "frankfurt",
        "stuttgart", "düsseldorf", "leipzig", "dresden", "nuremberg",
        "germany", "deutschland",
    ]

    def run(self) -> Iterable[Job]:
        try:
            post_id = self._find_latest_hiring_post()
            if not post_id:
                log.warning("Could not find latest 'Who is Hiring?' post")
                return []

            post_data = requests.get(self.ITEM_URL.format(post_id), timeout=30).json()
            if not post_data or "kids" not in post_data:
                return []

            jobs = []
            now = datetime.now(timezone.utc).isoformat()
            comment_ids = post_data["kids"][:200]

            for comment_id in comment_ids:
                try:
                    comment = requests.get(
                        self.ITEM_URL.format(comment_id), timeout=10
                    ).json()
                    if not comment or comment.get("deleted") or not comment.get("text"):
                        continue

                    text = BeautifulSoup(comment["text"], "html.parser").get_text(separator="\n")
                    job = self._parse_comment(text, comment_id, now)
                    if job:
                        jobs.append(job)
                except Exception as exc:
                    log.debug("HN comment %s failed: %s", comment_id, exc)

            return jobs
        except Exception as exc:
            log.warning("HN Hiring jobs fetch failed: %s", exc)
            return []

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

    def _parse_comment(self, text: str, comment_id: int, now: str) -> Job | None:
        if not self._matches_any_keyword(text, self.RELEVANT_KEYWORDS):
            return None

        first_line = text.strip().split("\n")[0] if text else ""
        match = re.match(r"^([^|:\-–—]+)", first_line)
        if not match:
            return None

        company_name = match.group(1).strip()
        if not company_name or len(company_name) < 2 or len(company_name) > 80:
            return None

        if not self._matches_any_keyword(text, self.ROLE_KEYWORDS):
            return None

        country = None
        city = None
        for geo_kw in self.GEO_KEYWORDS_DE:
            pattern = r'\b' + re.escape(geo_kw) + r'\b'
            if re.search(pattern, text, re.IGNORECASE):
                country = "DE"
                if geo_kw != "germany" and geo_kw != "deutschland":
                    city = geo_kw.title()
                break

        url_match = re.search(r"https?://[^\s<>\"{}|\\^`\[\]]+", text)
        url = url_match.group(0) if url_match else f"https://news.ycombinator.com/item?id={comment_id}"

        job_id = hashlib.sha256(f"hn|{company_name}|{comment_id}".encode()).hexdigest()

        return Job(
            id=job_id,
            company_name=company_name,
            role_title=first_line[:120],
            role_title_normalized=first_line[:120].lower(),
            is_ai_eng=True,
            country=country,
            city=city,
            remote=None,
            posted_at=None,
            url=url,
            source="hn_hiring",
            fetched_at=now,
            notes=text[:300],
        )
