from unittest.mock import patch

from jobs.sources.hn_hiring import HNHiringJobsSource


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
    "text": "SimuCorp | ML Engineer | Berlin<br>We build AI for simulation and digital twins. <a href='https://simucorp.example'>Apply</a>",
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


class DummyConfig:
    pass


def test_run_finds_ai_jobs(requests_mock):
    source = HNHiringJobsSource({})

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

    jobs = list(source.run())
    assert len(jobs) == 1
    assert jobs[0].company_name == "SimuCorp"
    assert jobs[0].country == "DE"
    assert jobs[0].city == "Berlin"
    assert jobs[0].source == "hn_hiring"


def test_run_no_post(requests_mock):
    source = HNHiringJobsSource({})

    requests_mock.get(
        "https://hn.algolia.com/api/v1/search",
        json={"hits": []},
    )

    jobs = list(source.run())
    assert jobs == []


def test_run_api_error():
    source = HNHiringJobsSource({})
    with patch("jobs.sources.hn_hiring.requests.get", side_effect=RuntimeError("network down")):
        jobs = list(source.run())
    assert jobs == []


def test_parse_comment_skips_deleted():
    source = HNHiringJobsSource({})
    job = source._parse_comment("", 123, "2026-05-06T12:00:00Z")
    assert job is None


def test_parse_comment_extracts_url():
    source = HNHiringJobsSource({})
    text = "DataCorp | Research Engineer | Frankfurt\nhttps://datacorp.example/join-us"
    job = source._parse_comment(text, 123, "2026-05-06T12:00:00Z")
    assert job is not None
    assert job.url == "https://datacorp.example/join-us"
