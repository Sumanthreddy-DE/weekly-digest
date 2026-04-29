from discovery.sources.berlin_ai_map import BerlinAIMapSource


HTML = """
<html><body>
  <article>
    <h3>Meridian AI</h3>
    <a href="https://meridian.example">Visit</a>
    <p>Builds simulation tooling and digital twin software for industrial design.</p>
  </article>
  <article>
    <h3>FactoryMind</h3>
    <a href="https://factorymind.example">Visit</a>
    <p>Manufacturing AI for robotics and factory planning.</p>
  </article>
</body></html>
"""


def _config(tmp_path):
    return {
        "discovery": {
            "checkpoint_dir": str(tmp_path),
            "rss_delay_seconds": 0,
            "sources": {"berlin_ai_map": {"enabled": True}},
        }
    }


def test_parse_page(tmp_path):
    source = BerlinAIMapSource(_config(tmp_path))
    companies = source.parse_page(HTML)
    assert len(companies) == 2
    assert companies[0].name == "Meridian AI"
    assert companies[0].country == "DE"
    assert companies[0].city == "Berlin"


def test_infer_sectors(tmp_path):
    source = BerlinAIMapSource(_config(tmp_path))
    sectors = source._infer_sectors("digital twin and simulation for manufacturing")
    assert "digital_twin" in sectors
    assert "ai_cae" in sectors
