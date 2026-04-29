import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest
from filelock import FileLock, Timeout

from lock.run_lock import LockHeldError, acquire_lock


def test_acquire_lock_writes_pid_metadata(tmp_path):
    lock_path = str(tmp_path / "run.lock")
    with acquire_lock(lock_path, stale_minutes=30):
        meta = json.loads(Path(lock_path + ".meta").read_text())
        assert meta["pid"] == os.getpid()
        assert "acquired_at" in meta


def test_second_acquire_raises_lock_held_error(tmp_path):
    lock_path = str(tmp_path / "run.lock")
    held = FileLock(lock_path)
    held.acquire()
    try:
        with pytest.raises(LockHeldError):
            with acquire_lock(lock_path, stale_minutes=30):
                pass
    finally:
        held.release()


def test_stale_lock_is_reclaimed(tmp_path):
    lock_path = str(tmp_path / "run.lock")
    stale_meta = {"pid": 999999, "acquired_at": "2000-01-01T00:00:00"}
    Path(lock_path + ".meta").write_text(json.dumps(stale_meta))

    call_count = {"n": 0}
    real_acquire = FileLock.acquire

    def fake_acquire(self, *args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise Timeout(self.lock_file)
        return real_acquire(self, *args, **kwargs)

    with patch.object(FileLock, "acquire", fake_acquire):
        with patch("lock.run_lock._is_process_alive", return_value=False):
            with acquire_lock(lock_path, stale_minutes=1):
                meta = json.loads(Path(lock_path + ".meta").read_text())
                assert meta["pid"] == os.getpid()
