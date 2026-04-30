from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from jobs.models import Job
from jobs.sources.base import JobSourceBase


class CareersPageSource(JobSourceBase):
    CAREER_PATHS = ["/careers", "/jobs", "/karriere"]
    USER_AGENT = "Mozilla/5.0 (compatible; ai-eng-tracker/0.1)"

    def __init__(self, config: dict, companies: list[dict]):
        super().__init__(config)
        self.companies = companies

    def run(self):
        jobs = []
        for company in self.companies:
            homepage = company.get("homepage")
            if not homepage:
                continue
            for path in self.CAREER_PATHS:
                url = urljoin(homepage.rstrip("/") + "/", path.lstrip("/"))
                try:
                    response = requests.get(url, timeout=20, headers={"User-Agent": self.USER_AGENT})
                    if response.status_code >= 400:
                        continue
                    parsed = self.parse_jobs_page(response.text, company, url)
                    if parsed:
                        jobs.extend(parsed)
                        break
                except Exception:
                    continue
        return jobs

    def parse_jobs_page(self, html: str, company: dict, source_url: str) -> list[Job]:
        soup = BeautifulSoup(html, "lxml")
        links = soup.select("a[href]")
        jobs = []
        now = datetime.now(timezone.utc).isoformat()

        for link in links:
            text = link.get_text(" ", strip=True)
            if not text:
                continue
            if not self._looks_like_job(text):
                continue
            job_url = urljoin(source_url, link.get("href"))
            job_id = hashlib.sha256(f"{company.get('name')}|{text}|{job_url}".encode()).hexdigest()
            jobs.append(
                Job(
                    id=job_id,
                    company_name=company.get("name", "Unknown"),
                    role_title=text,
                    role_title_normalized=text.lower(),
                    is_ai_eng=True,
                    country=company.get("country"),
                    city=company.get("city"),
                    remote=None,
                    posted_at=None,
                    url=job_url,
                    source="careers-page",
                    fetched_at=now,
                    notes=f"Extracted from careers page: {source_url}",
                )
            )
        return jobs

    @staticmethod
    def _looks_like_job(text: str) -> bool:
        lowered = text.lower()
        keywords = [
            "engineer",
            "engineering",
            "machine learning",
            "ml",
            "ai",
            "simulation",
            "data scientist",
            "research engineer",
            "computational",
        ]
        return any(keyword in lowered for keyword in keywords)
