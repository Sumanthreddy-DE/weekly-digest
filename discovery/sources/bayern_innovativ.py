from __future__ import annotations

from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

from discovery.models import Company, SourceRef
from discovery.sources.base import SourceBase


class BayernInnovativSource(SourceBase):
    name = "bayern_innovativ"
    geo_tier = "DE"
    extractor = "custom-bayern"
    URL = "https://www.bayern-innovativ.de/de/netzwerke-und-thinknet"
    USER_AGENT = "Mozilla/5.0 (compatible; ai-eng-tracker/0.1)"

    def iter_pages(self, start_page: int):
        if start_page > 1:
            return iter(())

        response = requests.get(self.URL, timeout=30, headers={"User-Agent": self.USER_AGENT})
        response.raise_for_status()
        companies = self.parse_page(response.text, self.URL)
        if not companies:
            return
        yield 1, self.URL, companies

    def parse_page(self, html: str, source_url: str) -> list[Company]:
        soup = BeautifulSoup(html, "lxml")
        cards = soup.select("article") or soup.select(".teaser") or soup.select(".list-item")
        companies = []
        now = datetime.now(timezone.utc).isoformat()

        for card in cards:
            title_node = card.select_one("h2, h3, h4")
            if not title_node:
                continue
            name = title_node.get_text(" ", strip=True)
            if not name:
                continue

            text = card.get_text(" ", strip=True)
            sectors = self._infer_sectors(text)
            if not sectors:
                continue

            link = card.select_one("a[href]")
            homepage = link.get("href") if link else None
            desc_parts = [node.get_text(" ", strip=True) for node in card.select("p")]
            ai_focus = " ".join(part for part in desc_parts if part) or text

            companies.append(
                Company(
                    name=name,
                    homepage=homepage,
                    country="DE",
                    city="Bavaria",
                    geo_tier="DE",
                    sectors=sectors,
                    ai_focus=ai_focus,
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
            "manufacturing_ai": ["produktion", "fertigung", "manufacturing", "industrial"],
            "ai_engineering": ["engineering", "simulation", "konstruktion", "entwicklung"],
            "aerospace": ["luft", "raumfahrt", "aerospace"],
            "composite_materials": ["leichtbau", "composite", "verbund", "material"],
            "digital_twin": ["digital twin", "digitaler zwilling"],
            "structural_mechanics": ["mechanik", "struktur", "fem", "fea"],
        }
        matches = []
        for sector, keywords in sector_map.items():
            if any(keyword in lowered for keyword in keywords):
                matches.append(sector)
        return matches
