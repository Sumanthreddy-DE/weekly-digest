from __future__ import annotations

from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

from discovery.models import Company, SourceRef
from discovery.sources.base import SourceBase


class BerlinAIMapSource(SourceBase):
    name = "berlin_ai_map"
    geo_tier = "DE"
    extractor = "custom-berlin-ai"
    URL = "https://merantix.com/companies/berlin-ai-map/"
    USER_AGENT = "Mozilla/5.0 (compatible; ai-eng-tracker/0.1)"

    def iter_pages(self, start_page: int):
        if start_page > 1:
            return iter(())

        response = requests.get(self.URL, timeout=30, headers={"User-Agent": self.USER_AGENT})
        response.raise_for_status()
        companies = self.parse_page(response.text)
        if not companies:
            return
        yield 1, self.URL, companies

    def parse_page(self, html: str) -> list[Company]:
        soup = BeautifulSoup(html, "lxml")
        cards = soup.select("article") or soup.select(".elementor-widget-wrap > div")
        companies = []
        now = datetime.now(timezone.utc).isoformat()

        for card in cards:
            text = card.get_text(" ", strip=True)
            if not text:
                continue

            link = card.select_one("a[href]")
            title = card.select_one("h2, h3, h4")
            name = title.get_text(" ", strip=True) if title else None
            if not name or len(name) < 2:
                continue

            homepage = link.get("href") if link else None
            description_parts = [p.get_text(" ", strip=True) for p in card.select("p")]
            description = " ".join(part for part in description_parts if part)
            sectors = self._infer_sectors(text)

            companies.append(
                Company(
                    name=name,
                    homepage=homepage,
                    country="DE",
                    city="Berlin",
                    geo_tier="DE",
                    sectors=sectors,
                    ai_focus=description or text,
                    stage=None,
                    size=None,
                    sources=[SourceRef(url=self.URL, fetched_at=now, extractor=self.extractor)],
                    last_seen_at=now,
                    notes=None,
                )
            )
        return companies

    @staticmethod
    def _infer_sectors(text: str) -> list[str]:
        lowered = text.lower()
        sector_map = {
            "ai_cae": ["simulation", "engineering", "design"],
            "digital_twin": ["digital twin"],
            "manufacturing_ai": ["manufacturing", "factory", "industrial"],
            "composite_materials": ["materials", "composite"],
        }
        matches = []
        for sector, keywords in sector_map.items():
            if any(keyword in lowered for keyword in keywords):
                matches.append(sector)
        return matches or ["ai_engineering"]
