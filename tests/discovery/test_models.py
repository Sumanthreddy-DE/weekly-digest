import pytest

from discovery.models import Company, SourceRef


def test_company_to_from_json_roundtrip():
    company = Company(
        name="Example GmbH",
        homepage="https://example.com",
        country="DE",
        city="Berlin",
        geo_tier="DE",
        sectors=["composite_materials", "structural_mechanics"],
        ai_focus="Builds AI for structural simulation.",
        stage="seed",
        size="11-50",
        sources=[SourceRef(url="https://source.test", fetched_at="2026-04-29T12:00:00Z", extractor="custom-eu-startups")],
        last_seen_at="2026-04-29T12:00:00Z",
        notes="reviewed",
    )

    loaded = Company.from_json(company.to_json())
    assert loaded == company


def test_company_rejects_invalid_geo_tier():
    with pytest.raises(ValueError):
        Company(
            name="Bad Co",
            homepage=None,
            country=None,
            city=None,
            geo_tier="INVALID",
            sectors=[],
            ai_focus="",
            stage=None,
            size=None,
            sources=[],
            last_seen_at="2026-04-29T12:00:00Z",
        )
