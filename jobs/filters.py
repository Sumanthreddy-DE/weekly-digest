from __future__ import annotations

from discovery.filters import evaluate

DE_EU_COUNTRIES = {"DE", "AT", "CH", "NL", "FR", "ES", "IT", "PL", "SE", "DK", "FI", "NO", "BE", "IE", "PT", "CZ"}
ROLE_TITLE_AI_KW = [
    "machine learning",
    "ml engineer",
    "ai engineer",
    "research engineer",
    "computational engineer",
    "simulation engineer",
    "data scientist",
]


def is_ai_eng_role(title: str, desc: str) -> bool:
    title_lower = title.lower()
    if not any(keyword in title_lower for keyword in ROLE_TITLE_AI_KW):
        return False
    result = evaluate(f"{title} {desc}")
    return result.passes_tier1


def is_de_eu(country: str | None) -> bool:
    return country in DE_EU_COUNTRIES if country else False
