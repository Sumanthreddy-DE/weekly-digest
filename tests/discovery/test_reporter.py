from discovery.models import Company, SourceRef
from discovery.reporter import write_reports


def _company(name, geo_tier, country):
    return Company(
        name=name,
        homepage=f"https://{name.lower()}.com",
        country=country,
        city="Berlin",
        geo_tier=geo_tier,
        sectors=["ai_cae"],
        ai_focus="Builds AI for engineering.",
        stage=None,
        size=None,
        sources=[SourceRef(url="https://source.test", fetched_at="2026-04-29T12:00:00Z", extractor="custom-eu-startups")],
        last_seen_at="2026-04-29T12:00:00Z",
    )


def test_write_reports_creates_three_files(tmp_path):
    write_reports([
        _company("DECo", "DE", "DE"),
        _company("EUCo", "EU", "FR"),
        _company("GlobalCo", "GLOBAL", "US"),
    ], str(tmp_path))
    assert (tmp_path / "01-germany.md").exists()
    assert (tmp_path / "02-european-union.md").exists()
    assert (tmp_path / "03-global.md").exists()


def test_de_deep_format(tmp_path):
    write_reports([_company("DECo", "DE", "DE")], str(tmp_path))
    text = (tmp_path / "01-germany.md").read_text()
    assert "## DECo" in text
    assert "- **Homepage**: https://deco.com" in text


def test_eu_scan_table_header(tmp_path):
    write_reports([_company("EUCo", "EU", "FR")], str(tmp_path))
    text = (tmp_path / "02-european-union.md").read_text()
    assert "| Name | Country | Sectors | Homepage | Source |" in text


def test_global_ref_bullet_format(tmp_path):
    write_reports([_company("GlobalCo", "GLOBAL", "US")], str(tmp_path))
    lines = (tmp_path / "03-global.md").read_text().splitlines()
    assert any(line.startswith("- **GlobalCo**") for line in lines)
