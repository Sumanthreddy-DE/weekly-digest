from __future__ import annotations

import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

from discovery.models import Company, SourceRef
from discovery.ollama_extractor import extract_companies
from discovery.sources.base import SourceBase


class TechEUSource(SourceBase):
    name = "tech_eu"
    geo_tier = "EU"
    extractor = "custom-tech-eu"
    BASE_URL = "https://tech.eu/"
    USER_AGENT = "Mozilla/5.0 (compatible; ai-eng-tracker/0.1)"

    def iter_pages(self, start_page: int):
        max_pages = self.config["discovery"]["sources"].get("tech_eu", {}).get("max_pages", 5)
        for page_num in range(start_page, max_pages + 1):
            url = self.BASE_URL if page_num == 1 else f"{self.BASE_URL}page/{page_num}/"
            response = requests.get(url, timeout=30, headers={"User-Agent": self.USER_AGENT})
            response.raise_for_status()
            companies = self.parse_index_page(response.text, url)
            if not companies:
                return
            yield page_num, url, companies
            time.sleep(self.delay_seconds)

    def parse_index_page(self, html: str, source_url: str) -> list[Company]:
        soup = BeautifulSoup(html, "lxml")
        articles = soup.select("article")
        now = datetime.now(timezone.utc).isoformat()
        companies = []

        for article in articles:
            title_node = article.select_one("h2, h3")
            if not title_node:
                continue
            title = title_node.get_text(" ", strip=True)
            summary_node = article.select_one("p")
            summary = summary_node.get_text(" ", strip=True) if summary_node else ""
            text = f"{title}. {summary}"

            extracted = extract_companies(text, self.config)
            if extracted:
                for item in extracted:
                    companies.append(
                        Company(
                            name=item.get("name") or title,
                            homepage=item.get("homepage"),
                            country=item.get("country"),
                            city=item.get("city"),
                            geo_tier="DE" if item.get("country") == "DE" else "EU",
                            sectors=item.get("sectors") or [],
                            ai_focus=item.get("ai_focus") or summary,
                            stage=None,
                            size=None,
                            sources=[SourceRef(url=source_url, fetched_at=now, extractor="llm-ollama")],
                            last_seen_at=now,
                            notes=None,
                        )
                    )
                continue

            inferred = self._infer_from_text(title, summary, source_url, now)
            if inferred:
                companies.append(inferred)

        return companies

    def _infer_from_text(self, title: str, summary: str, source_url: str, now: str) -> Company | None:
        text = f"{title} {summary}".lower()
        if not any(keyword in text for keyword in ["ai", "simulation", "engineering", "manufacturing", "digital twin"]):
            return None
        return Company(
            name=title,
            homepage=None,
            country=None,
            city=None,
            geo_tier="EU",
            sectors=self._infer_sectors(text),
            ai_focus=summary or title,
            stage=None,
            size=None,
            sources=[SourceRef(url=source_url, fetched_at=now, extractor=self.extractor)],
            last_seen_at=now,
            notes="inferred from Tech.eu index entry",
        )

    @staticmethod
    def _infer_sectors(text: str) -> list[str]:
        sector_map = {
            "ai_engineering": ["engineering", "simulation"],
            "manufacturing_ai": ["manufacturing", "industrial"],
            "digital_twin": ["digital twin"],
            "aerospace": ["aerospace"],
            "composite_materials": ["materials", "composite"],
        }
        matches = []
        for sector, keywords in sector_map.items():
            if any(keyword in text for keyword in keywords):
                matches.append(sector)
        return matches or ["ai_engineering"]
