import json
from datetime import datetime, timedelta, timezone

import pytest

from state.ledger import add_items, get_pending, load_state, mark_delivered, prune_state, save_state


def test_load_state_first_ever_run(tmp_path):
    result = load_state(str(tmp_path / "state.json"), str(tmp_path / ".initialized"))
    assert result == {"last_successful_delivery": None, "items": []}


def test_load_state_fail_closed_when_marker_exists(tmp_path):
    (tmp_path / ".initialized").touch()
    with pytest.raises(RuntimeError, match="state corrupted"):
        load_state(str(tmp_path / "state.json"), str(tmp_path / ".initialized"))


def test_load_state_falls_back_to_backup(tmp_path):
    state_path = tmp_path / "state.json"
    bak_path = tmp_path / "state.json.bak"
    state_path.write_text("not json")
    good = {"last_successful_delivery": None, "items": []}
    bak_path.write_text(json.dumps(good))
    result = load_state(str(state_path), str(tmp_path / ".initialized"))
    assert result == good


def test_load_state_both_corrupt_with_marker(tmp_path):
    (tmp_path / "state.json").write_text("bad")
    (tmp_path / "state.json.bak").write_text("also bad")
    (tmp_path / ".initialized").touch()
    with pytest.raises(RuntimeError, match="state corrupted"):
        load_state(str(tmp_path / "state.json"), str(tmp_path / ".initialized"))


def test_save_state_creates_backup(tmp_path):
    state_path = tmp_path / "state.json"
    marker_path = tmp_path / ".initialized"
    original = {"last_successful_delivery": None, "items": []}
    state_path.write_text(json.dumps(original))
    new_state = {"last_successful_delivery": "2026-04-20T08:00:00Z", "items": []}
    save_state(str(state_path), str(marker_path), new_state)
    bak = json.loads((tmp_path / "state.json.bak").read_text())
    assert bak == original


def test_save_state_atomic_valid_json(tmp_path):
    state_path = tmp_path / "state.json"
    marker_path = tmp_path / ".initialized"
    state = {"last_successful_delivery": None, "items": []}
    save_state(str(state_path), str(marker_path), state)
    assert json.loads(state_path.read_text()) == state


def test_save_state_creates_marker(tmp_path):
    state_path = tmp_path / "state.json"
    marker_path = tmp_path / ".initialized"
    save_state(str(state_path), str(marker_path), {"last_successful_delivery": None, "items": []})
    assert marker_path.exists()


def test_add_items_adds_as_discovered(empty_state):
    items = [
        {"id": "<msg-1@gmail>", "type": "newsletter"},
        {"id": "https://example.com/a", "type": "job_intel"},
    ]
    result = add_items(empty_state, items)
    assert len(result["items"]) == 2
    assert all(i["state"] == "discovered" for i in result["items"])
    assert all(i["discovered_at"] for i in result["items"])


def test_add_items_skips_duplicates(state_with_items):
    new_items = [
        {"id": "<msg-123@gmail>", "type": "newsletter"},
        {"id": "https://example.com/article-1", "type": "job_intel"},
        {"id": "https://example.com/brand-new", "type": "job_intel"},
    ]
    result = add_items(state_with_items, new_items)
    ids = [i["id"] for i in result["items"]]
    assert ids.count("<msg-123@gmail>") == 1
    assert ids.count("https://example.com/article-1") == 1
    assert "https://example.com/brand-new" in ids


def test_get_pending_returns_only_discovered(state_with_items):
    pending = get_pending(state_with_items)
    assert len(pending) == 1
    assert pending[0]["id"] == "https://example.com/article-1"
    assert all(i["state"] == "discovered" for i in pending)


def test_mark_delivered_flips_all_discovered(state_with_items):
    ts = "2026-04-20T08:05:00Z"
    result = mark_delivered(state_with_items, ts)
    assert result["last_successful_delivery"] == ts
    assert all(i["state"] == "delivered" for i in result["items"])


def test_prune_removes_old_delivered_keeps_discovered(tmp_path):
    old_ts = (datetime.now(timezone.utc) - timedelta(days=35)).isoformat()
    recent_ts = datetime.now(timezone.utc).isoformat()
    state = {
        "last_successful_delivery": recent_ts,
        "items": [
            {"id": "old", "type": "newsletter", "state": "delivered", "discovered_at": old_ts, "delivered_at": old_ts},
            {"id": "recent", "type": "newsletter", "state": "delivered", "discovered_at": recent_ts, "delivered_at": recent_ts},
            {"id": "pending", "type": "job_intel", "state": "discovered", "discovered_at": old_ts, "delivered_at": None},
        ],
    }
    result = prune_state(state, days=30)
    ids = [i["id"] for i in result["items"]]
    assert "old" not in ids
    assert "recent" in ids
    assert "pending" in ids
