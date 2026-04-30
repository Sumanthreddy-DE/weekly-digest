from __future__ import annotations

from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

from discovery.models import Company, SourceRef
from discovery.sources.base import SourceBase


class PlugAndPlayMunichSource(SourceBase):
    name = "plug_and_play_munich"
    geo_tier = "DE"
    extractor = "custom-plug-and-play"
    URL = "https://www.plugandplaytechcenter.com/munich/"
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
        cards = soup.select("article") or soup.select(".portfolio-item") or soup.select(".company-card")
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
                    city="Munich",
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
            "manufacturing_ai": ["manufacturing", "industrial", "factory", "mobility"],
            "ai_engineering": ["engineering", "simulation", "design", "cad", "cae"],
            "aerospace": ["aerospace", "aviation"],
            "digital_twin": ["digital twin"],
            "composite_materials": ["materials", "composite"],
        }
        matches = []
        for sector, keywords in sector_map.items():
            if any(keyword in lowered for keyword in keywords):
                matches.append(sector)
        return matches
