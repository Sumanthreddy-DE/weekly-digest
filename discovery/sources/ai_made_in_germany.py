from __future__ import annotations

import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

from discovery.models import Company, SourceRef
from discovery.sources.base import SourceBase


class AIMadeInGermanySource(SourceBase):
    name = "ai_made_in_germany"
    geo_tier = "DE"
    extractor = "custom-ai-made-de"
    BASE_URL = "https://ai.bundesnetzagentur.de/"
    USER_AGENT = "Mozilla/5.0 (compatible; ai-eng-tracker/0.1)"

    def iter_pages(self, start_page: int):
        max_pages = self.config["discovery"]["sources"].get("ai_made_in_germany", {}).get("max_pages", 5)
        for page_num in range(start_page, max_pages + 1):
            url = self.BASE_URL if page_num == 1 else f"{self.BASE_URL}?page={page_num}"
            response = requests.get(url, timeout=30, headers={"User-Agent": self.USER_AGENT})
            response.raise_for_status()
            companies = self.parse_page(response.text, url)
            if not companies:
                return
            yield page_num, url, companies
            time.sleep(self.delay_seconds)

    def parse_page(self, html: str, source_url: str) -> list[Company]:
        soup = BeautifulSoup(html, "lxml")
        cards = soup.select("article") or soup.select(".card") or soup.select(".entry")
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
                    city=None,
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
            "ai_engineering": ["engineering", "simulation", "konstruktion", "ingenieur"],
            "manufacturing_ai": ["fertigung", "produktion", "manufacturing", "industrial"],
            "digital_twin": ["digital twin", "digitaler zwilling"],
            "structural_mechanics": ["struktur", "mechanik", "fem", "fea"],
            "composite_materials": ["verbund", "composite", "material"],
            "aerospace": ["luftfahrt", "raumfahrt", "aerospace"],
        }
        matches = []
        for sector, keywords in sector_map.items():
            if any(keyword in lowered for keyword in keywords):
                matches.append(sector)
        return matches
