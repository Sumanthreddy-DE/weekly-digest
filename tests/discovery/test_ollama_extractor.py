from unittest.mock import MagicMock, patch

import requests

from discovery.ollama_extractor import EXTRACT_PROMPT, extract_companies


def _response(payload):
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = payload
    return response


@patch("discovery.ollama_extractor.requests.post")
def test_extract_valid_json(mock_post, config):
    config["discovery"] = {
        "ollama_extractor": {"model": "qwen3:8b", "timeout_seconds": 90, "max_retries": 1}
    }
    mock_post.return_value = _response({"response": '{"companies": [{"name": "FooCo", "homepage": null, "country": "DE", "city": "Berlin", "ai_focus": "AI for CAE", "sectors": ["ai_cae"]}]}'})

    companies = extract_companies("Foo text", config)
    assert len(companies) == 1
    assert companies[0]["name"] == "FooCo"


@patch("discovery.ollama_extractor.requests.post")
def test_extract_invalid_json_returns_empty(mock_post, config):
    config["discovery"] = {
        "ollama_extractor": {"model": "qwen3:8b", "timeout_seconds": 90, "max_retries": 1}
    }
    mock_post.return_value = _response({"response": "not json"})
    assert extract_companies("Foo text", config) == []


@patch("discovery.ollama_extractor.requests.post")
def test_extract_network_error_retries_then_fails(mock_post, config):
    config["discovery"] = {
        "ollama_extractor": {"model": "qwen3:8b", "timeout_seconds": 90, "max_retries": 1}
    }
    mock_post.side_effect = requests.exceptions.ConnectionError("nope")
    assert extract_companies("Foo text", config) == []
    assert mock_post.call_count == 2


@patch("discovery.ollama_extractor.requests.post")
def test_extract_truncates_long_input(mock_post, config):
    config["discovery"] = {
        "ollama_extractor": {"model": "qwen3:8b", "timeout_seconds": 90, "max_retries": 1}
    }
    mock_post.return_value = _response({"response": '{"companies": []}'})
    extract_companies("X" * 10000, config)
    prompt = mock_post.call_args.kwargs["json"]["prompt"]
    assert prompt.startswith(EXTRACT_PROMPT)
    assert len(prompt) == len(EXTRACT_PROMPT) + 8000


@patch("discovery.ollama_extractor.requests.post")
def test_extract_uses_format_json_flag(mock_post, config):
    config["discovery"] = {
        "ollama_extractor": {"model": "qwen3:8b", "timeout_seconds": 90, "max_retries": 1}
    }
    mock_post.return_value = _response({"response": '{"companies": []}'})
    extract_companies("Foo text", config)
    assert mock_post.call_args.kwargs["json"]["format"] == "json"
