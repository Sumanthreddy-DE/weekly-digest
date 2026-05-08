from pathlib import Path
from unittest.mock import patch

from discovery.checkpoint import Checkpoint, read_checkpoint, write_checkpoint


def test_checkpoint_write_then_read(tmp_path):
    checkpoint = Checkpoint(
        source="eu_startups",
        started_at="2026-04-29T12:00:00Z",
        last_completed_page=3,
        last_completed_url="https://example.com/page/3",
        items_emitted=42,
        status="in_progress",
        error=None,
    )

    write_checkpoint(str(tmp_path), checkpoint)
    loaded = read_checkpoint(str(tmp_path), "eu_startups")
    assert loaded == checkpoint


def test_checkpoint_atomic_no_partial(tmp_path):
    checkpoint = Checkpoint(
        source="eu_startups",
        started_at="2026-04-29T12:00:00Z",
        last_completed_page=1,
        last_completed_url=None,
        items_emitted=1,
        status="in_progress",
    )
    target = tmp_path / "eu_startups.json"
    target.write_text('{"ok": true}')

    with patch("discovery.checkpoint.os.replace", side_effect=RuntimeError("boom")):
        try:
            write_checkpoint(str(tmp_path), checkpoint)
        except RuntimeError:
            pass

    assert target.read_text() == '{"ok": true}'
    assert not list(Path(tmp_path).glob("*.tmp"))


def test_checkpoint_missing_returns_none(tmp_path):
    assert read_checkpoint(str(tmp_path), "missing") is None
