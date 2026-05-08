from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

from discovery.models import Company, SourceRef
from discovery.sources.base import SourceBase

log = logging.getLogger(__name__)

COUNTRY_MAP = {
    "germany": "DE",
    "france": "FR",
    "spain": "ES",
    "italy": "IT",
    "netherlands": "NL",
    "belgium": "BE",
    "austria": "AT",
    "switzerland": "CH",
    "sweden": "SE",
    "denmark": "DK",
    "finland": "FI",
    "norway": "NO",
    "ireland": "IE",
    "portugal": "PT",
    "poland": "PL",
    "czech republic": "CZ",
}


class EUStartupsSource(SourceBase):
    name = "eu_startups"
    geo_tier = "EU"
    extractor = "custom-eu-startups"
    BASE_URL = "https://www.eu-startups.com/directory/"
    USER_AGENT = "Mozilla/5.0 (compatible; ai-eng-tracker/0.1)"

    def iter_pages(self, start_page: int):
        max_pages = self.config["discovery"]["sources"]["eu_startups"]["max_pages"]
        for page_num in range(start_page, max_pages + 1):
            url = f"{self.BASE_URL}?_page={page_num}"
            response = requests.get(url, timeout=30, headers={"User-Agent": self.USER_AGENT})
            response.raise_for_status()
            companies = self.parse_page(response.text, url)
            if not companies:
                return
            yield page_num, url, companies
            time.sleep(self.delay_seconds)

    def parse_page(self, html: str, source_url: str) -> list[Company]:
        soup = BeautifulSoup(html, "lxml")
        cards = soup.select("div.directory-listing-item")
        if not cards:
            cards = soup.select("article")
        companies = []
        now = datetime.now(timezone.utc).isoformat()

        for card in cards:
            name_node = card.select_one(".company-name") or card.select_one("h2") or card.select_one("h3")
            if not name_node:
                continue
            name = name_node.get_text(" ", strip=True)
            homepage_node = card.select_one("a.website-link") or card.select_one("a[href]")
            homepage = homepage_node.get("href") if homepage_node else None
            country_node = card.select_one(".country") or card.select_one("[data-country]")
            country_name = country_node.get_text(" ", strip=True) if country_node else None
            description_node = card.select_one(".description") or card.select_one("p")
            description = description_node.get_text(" ", strip=True) if description_node else ""
            sector_nodes = card.select(".sector-tag, .tag, .elementor-button-text")
            sectors = [node.get_text(" ", strip=True) for node in sector_nodes if node.get_text(" ", strip=True)]

            country_code = self._iso_country(country_name)
            geo_tier = "DE" if country_code == "DE" else "EU"
            companies.append(
                Company(
                    name=name,
                    homepage=homepage,
                    country=country_code,
                    city=None,
                    geo_tier=geo_tier,
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
    def _iso_country(name: str | None) -> str | None:
        if not name:
            return None
        return COUNTRY_MAP.get(name.strip().lower())
