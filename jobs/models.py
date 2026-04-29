from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional


@dataclass
class Job:
    id: str
    company_name: str
    role_title: str
    role_title_normalized: str
    is_ai_eng: bool
    country: Optional[str]
    city: Optional[str]
    remote: Optional[bool]
    posted_at: Optional[str]
    url: str
    source: str
    fetched_at: str
    notes: Optional[str] = None

    def to_json(self) -> dict:
        return asdict(self)
