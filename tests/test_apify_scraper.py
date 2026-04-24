from unittest.mock import MagicMock, patch

import pytest

from collector.apify_scraper import ApifyFetchError, fetch_via_apify


def _make_apify_mock(items):
    client = MagicMock()
    run = {"defaultDatasetId": "ds-123"}
    client.actor.return_value.call.return_value = run
    client.dataset.return_value.iterate_items.return_value = iter(items)
    return client


@patch("collector.apify_scraper.ApifyClient")
def test_fetch_via_apify_returns_items(mock_cls, config):
    items = [
        {"url": "https://simscale.com/news", "title": "SimScale raises Series B"},
        {"url": "https://example.com/2", "title": "FEA startup hires ML team"},
    ]
    mock_cls.return_value = _make_apify_mock(items)
    result = fetch_via_apify(config)
    assert len(result) == 2
    assert result[0]["url"] == "https://simscale.com/news"


@patch("collector.apify_scraper.ApifyClient")
def test_fetch_via_apify_passes_timeout(mock_cls, config):
    mock_client = _make_apify_mock([])
    mock_cls.return_value = mock_client
    fetch_via_apify(config)
    call_kwargs = mock_client.actor.return_value.call.call_args
    assert call_kwargs.kwargs.get("timeout_secs") == 600


@patch("collector.apify_scraper.ApifyClient")
def test_fetch_via_apify_wraps_errors(mock_cls, config):
    mock_client = MagicMock()
    mock_client.actor.return_value.call.side_effect = Exception("API error")
    mock_cls.return_value = mock_client
    with pytest.raises(ApifyFetchError):
        fetch_via_apify(config)
