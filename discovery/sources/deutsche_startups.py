from __future__ import annotations

import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

from discovery.models import Company, SourceRef
from discovery.sources.base import SourceBase


class DeutscheStartupsSource(SourceBase):
    name = "deutsche_startups"
    geo_tier = "DE"
    extractor = "custom-deutsche-startups"
    BASE_URL = "https://www.deutsche-startups.de/startups/"
    USER_AGENT = "Mozilla/5.0 (compatible; ai-eng-tracker/0.1)"

    def iter_pages(self, start_page: int):
        max_pages = self.config["discovery"]["sources"]["deutsche_startups"]["max_pages"]
        for page_num in range(start_page, max_pages + 1):
            url = f"{self.BASE_URL}?paged={page_num}"
            response = requests.get(url, timeout=30, headers={"User-Agent": self.USER_AGENT})
            response.raise_for_status()
            companies = self.parse_page(response.text, url)
            if not companies:
                return
            yield page_num, url, companies
            time.sleep(self.delay_seconds)

    def parse_page(self, html: str, source_url: str) -> list[Company]:
        soup = BeautifulSoup(html, "lxml")
        cards = soup.select("article") or soup.select(".post")
        companies = []
        now = datetime.now(timezone.utc).isoformat()

        for card in cards:
            name_node = card.select_one("h2, h3")
            if not name_node:
                continue
            name = name_node.get_text(" ", strip=True)
            if not name:
                continue

            body_text = card.get_text(" ", strip=True)
            sectors = self._infer_sectors(body_text)
            if not sectors:
                continue

            link = card.select_one("a[href]")
            homepage = link.get("href") if link else None
            description_parts = [p.get_text(" ", strip=True) for p in card.select("p")]
            description = " ".join(part for part in description_parts if part) or body_text

            companies.append(
                Company(
                    name=name,
                    homepage=homepage,
                    country="DE",
                    city=None,
                    geo_tier="DE",
                    sectors=sectors,
                    ai_focus=description,
                    stage=None,
                    size=None,
                    sources=[SourceRef(url=source_url, fetched_at=now, extractor=self.extractor)],
                    last_seen_at=now,
                    notes=None,
                )
            )
        return companies

    @staticmethod
    def _infer_sectors(text: str) -> list[str]:
        lowered = text.lower()
        sector_map = {
            "manufacturing_ai": ["industrie", "maschinenbau", "manufacturing", "industrial"],
            "ai_engineering": ["engineering", "simulation", "ki", "ai"],
            "composite_materials": ["material", "composite", "verbund"],
            "aerospace": ["luftfahrt", "aerospace"],
            "structural_mechanics": ["struktur", "mechanik"],
        }
        matches = []
        for sector, keywords in sector_map.items():
            if any(keyword in lowered for keyword in keywords):
                matches.append(sector)
        return matches
