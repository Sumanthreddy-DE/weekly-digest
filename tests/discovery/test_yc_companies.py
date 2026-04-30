from discovery.sources.yc_companies import YCCompaniesSource


HTML = """
<html><body>
  <a href="/companies/simcad-ai">
    SimCAD AI
    Industrial simulation and CAD copilot for manufacturing teams
  </a>
  <a href="/companies/social-buzz">
    Social Buzz
    Social media tool for creators
  </a>
</body></html>
"""


def _config(tmp_path):
    return {
        "discovery": {
            "checkpoint_dir": str(tmp_path),
            "rss_delay_seconds": 0,
            "sources": {"yc_companies": {"enabled": True}},
        }
    }


def test_parse_page_filters_relevant_entries(tmp_path):
    source = YCCompaniesSource(_config(tmp_path))
    companies = source.parse_page(HTML, "https://www.ycombinator.com/companies")
    assert len(companies) == 1
    assert companies[0].name.startswith("SimCAD AI")
    assert companies[0].geo_tier == "GLOBAL"


def test_infer_sectors(tmp_path):
    source = YCCompaniesSource(_config(tmp_path))
    sectors = source._infer_sectors("industrial simulation and CAD for manufacturing")
    assert "manufacturing_ai" in sectors
    assert "ai_engineering" in sectors
