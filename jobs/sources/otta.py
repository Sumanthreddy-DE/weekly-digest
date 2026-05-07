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


class OttaSource(JobSourceBase):
    USER_AGENT = "Mozilla/5.0 (compatible; ai-eng-tracker/0.1)"
    DEFAULT_SEARCH_URL = "https://otta.com/jobs?q=machine+learning&l=berlin"

    def run(self):
        search_url = self.config.get("jobs", {}).get("sources", {}).get("otta", {}).get("search_url", self.DEFAULT_SEARCH_URL)
        try:
            response = requests.get(search_url, timeout=30, headers={"User-Agent": self.USER_AGENT})
            response.raise_for_status()
            return self.parse_jobs_page(response.text, search_url)
        except Exception as exc:
            log.warning("Otta fetch failed: %s", exc)
            return []

    def parse_jobs_page(self, html: str, source_url: str) -> list[Job]:
        soup = BeautifulSoup(html, "lxml")
        cards = soup.select("article") or soup.select(".job-tile") or soup.select(".styles_jobCard__")
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
            company_node = card.select_one(".company, .company-name")
            company_name = company_node.get_text(" ", strip=True) if company_node else "Unknown"
            location_node = card.select_one(".location")
            location = location_node.get_text(" ", strip=True) if location_node else ""
            country = "DE" if "germany" in location.lower() or "berlin" in location.lower() else None
            job_id = hashlib.sha256(f"otta|{company_name}|{title}|{job_url}".encode()).hexdigest()
            jobs.append(
                Job(
                    id=job_id,
                    company_name=company_name,
                    role_title=title,
                    role_title_normalized=title.lower(),
                    is_ai_eng=True,
                    country=country,
                    city=None,
                    remote=None,
                    posted_at=None,
                    url=job_url,
                    source="otta",
                    fetched_at=now,
                    notes=f"Parsed from Otta listing at {source_url}",
                )
            )
        return jobs

    @staticmethod
    def _looks_like_ai_eng(title: str) -> bool:
        lowered = title.lower()
        keywords = ["ai", "machine learning", "ml engineer", "ml ", "simulation", "computational", "data scientist"]
        return any(keyword in lowered for keyword in keywords)
