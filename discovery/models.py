from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal, Optional

GeoTier = Literal["DE", "EU", "GLOBAL"]
VALID_GEO_TIERS = {"DE", "EU", "GLOBAL"}

SourceExtractor = Literal[
    "custom-eu-startups",
    "custom-yc",
    "custom-berlin-ai",
    "custom-bayern",
    "custom-deutsche-startups",
    "custom-plug-and-play",
    "custom-ai-made-de",
    "custom-tech-eu",
    "llm-ollama",
    "llm-failed",
    "google-news-en",
    "google-news-de",
]


@dataclass
class SourceRef:
    url: str
    fetched_at: str
    extractor: SourceExtractor


@dataclass
class Company:
    name: str
    homepage: Optional[str]
    country: Optional[str]
    city: Optional[str]
    geo_tier: GeoTier
    sectors: list[str]
    ai_focus: str
    stage: Optional[str]
    size: Optional[str]
    sources: list[SourceRef]
    last_seen_at: str
    notes: Optional[str] = None

    def __post_init__(self) -> None:
        if self.geo_tier not in VALID_GEO_TIERS:
            raise ValueError(f"Invalid geo_tier: {self.geo_tier}")

    def to_json(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_json(data: dict) -> "Company":
        payload = dict(data)
        payload["sources"] = [SourceRef(**item) for item in payload.get("sources", [])]
        return Company(**payload)
