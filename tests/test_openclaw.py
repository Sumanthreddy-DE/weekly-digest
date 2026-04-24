from unittest.mock import MagicMock, patch

import requests

from summarizer.openclaw import DEGRADED_PREFIX, summarize_job_intel, summarize_newsletters


def _ok_response(text):
    r = MagicMock()
    r.json.return_value = {"response": text}
    r.raise_for_status = MagicMock()
    return r


NEWSLETTERS = [
    {"id": "<m1@g>", "subject": "AI Weekly", "body": "A" * 100, "sender": "a@b.com", "date": "Mon"},
    {"id": "<m2@g>", "subject": "Sim News", "body": "B" * 100, "sender": "s@b.com", "date": "Mon"},
]
JOB_INTEL = [
    {"id": "https://ex.com/1", "title": "SimScale Munich raises Series B", "summary": "Munich startup...", "location": "DE", "url": "https://ex.com/1"},
]


@patch("summarizer.openclaw.requests.post")
def test_summarize_newsletters_returns_one_per_input(mock_post, config):
    mock_post.return_value = _ok_response("- point 1\n- point 2")
    result = summarize_newsletters(NEWSLETTERS, config)
    assert len(result) == 2
    assert all("summary" in r for r in result)


@patch("summarizer.openclaw.requests.post")
def test_summarize_newsletters_truncates_long_body(mock_post, config):
    mock_post.return_value = _ok_response("summary")
    long_nl = [{"id": "<m@g>", "subject": "X", "body": "Z" * 10000, "sender": "a@b.com", "date": "Mon"}]
    summarize_newsletters(long_nl, config)
    call_json = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1]["json"]
    assert len(call_json["prompt"]) < 10000


@patch("summarizer.openclaw.requests.post")
def test_summarize_newsletters_extractive_on_timeout(mock_post, config):
    mock_post.side_effect = requests.exceptions.Timeout()
    result = summarize_newsletters(NEWSLETTERS, config)
    assert len(result) == 2
    assert all(r["summary"].startswith(DEGRADED_PREFIX) for r in result)


@patch("summarizer.openclaw.requests.post")
def test_summarize_job_intel_returns_one_per_input(mock_post, config):
    mock_post.return_value = _ok_response("SimScale raised EUR 20M.")
    result = summarize_job_intel(JOB_INTEL, config)
    assert len(result) == 1
    assert result[0]["location"] == "DE"


@patch("summarizer.openclaw.requests.post")
def test_one_failure_does_not_stop_others(mock_post, config):
    mock_post.side_effect = [
        requests.exceptions.Timeout(),
        requests.exceptions.Timeout(),
        requests.exceptions.Timeout(),
        _ok_response("good summary"),
    ]
    result = summarize_newsletters(NEWSLETTERS, config)
    assert len(result) == 2
