from discovery.sources.bayern_innovativ import BayernInnovativSource


HTML = """
<html><body>
  <article>
    <h3>Leichtbau Dynamics</h3>
    <a href="https://leichtbau.example">Visit</a>
    <p>Simulation, Leichtbau and digitaler Zwilling for industrielle Fertigung.</p>
  </article>
  <article>
    <h3>Retail Portal</h3>
    <a href="https://retail.example">Visit</a>
    <p>Online marketplace for fashion.</p>
  </article>
</body></html>
"""


def _config(tmp_path):
    return {
        "discovery": {
            "checkpoint_dir": str(tmp_path),
            "rss_delay_seconds": 0,
            "sources": {"bayern_innovativ": {"enabled": True}},
        }
    }


def test_parse_page_filters_relevant_entries(tmp_path):
    source = BayernInnovativSource(_config(tmp_path))
    companies = source.parse_page(HTML, "https://example.com")
    assert len(companies) == 1
    assert companies[0].name == "Leichtbau Dynamics"
    assert companies[0].city == "Bavaria"


def test_infer_sectors(tmp_path):
    source = BayernInnovativSource(_config(tmp_path))
    sectors = source._infer_sectors("Leichtbau simulation and digitaler Zwilling for industrielle Fertigung")
    assert "composite_materials" in sectors
    assert "digital_twin" in sectors
    assert "manufacturing_ai" in sectors
