from unittest.mock import patch

from discovery.sources.hn_hiring import HNHiringSource


MOCK_HIRING_POST = {
    "objectID": "999999",
    "title": "Ask HN: Who is hiring? (May 2026)",
}

MOCK_POST_DATA = {
    "id": 999999,
    "kids": [1000001, 1000002, 1000003],
}

MOCK_COMMENT_AI = {
    "id": 1000001,
    "text": "SimuCorp | ML Engineer | Berlin\nWe build AI for simulation and digital twins. <a href='https://simucorp.example'>https://simucorp.example</a>",
    "deleted": False,
}

MOCK_COMMENT_NON_AI = {
    "id": 1000002,
    "text": "RetailApp | Sales Manager | Hamburg<br>We sell shoes.",
    "deleted": False,
}

MOCK_COMMENT_DELETED = {
    "id": 1000003,
    "deleted": True,
}


def _config(tmp_path):
    return {
        "discovery": {
            "checkpoint_dir": str(tmp_path),
            "rss_delay_seconds": 0,
            "sources": {"hn_who_is_hiring": {"enabled": True}},
        }
    }


def test_iter_pages_finds_ai_companies(tmp_path, requests_mock):
    source = HNHiringSource(_config(tmp_path))

    requests_mock.get(
        "https://hn.algolia.com/api/v1/search",
        json={"hits": [MOCK_HIRING_POST]},
    )
    requests_mock.get(
        "https://hacker-news.firebaseio.com/v0/item/999999.json",
        json=MOCK_POST_DATA,
    )
    requests_mock.get(
        "https://hacker-news.firebaseio.com/v0/item/1000001.json",
        json=MOCK_COMMENT_AI,
    )
    requests_mock.get(
        "https://hacker-news.firebaseio.com/v0/item/1000002.json",
        json=MOCK_COMMENT_NON_AI,
    )
    requests_mock.get(
        "https://hacker-news.firebaseio.com/v0/item/1000003.json",
        json=MOCK_COMMENT_DELETED,
    )

    pages = list(source.iter_pages(1))
    assert len(pages) == 1
    page_num, url, companies = pages[0]
    assert page_num == 1
    assert "ycombinator" in url
    assert len(companies) == 1
    assert companies[0].name == "SimuCorp"
    assert companies[0].country == "DE"
    assert companies[0].city == "Berlin"


def test_iter_pages_no_post(tmp_path, requests_mock):
    source = HNHiringSource(_config(tmp_path))

    requests_mock.get(
        "https://hn.algolia.com/api/v1/search",
        json={"hits": []},
    )

    pages = list(source.iter_pages(1))
    assert pages == []


def test_parse_comment_extracts_company():
    source = HNHiringSource(_config(None))
    text = "Structuro AI | AI Engineer | Munich\nWe do FEA and simulation with ML. https://structuro.example"
    company = source._parse_comment(text, 12345, "2026-05-06T12:00:00Z")
    assert company is not None
    assert company.name == "Structuro AI"
    assert company.country == "DE"
    assert company.city == "Munich"
    assert company.homepage == "https://structuro.example"


def test_parse_comment_skips_non_ai():
    source = HNHiringSource(_config(None))
    text = "PizzaChain | Delivery Driver | Rome\nWe deliver pizza fast."
    company = source._parse_comment(text, 12345, "2026-05-06T12:00:00Z")
    assert company is None


def test_parse_comment_handles_no_url():
    source = HNHiringSource(_config(None))
    text = "AI Corp | Data Scientist | Berlin\nWe do machine learning."
    company = source._parse_comment(text, 12345, "2026-05-06T12:00:00Z")
    assert company is not None
    assert company.homepage is None
