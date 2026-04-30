from __future__ import annotations

import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

from discovery.models import Company, SourceRef
from discovery.sources.base import SourceBase


class YCCompaniesSource(SourceBase):
    name = "yc_companies"
    geo_tier = "GLOBAL"
    extractor = "custom-yc"
    BASE_URL = "https://www.ycombinator.com/companies"
    USER_AGENT = "Mozilla/5.0 (compatible; ai-eng-tracker/0.1)"

    def iter_pages(self, start_page: int):
        if start_page > 1:
            return iter(())
        response = requests.get(self.BASE_URL, timeout=30, headers={"User-Agent": self.USER_AGENT})
        response.raise_for_status()
        companies = self.parse_page(response.text, self.BASE_URL)
        if not companies:
            return
        yield 1, self.BASE_URL, companies
        time.sleep(self.delay_seconds)

    def parse_page(self, html: str, source_url: str) -> list[Company]:
        soup = BeautifulSoup(html, "lxml")
        cards = soup.select("a[href*='/companies/']")
        companies = []
        now = datetime.now(timezone.utc).isoformat()

        for card in cards:
            text = card.get_text(" ", strip=True)
            if not text:
                continue
            sectors = self._infer_sectors(text)
            if not sectors:
                continue

            lines = [part.strip() for part in text.split("\n") if part.strip()]
            name = lines[0] if lines else text[:80]
            homepage = card.get("href")
            if homepage and homepage.startswith("/"):
                homepage = f"https://www.ycombinator.com{homepage}"

            companies.append(
                Company(
                    name=name,
                    homepage=homepage,
                    country=None,
                    city=None,
                    geo_tier="GLOBAL",
                    sectors=sectors,
                    ai_focus=text,
                    stage="yc",
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
            "manufacturing_ai": ["manufacturing", "industrial", "factory"],
            "ai_engineering": ["engineering", "simulation", "design ai", "cad", "cae"],
            "composite_materials": ["materials", "composite"],
            "aerospace": ["aerospace", "space", "aircraft"],
            "digital_twin": ["digital twin"],
        }
        matches = []
        for sector, keywords in sector_map.items():
            if any(keyword in lowered for keyword in keywords):
                matches.append(sector)
        return matches
