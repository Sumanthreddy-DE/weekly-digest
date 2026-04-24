from unittest.mock import MagicMock, patch

from collector.rss_scraper import fetch_via_rss


def _make_entry(title, link):
    e = MagicMock()
    e.title = title
    e.link = link
    e.summary = ""
    e.get = lambda k, d=None: {"title": title, "link": link, "summary": ""}.get(k, d)
    return e


def _make_feed(entries):
    f = MagicMock()
    f.entries = entries
    return f


@patch("collector.rss_scraper.feedparser.parse")
def test_fetch_via_rss_returns_normalized_items(mock_parse, config):
    mock_parse.return_value = _make_feed([
        _make_entry("SimScale raises Series B", "https://news.google.com/1"),
    ])
    result = fetch_via_rss(config)
    assert len(result) > 0
    assert all("url" in r and "title" in r for r in result)


@patch("collector.rss_scraper.feedparser.parse")
def test_fetch_via_rss_deduplicates_urls(mock_parse, config):
    mock_parse.return_value = _make_feed([
        _make_entry("Article", "https://news.google.com/same"),
    ])
    result = fetch_via_rss(config)
    urls = [r["url"] for r in result]
    assert len(urls) == len(set(urls))


@patch("collector.rss_scraper.feedparser.parse")
def test_fetch_via_rss_handles_feed_error_gracefully(mock_parse, config):
    mock_parse.side_effect = Exception("network error")
    result = fetch_via_rss(config)
    assert result == []
