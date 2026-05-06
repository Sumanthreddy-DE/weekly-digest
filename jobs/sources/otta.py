from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from jobs.models import Job
from jobs.sources.base import JobSourceBase


class OttaSource(JobSourceBase):
    def run(self):
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
