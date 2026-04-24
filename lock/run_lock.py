import json
import logging
import os
import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from filelock import FileLock, Timeout

log = logging.getLogger(__name__)


class LockHeldError(Exception):
    pass


def _is_process_alive(pid: int) -> bool:
    try:
        if sys.platform == "win32":
            import ctypes
            handle = ctypes.windll.kernel32.OpenProcess(0x0400, False, pid)
            if handle:
                ctypes.windll.kernel32.CloseHandle(handle)
                return True
            return False
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def _read_meta(lock_path: str) -> dict:
    try:
        return json.loads(Path(lock_path).read_text())
    except Exception:
        return {}


def _write_meta(lock_path: str) -> None:
    Path(lock_path).write_text(
        json.dumps({"pid": os.getpid(), "acquired_at": datetime.now().isoformat()})
    )


@contextmanager
def acquire_lock(lock_path: str, stale_minutes: int):
    Path(lock_path).parent.mkdir(parents=True, exist_ok=True)
    fl = FileLock(lock_path, timeout=0)
    try:
        fl.acquire()
        _write_meta(lock_path)
        try:
            yield
        finally:
            fl.release()
    except Timeout:
        meta = _read_meta(lock_path)
        pid = meta.get("pid")
        try:
            acquired_at = datetime.fromisoformat(meta.get("acquired_at", ""))
            age_minutes = (datetime.now() - acquired_at).total_seconds() / 60
        except ValueError:
            age_minutes = stale_minutes + 1

        if pid and not _is_process_alive(pid) and age_minutes > stale_minutes:
            log.warning("Stale lock (PID %s, %.1f min), reclaiming", pid, age_minutes)
            Path(lock_path).unlink(missing_ok=True)
            fl2 = FileLock(lock_path, timeout=5)
            fl2.acquire()
            _write_meta(lock_path)
            try:
                yield
            finally:
                fl2.release()
        else:
            raise LockHeldError(f"Pipeline already running (PID {pid}). Aborting.")
