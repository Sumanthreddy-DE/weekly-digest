import pytest


@pytest.fixture
def config():
    return {
        "gmail": {
            "email": "test@gmail.com",
            "app_password": "test-pass",
            "imap_server": "imap.gmail.com",
        },
        "newsletters": {"senders": ["sender@example.com"]},
        "openclaw": {"base_url": "http://localhost:11434", "model": "qwen3:8b"},
        "apify": {
            "api_token": "test-token",
            "actor_id": "apify/rss-feed-scraper",
            "timeout_secs": 600,
        },
        "keywords": {
            "sectors": ["simulation software", "digital twins"],
            "signals": ["raised funding", "Series A"],
        },
        "digest": {"send_to": "dest@gmail.com", "send_day": "sunday", "send_hour": 8},
        "state": {
            "file": "data/state.json",
            "prune_after_days": 30,
            "default_lookback_days": 7,
        },
        "lock": {"file": "data/run.lock", "stale_minutes": 30},
        "openclaw_resilience": {
            "timeout_seconds": 60,
            "max_retries": 2,
            "max_input_chars": 4000,
            "degraded_extract_chars": 200,
        },
    }


@pytest.fixture
def empty_state():
    return {"last_successful_delivery": None, "items": []}


@pytest.fixture
def state_with_items():
    return {
        "last_successful_delivery": "2026-04-13T08:05:00Z",
        "items": [
            {
                "id": "<msg-123@gmail>",
                "type": "newsletter",
                "state": "delivered",
                "discovered_at": "2026-04-13T07:00:00Z",
                "delivered_at": "2026-04-13T08:05:00Z",
            },
            {
                "id": "https://example.com/article-1",
                "type": "job_intel",
                "state": "discovered",
                "discovered_at": "2026-04-20T07:00:00Z",
                "delivered_at": None,
            },
        ],
    }
