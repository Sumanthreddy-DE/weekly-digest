from discovery.sources.tech_eu import TechEUSource


HTML = """
<html><body>
  <article>
    <h2>SimForge raises funding for AI engineering platform</h2>
    <p>European startup building simulation and digital twin tools for manufacturers.</p>
  </article>
  <article>
    <h2>Travel app launches rewards card</h2>
    <p>Consumer fintech story.</p>
  </article>
</body></html>
"""


def _config(tmp_path):
    return {
        "openclaw": {"base_url": "http://localhost:11434"},
        "discovery": {
            "checkpoint_dir": str(tmp_path),
            "rss_delay_seconds": 0,
            "sources": {"tech_eu": {"enabled": True, "max_pages": 3}},
            "ollama_extractor": {"model": "qwen3:8b", "timeout_seconds": 90, "max_retries": 1},
        },
    }


def test_parse_index_page_with_fallback_inference(tmp_path, monkeypatch):
    source = TechEUSource(_config(tmp_path))
    monkeypatch.setattr("discovery.sources.tech_eu.extract_companies", lambda text, config: [])
    companies = source.parse_index_page(HTML, "https://tech.eu")
    assert len(companies) == 1
    assert companies[0].notes == "inferred from Tech.eu index entry"


def test_parse_index_page_with_llm_extract(tmp_path, monkeypatch):
    source = TechEUSource(_config(tmp_path))
    monkeypatch.setattr(
        "discovery.sources.tech_eu.extract_companies",
        lambda text, config: [
            {
                "name": "SimForge",
                "homepage": "https://simforge.example",
                "country": "DE",
                "city": "Berlin",
                "ai_focus": "AI for simulation",
                "sectors": ["ai_engineering"],
            }
        ]
        if "SimForge" in text
        else [],
    )
    companies = source.parse_index_page(HTML, "https://tech.eu")
    assert len(companies) == 1
    assert companies[0].name == "SimForge"
    assert companies[0].country == "DE"


def test_infer_sectors(tmp_path):
    source = TechEUSource(_config(tmp_path))
    sectors = source._infer_sectors("simulation digital twin manufacturing")
    assert "ai_engineering" in sectors
    assert "digital_twin" in sectors
    assert "manufacturing_ai" in sectors
