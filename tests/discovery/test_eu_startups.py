from discovery.checkpoint import Checkpoint, write_checkpoint
from discovery.sources.eu_startups import EUStartupsSource


HTML_WITH_CARDS = """
<html><body>
  <div class="directory-listing-item">
    <h2 class="company-name">Alpha Mechanics</h2>
    <a class="website-link" href="https://alpha.example">Website</a>
    <div class="country">Germany</div>
    <div class="description">AI for engineering and CFD workflows</div>
    <span class="sector-tag">Simulation</span>
    <span class="sector-tag">CAE</span>
  </div>
  <div class="directory-listing-item">
    <h2 class="company-name">Beta Composites</h2>
    <a class="website-link" href="https://beta.example">Website</a>
    <div class="country">France</div>
    <div class="description">Composites and structural mechanics tooling</div>
    <span class="sector-tag">Composites</span>
  </div>
</body></html>
"""

HTML_NO_CARDS = "<html><body><p>nothing here</p></body></html>"


class DummyResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        return None


def _config(tmp_path):
    return {
        "discovery": {
            "checkpoint_dir": str(tmp_path),
            "rss_delay_seconds": 0,
            "sources": {"eu_startups": {"enabled": True, "max_pages": 5}},
        }
    }


def test_parse_listing_page(tmp_path):
    source = EUStartupsSource(_config(tmp_path))
    companies = source.parse_page(HTML_WITH_CARDS, "https://example.com/page1")
    assert len(companies) == 2
    assert companies[0].name == "Alpha Mechanics"
    assert companies[0].homepage == "https://alpha.example"


def test_iso_country_mapping(tmp_path):
    source = EUStartupsSource(_config(tmp_path))
    assert source._iso_country("Germany") == "DE"
    assert source._iso_country("France") == "FR"
    assert source._iso_country("Unknownland") is None


def test_pagination_stops_when_no_cards(tmp_path, monkeypatch):
    source = EUStartupsSource(_config(tmp_path))

    def fake_get(url, timeout, headers):
        return DummyResponse(HTML_NO_CARDS)

    monkeypatch.setattr("discovery.sources.eu_startups.requests.get", fake_get)
    pages = list(source.iter_pages(1))
    assert pages == []


def test_checkpoint_resume(tmp_path, monkeypatch):
    cfg = _config(tmp_path)
    source = EUStartupsSource(cfg)
    write_checkpoint(
        str(tmp_path),
        Checkpoint(
            source="eu_startups",
            started_at="2026-04-29T12:00:00Z",
            last_completed_page=3,
            last_completed_url="https://example.com/page3",
            items_emitted=6,
            status="in_progress",
        ),
    )

    called_urls = []

    def fake_get(url, timeout, headers):
        called_urls.append(url)
        if url.endswith("_page=4"):
            return DummyResponse(HTML_WITH_CARDS)
        return DummyResponse(HTML_NO_CARDS)

    monkeypatch.setattr("discovery.sources.eu_startups.requests.get", fake_get)
    companies = list(source.run())
    assert companies
    assert called_urls[0].endswith("_page=4")
