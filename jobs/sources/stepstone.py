from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from jobs.models import Job
from jobs.sources.base import JobSourceBase

log = logging.getLogger(__name__)


class StepStoneSource(JobSourceBase):
    USER_AGENT = "Mozilla/5.0 (compatible; ai-eng-tracker/0.1)"
    DEFAULT_SEARCH_URL = "https://www.stepstone.de/jobs/?ke=machine+learning&ws=Deutschland"

    def run(self):
        search_url = self.config.get("jobs", {}).get("sources", {}).get("stepstone", {}).get("search_url", self.DEFAULT_SEARCH_URL)
        try:
            response = requests.get(search_url, timeout=30, headers={"User-Agent": self.USER_AGENT})
            response.raise_for_status()
            return self.parse_jobs_page(response.text, search_url)
        except Exception as exc:
            log.warning("StepStone fetch failed: %s", exc)
            return []

    def parse_jobs_page(self, html: str, source_url: str) -> list[Job]:
        soup = BeautifulSoup(html, "lxml")
        cards = soup.select("article") or soup.select(".job-listing") or soup.select(".result")
        jobs = []
        now = datetime.now(timezone.utc).isoformat()

        for card in cards:
            title_node = card.select_one("h2, h3, a")
            if not title_node:
                continue
            title = title_node.get_text(" ", strip=True)
            if not title or not self._looks_like_ai_eng(title):
                continue
            link = card.select_one("a[href]")
            job_url = urljoin(source_url, link.get("href")) if link else source_url
            location_node = card.select_one(".location, .job-location")
            location = location_node.get_text(" ", strip=True) if location_node else "Germany"
            country = "DE" if "germany" in location.lower() or "berlin" in location.lower() or "munich" in location.lower() else None
            job_id = hashlib.sha256(f"stepstone|{title}|{job_url}".encode()).hexdigest()
            jobs.append(
                Job(
                    id=job_id,
                    company_name="Unknown",
                    role_title=title,
                    role_title_normalized=title.lower(),
                    is_ai_eng=True,
                    country=country,
                    city=None,
                    remote=None,
                    posted_at=None,
                    url=job_url,
                    source="stepstone",
                    fetched_at=now,
                    notes=f"Parsed from StepStone listing at {source_url}",
                )
            )
        return jobs

    @staticmethod
    def _looks_like_ai_eng(title: str) -> bool:
        lowered = title.lower()
        keywords = ["ai", "machine learning", "ml engineer", "simulation", "computational", "data scientist"]
        return any(keyword in lowered for keyword in keywords)
