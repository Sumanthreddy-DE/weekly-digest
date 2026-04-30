from discovery.sources.plug_and_play_munich import PlugAndPlayMunichSource


HTML = """
<html><body>
  <article>
    <h3>MobilitySim</h3>
    <a href="https://mobilitysim.example">Visit</a>
    <p>Simulation and digital twin platform for mobility manufacturing.</p>
  </article>
  <article>
    <h3>Generic SaaS</h3>
    <a href="https://saas.example">Visit</a>
    <p>CRM for small businesses.</p>
  </article>
</body></html>
"""


def _config(tmp_path):
    return {
        "discovery": {
            "checkpoint_dir": str(tmp_path),
            "rss_delay_seconds": 0,
            "sources": {"plug_and_play_munich": {"enabled": True}},
        }
    }


def test_parse_page_filters_relevant_entries(tmp_path):
    source = PlugAndPlayMunichSource(_config(tmp_path))
    companies = source.parse_page(HTML, "https://example.com")
    assert len(companies) == 1
    assert companies[0].name == "MobilitySim"
    assert companies[0].city == "Munich"


def test_infer_sectors(tmp_path):
    source = PlugAndPlayMunichSource(_config(tmp_path))
    sectors = source._infer_sectors("simulation and digital twin for mobility manufacturing")
    assert "ai_engineering" in sectors
    assert "digital_twin" in sectors
    assert "manufacturing_ai" in sectors
