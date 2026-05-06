import json

from discovery.run import main


HTML_WITH_CARD = """
<html><body>
  <div class="directory-listing-item">
    <h2 class="company-name">Alpha Mechanics</h2>
    <a class="website-link" href="https://alpha.example">Website</a>
    <div class="country">Germany</div>
    <div class="description">AI for engineering and CFD workflows</div>
    <span class="sector-tag">Simulation</span>
  </div>
</body></html>
"""

HTML_NO_CARDS = "<html><body></body></html>"


class DummyResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        return None


def test_run_smoke(tmp_path, monkeypatch):
    config_path = tmp_path / "config.yaml"
    cp_dir = (tmp_path / 'checkpoints').as_posix()
    out_dir = (tmp_path / 'reports').as_posix()
    comp_file = (tmp_path / 'companies.json').as_posix()
    jobs_file = (tmp_path / 'jobs.json').as_posix()
    jobs_md = (tmp_path / 'jobs.md').as_posix()
    config_path.write_text(
        f"""
openclaw:
  base_url: http://localhost:11434
  model: qwen3:8b

discovery:
  enable_hard_sources: false
  max_companies_total: 10
  rss_delay_seconds: 0
  per_source_timeout_seconds: 1800
  checkpoint_dir: {cp_dir}
  output_dir: {out_dir}
  companies_file: {comp_file}
  ollama_extractor:
    model: qwen3:8b
    format: json
    timeout_seconds: 90
    max_retries: 1
  sources:
    eu_startups: {{ enabled: true, max_pages: 2 }}

jobs:
  enabled: true
  output_file: {jobs_file}
  report_file: {jobs_md}
  geo_filter: [DE]
  sources:
    careers_pages: {{ enabled: true }}
"""
    )

    calls = {"count": 0}

    def fake_get(url, timeout, headers):
        calls["count"] += 1
        if calls["count"] == 1:
            return DummyResponse(HTML_WITH_CARD)
        return DummyResponse(HTML_NO_CARDS)

    monkeypatch.setattr("discovery.sources.eu_startups.requests.get", fake_get)
    assert main([str(config_path)]) == 0

    companies = json.loads((tmp_path / "companies.json").read_text())
    assert len(companies) == 1
    assert (tmp_path / "reports" / "01-germany.md").exists()
