from discovery.sources.deutsche_startups import DeutscheStartupsSource


HTML = """
<html><body>
  <article>
    <h2>Structuro AI</h2>
    <a href="https://structuro.example">Read more</a>
    <p>KI startup for structural mechanics and simulation in Maschinenbau.</p>
  </article>
  <article>
    <h2>Food Delivery App</h2>
    <a href="https://food.example">Read more</a>
    <p>We deliver pizza faster.</p>
  </article>
</body></html>
"""


HTML_NO_MATCH = "<html><body><article><h2>Nothing</h2><p>Just retail</p></article></body></html>"


def _config(tmp_path):
    return {
        "discovery": {
            "checkpoint_dir": str(tmp_path),
            "rss_delay_seconds": 0,
            "sources": {"deutsche_startups": {"enabled": True, "max_pages": 3}},
        }
    }


def test_parse_page_filters_relevant_entries(tmp_path):
    source = DeutscheStartupsSource(_config(tmp_path))
    companies = source.parse_page(HTML, "https://example.com")
    assert len(companies) == 1
    assert companies[0].name == "Structuro AI"
    assert companies[0].country == "DE"


def test_parse_page_returns_empty_when_no_relevant_entries(tmp_path):
    source = DeutscheStartupsSource(_config(tmp_path))
    companies = source.parse_page(HTML_NO_MATCH, "https://example.com")
    assert companies == []


def test_infer_sectors(tmp_path):
    source = DeutscheStartupsSource(_config(tmp_path))
    sectors = source._infer_sectors("KI for structural mechanics in Maschinenbau")
    assert "structural_mechanics" in sectors
    assert "manufacturing_ai" in sectors
