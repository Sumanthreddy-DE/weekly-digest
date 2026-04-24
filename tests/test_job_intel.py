from unittest.mock import patch

from collector.apify_scraper import ApifyFetchError
from collector.job_intel import fetch_job_intel

APIFY_ITEMS = [
    {"url": "https://simscale.com/news/1", "title": "SimScale Munich raises Series B"},
    {"url": "https://cae.fr/2", "title": "French CAE startup hires ML team in Paris"},
    {"url": "https://us-company.com/3", "title": "US digital twin startup closes round"},
]
RSS_ITEMS = [
    {"url": "https://rss.com/1", "title": "FEA news", "summary": "", "source": "rss"},
]


@patch("collector.job_intel.fetch_via_rss")
@patch("collector.job_intel.fetch_via_apify")
def test_uses_apify_as_primary(mock_apify, mock_rss, config):
    mock_apify.return_value = APIFY_ITEMS
    result = fetch_job_intel(config, {"last_successful_delivery": None, "items": []})
    mock_apify.assert_called_once()
    mock_rss.assert_not_called()
    assert len(result) == 3


@patch("collector.job_intel.fetch_via_rss")
@patch("collector.job_intel.fetch_via_apify")
def test_falls_back_to_rss_on_apify_error(mock_apify, mock_rss, config):
    mock_apify.side_effect = ApifyFetchError("quota exceeded")
    mock_rss.return_value = RSS_ITEMS
    result = fetch_job_intel(config, {"last_successful_delivery": None, "items": []})
    mock_rss.assert_called_once()
    assert len(result) == 1


@patch("collector.job_intel.fetch_via_rss")
@patch("collector.job_intel.fetch_via_apify")
def test_location_tagging(mock_apify, mock_rss, config):
    mock_apify.return_value = APIFY_ITEMS
    result = fetch_job_intel(config, {"last_successful_delivery": None, "items": []})
    by_url = {r["id"]: r["location"] for r in result}
    assert by_url["https://simscale.com/news/1"] == "DE"
    assert by_url["https://cae.fr/2"] == "EU"
    assert by_url["https://us-company.com/3"] == "Global"


@patch("collector.job_intel.fetch_via_rss")
@patch("collector.job_intel.fetch_via_apify")
def test_dedup_against_state(mock_apify, mock_rss, config):
    mock_apify.return_value = APIFY_ITEMS
    state = {
        "last_successful_delivery": None,
        "items": [{"id": "https://simscale.com/news/1", "type": "job_intel", "state": "delivered", "discovered_at": "2026-04-13T07:00:00Z", "delivered_at": "2026-04-13T08:00:00Z"}],
    }
    result = fetch_job_intel(config, state)
    assert all(r["id"] != "https://simscale.com/news/1" for r in result)
    assert len(result) == 2
