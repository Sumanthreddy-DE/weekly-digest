from discovery.sources.ai_made_in_germany import AIMadeInGermanySource


HTML = """
<html><body>
  <article>
    <h3>IngenieurKI GmbH</h3>
    <a href="https://ingenieurki.example">Visit</a>
    <p>KI für Konstruktion, FEM und digitaler Zwilling in der Fertigung.</p>
  </article>
  <article>
    <h3>Consumer Fun App</h3>
    <a href="https://fun.example">Visit</a>
    <p>Photo sharing app for consumers.</p>
  </article>
</body></html>
"""


def _config(tmp_path):
    return {
        "discovery": {
            "checkpoint_dir": str(tmp_path),
            "rss_delay_seconds": 0,
            "sources": {"ai_made_in_germany": {"enabled": True, "max_pages": 3}},
        }
    }


def test_parse_page_filters_relevant_entries(tmp_path):
    source = AIMadeInGermanySource(_config(tmp_path))
    companies = source.parse_page(HTML, "https://example.com")
    assert len(companies) == 1
    assert companies[0].name == "IngenieurKI GmbH"
    assert companies[0].country == "DE"


def test_infer_sectors(tmp_path):
    source = AIMadeInGermanySource(_config(tmp_path))
    sectors = source._infer_sectors("digitaler Zwilling und FEM für Konstruktion in der Fertigung")
    assert "digital_twin" in sectors
    assert "structural_mechanics" in sectors
    assert "manufacturing_ai" in sectors
