# Weekly Digest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python cron script that ingests Gmail newsletters + scrapes job-relevant company intel via Apify (RSS fallback), summarizes with OpenClaw, and delivers a tiered HTML email digest every Sunday morning.

**Architecture:** Five-stage pipeline (replay → newsletters → job-intel → summarize → format+send) orchestrated by `main.py`. Single `state.json` delivery ledger tracks every item from discovery to delivery. Apify is primary scraper with automatic RSS fallback on quota/error. OpenClaw handles summarization with extractive degraded mode when unreachable.

**Tech Stack:** Python 3.11+, `imaplib`/`smtplib`/`email` (stdlib), `feedparser`, `beautifulsoup4`, `requests`, `pyyaml`, `jinja2`, `filelock`, `apify-client`, `pytest`, `pytest-mock`

---

## File Map

```
weekly-digest/
├── main.py                     # entry point — orchestrates all 5 stages
├── config.yaml                 # config template (no secrets)
├── .env.example                # env var documentation
├── collector/
│   ├── __init__.py
│   ├── newsletters.py          # Gmail IMAP fetch, HTML strip, dedup against ledger
│   ├── job_intel.py            # Apify-first, RSS fallback, location tagging, dedup
│   ├── apify_scraper.py        # Apify actor trigger + dataset fetch
│   └── rss_scraper.py          # feedparser RSS fallback
├── summarizer/
│   ├── __init__.py
│   └── openclaw.py             # OpenClaw requests, per-item isolation, degraded mode
├── formatter/
│   ├── __init__.py
│   ├── email_builder.py        # jinja2 HTML email, tiered DE/EU/Global layout
│   └── digest_template.html   # jinja2 HTML template
├── sender/
│   ├── __init__.py
│   └── smtp.py                 # smtplib send + fallback to local HTML file
├── state/
│   ├── __init__.py
│   └── ledger.py               # state.json CRUD, atomic write, backup, fail-closed
├── lock/
│   ├── __init__.py
│   └── run_lock.py             # filelock with PID metadata + stale detection
├── data/
│   └── .gitkeep               # auto-generated files go here — do not commit state.json
├── logs/
│   └── .gitkeep               # cron output logs — do not commit
├── tests/
│   ├── conftest.py             # shared fixtures: config dict, sample states, tmp_path helpers
│   ├── test_ledger.py
│   ├── test_run_lock.py
│   ├── test_newsletters.py
│   ├── test_apify_scraper.py
│   ├── test_rss_scraper.py
│   ├── test_job_intel.py
│   ├── test_openclaw.py
│   ├── test_email_builder.py
│   ├── test_smtp.py
│   └── test_main.py
├── requirements.txt
└── docs/
    ├── deployment.md
    └── specs/
        └── 2026-04-20-newsletter-weekly-digest-design.md
```

---

### Task 1: Project Scaffold

**Files:**
- Create: `requirements.txt`
- Create: `config.yaml`
- Create: `.env.example`
- Create: `collector/__init__.py`, `summarizer/__init__.py`, `formatter/__init__.py`, `sender/__init__.py`, `state/__init__.py`, `lock/__init__.py`
- Create: `tests/conftest.py`
- Create: `data/.gitkeep`, `logs/.gitkeep`

- [ ] **Step 1: Create requirements.txt**

```
feedparser==6.0.11
beautifulsoup4==4.12.3
requests==2.32.3
pyyaml==6.0.2
jinja2==3.1.4
filelock==3.16.1
apify-client==1.8.1
pytest==8.3.3
pytest-mock==3.14.0
```

- [ ] **Step 2: Create config.yaml**

```yaml
gmail:
  email: "${GMAIL_EMAIL}"
  app_password: "${GMAIL_APP_PASSWORD}"
  imap_server: "imap.gmail.com"

newsletters:
  senders: []  # add sender email addresses here

openclaw:
  base_url: "${OPENCLAW_BASE_URL}"

apify:
  api_token: "${APIFY_API_TOKEN}"
  actor_id: "apify/rss-feed-scraper"
  timeout_secs: 600

keywords:
  sectors:
    - "AI for engineering"
    - "computational engineering"
    - "simulation software"
    - "digital twins"
    - "physics-informed machine learning"
    - "FEA software"
    - "CAE startup"
  signals:
    - "raised funding"
    - "Series A"
    - "hiring"
    - "new round"
    - "expansion"

digest:
  send_to: "${DIGEST_SEND_TO}"
  send_day: "sunday"
  send_hour: 8

state:
  file: "data/state.json"
  prune_after_days: 30
  default_lookback_days: 7

lock:
  file: "data/run.lock"
  stale_minutes: 30

openclaw_resilience:
  timeout_seconds: 60
  max_retries: 2
  max_input_chars: 4000
  degraded_extract_chars: 200
```

- [ ] **Step 3: Create .env.example**

```
GMAIL_EMAIL=your-email@gmail.com
GMAIL_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
OPENCLAW_BASE_URL=http://localhost:11434
APIFY_API_TOKEN=apify_api_xxxx
DIGEST_SEND_TO=your-email@gmail.com
```

- [ ] **Step 4: Create package directories and empty `__init__.py` files**

```bash
mkdir -p collector summarizer formatter sender state lock tests data logs
touch collector/__init__.py summarizer/__init__.py formatter/__init__.py
touch sender/__init__.py state/__init__.py lock/__init__.py
touch data/.gitkeep logs/.gitkeep
```

- [ ] **Step 5: Create tests/conftest.py**

```python
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
        "openclaw": {"base_url": "http://localhost:11434"},
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
```

- [ ] **Step 6: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: all packages install without error.

- [ ] **Step 7: Verify pytest collects cleanly**

```bash
pytest tests/ --collect-only
```

Expected: `0 items / 0 errors`

- [ ] **Step 8: Commit**

```bash
git add requirements.txt config.yaml .env.example collector/ summarizer/ formatter/ sender/ state/ lock/ tests/ data/.gitkeep logs/.gitkeep
git commit -m "chore: project scaffold — packages, config, test fixtures"
```

---

### Task 2: State Ledger

**Files:**
- Create: `state/ledger.py`
- Test: `tests/test_ledger.py`

The single source of truth for all items. Newsletters keyed by Gmail Message-ID, job intel by URL. Atomic writes via `os.replace`. Backup created before every write. Bootstrap marker distinguishes first run from state corruption.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_ledger.py
import json
import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from state.ledger import (
    load_state,
    save_state,
    add_items,
    get_pending,
    mark_delivered,
    prune_state,
)


def test_load_state_first_ever_run(tmp_path):
    """No state.json, no marker → return empty state (first run)."""
    result = load_state(
        str(tmp_path / "state.json"),
        str(tmp_path / ".initialized"),
    )
    assert result == {"last_successful_delivery": None, "items": []}


def test_load_state_fail_closed_when_marker_exists(tmp_path):
    """state.json missing but marker exists → raise RuntimeError."""
    (tmp_path / ".initialized").touch()
    with pytest.raises(RuntimeError, match="state corrupted"):
        load_state(str(tmp_path / "state.json"), str(tmp_path / ".initialized"))


def test_load_state_falls_back_to_backup(tmp_path):
    """Corrupt state.json but valid .bak → load from backup."""
    state_path = tmp_path / "state.json"
    bak_path = tmp_path / "state.json.bak"
    state_path.write_text("not json")
    good = {"last_successful_delivery": None, "items": []}
    bak_path.write_text(json.dumps(good))
    result = load_state(str(state_path), str(tmp_path / ".initialized"))
    assert result == good


def test_load_state_both_corrupt_with_marker(tmp_path):
    """Both state.json and .bak corrupt, marker exists → raise RuntimeError."""
    (tmp_path / "state.json").write_text("bad")
    (tmp_path / "state.json.bak").write_text("also bad")
    (tmp_path / ".initialized").touch()
    with pytest.raises(RuntimeError, match="state corrupted"):
        load_state(str(tmp_path / "state.json"), str(tmp_path / ".initialized"))


def test_save_state_creates_backup(tmp_path):
    """save_state copies existing file to .bak before overwriting."""
    state_path = tmp_path / "state.json"
    marker_path = tmp_path / ".initialized"
    original = {"last_successful_delivery": None, "items": []}
    state_path.write_text(json.dumps(original))
    new_state = {"last_successful_delivery": "2026-04-20T08:00:00Z", "items": []}
    save_state(str(state_path), str(marker_path), new_state)
    bak = json.loads((tmp_path / "state.json.bak").read_text())
    assert bak == original


def test_save_state_atomic_valid_json(tmp_path):
    """Saved file is valid JSON matching the input."""
    state_path = tmp_path / "state.json"
    marker_path = tmp_path / ".initialized"
    state = {"last_successful_delivery": None, "items": []}
    save_state(str(state_path), str(marker_path), state)
    assert json.loads(state_path.read_text()) == state


def test_save_state_creates_marker(tmp_path):
    """save_state creates .initialized marker."""
    state_path = tmp_path / "state.json"
    marker_path = tmp_path / ".initialized"
    save_state(str(state_path), str(marker_path), {"last_successful_delivery": None, "items": []})
    assert marker_path.exists()


def test_add_items_adds_as_discovered(empty_state):
    """New items get state=discovered and discovered_at timestamp."""
    items = [
        {"id": "<msg-1@gmail>", "type": "newsletter"},
        {"id": "https://example.com/a", "type": "job_intel"},
    ]
    result = add_items(empty_state, items)
    assert len(result["items"]) == 2
    assert all(i["state"] == "discovered" for i in result["items"])
    assert all(i["discovered_at"] for i in result["items"])


def test_add_items_skips_duplicates(state_with_items):
    """Items already in ledger (any state) are skipped."""
    new_items = [
        {"id": "<msg-123@gmail>", "type": "newsletter"},        # already delivered
        {"id": "https://example.com/article-1", "type": "job_intel"},  # already discovered
        {"id": "https://example.com/brand-new", "type": "job_intel"},  # new
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
            {"id": "old", "type": "newsletter", "state": "delivered",
             "discovered_at": old_ts, "delivered_at": old_ts},
            {"id": "recent", "type": "newsletter", "state": "delivered",
             "discovered_at": recent_ts, "delivered_at": recent_ts},
            {"id": "pending", "type": "job_intel", "state": "discovered",
             "discovered_at": old_ts, "delivered_at": None},
        ],
    }
    result = prune_state(state, days=30)
    ids = [i["id"] for i in result["items"]]
    assert "old" not in ids
    assert "recent" in ids
    assert "pending" in ids  # never prune discovered
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_ledger.py -v
```

Expected: `ImportError: cannot import name 'load_state' from 'state.ledger'`

- [ ] **Step 3: Implement state/ledger.py**

```python
# state/ledger.py
import json
import logging
import os
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path

log = logging.getLogger(__name__)


def load_state(state_path: str, marker_path: str) -> dict:
    def _try_load(path):
        try:
            return json.loads(Path(path).read_text())
        except Exception:
            return None

    primary = _try_load(state_path)
    if primary is not None:
        return primary

    backup = _try_load(state_path + ".bak")
    if backup is not None:
        log.warning("state.json corrupt, loaded from backup")
        return backup

    if Path(marker_path).exists():
        raise RuntimeError(
            f"state corrupted: both {state_path} and {state_path}.bak unreadable "
            "but .initialized marker exists. Manual recovery required."
        )

    log.info("First-ever run: initializing empty state")
    return {"last_successful_delivery": None, "items": []}


def save_state(state_path: str, marker_path: str, state: dict) -> None:
    sp = Path(state_path)
    sp.parent.mkdir(parents=True, exist_ok=True)

    if sp.exists():
        shutil.copy2(str(sp), str(sp) + ".bak")

    tmp = str(sp) + ".tmp"
    content = json.dumps(state, indent=2)
    Path(tmp).write_text(content)
    json.loads(Path(tmp).read_text())  # validate before replacing
    os.replace(tmp, str(sp))

    Path(marker_path).parent.mkdir(parents=True, exist_ok=True)
    Path(marker_path).touch()


def add_items(state: dict, items: list) -> dict:
    existing_ids = {i["id"] for i in state["items"]}
    now = datetime.now(timezone.utc).isoformat()
    new_items = [
        {
            "id": item["id"],
            "type": item["type"],
            "state": "discovered",
            "discovered_at": now,
            "delivered_at": None,
            **{k: v for k, v in item.items() if k not in ("id", "type")},
        }
        for item in items
        if item["id"] not in existing_ids
    ]
    return {**state, "items": state["items"] + new_items}


def get_pending(state: dict) -> list:
    return [i for i in state["items"] if i["state"] == "discovered"]


def mark_delivered(state: dict, timestamp: str) -> dict:
    updated = [
        {**item, "state": "delivered", "delivered_at": timestamp}
        if item["state"] == "discovered" else item
        for item in state["items"]
    ]
    return {**state, "items": updated, "last_successful_delivery": timestamp}


def prune_state(state: dict, days: int) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    kept = [
        item for item in state["items"]
        if not (
            item["state"] == "delivered"
            and item.get("delivered_at")
            and datetime.fromisoformat(
                item["delivered_at"].replace("Z", "+00:00")
            ) < cutoff
        )
    ]
    return {**state, "items": kept}
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_ledger.py -v
```

Expected: all 12 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add state/ledger.py tests/test_ledger.py
git commit -m "feat: state ledger — atomic write, backup, fail-closed recovery, pruning"
```

---

### Task 3: Run Lock

**Files:**
- Create: `lock/run_lock.py`
- Test: `tests/test_run_lock.py`

Prevents concurrent pipeline runs. OS-level exclusive lock via `filelock`. Writes PID + timestamp so stale locks from crashed processes can be detected and reclaimed.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_run_lock.py
import json
import os
import pytest
from pathlib import Path
from filelock import FileLock
from lock.run_lock import acquire_lock, LockHeldError


def test_acquire_lock_writes_pid_metadata(tmp_path):
    lock_path = str(tmp_path / "run.lock")
    with acquire_lock(lock_path, stale_minutes=30):
        meta = json.loads(Path(lock_path).read_text())
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
    """Dead PID + old timestamp → lock reclaimed without error."""
    lock_path = str(tmp_path / "run.lock")
    stale_meta = {"pid": 999999, "acquired_at": "2000-01-01T00:00:00"}
    Path(lock_path).write_text(json.dumps(stale_meta))
    with acquire_lock(lock_path, stale_minutes=1):
        meta = json.loads(Path(lock_path).read_text())
        assert meta["pid"] == os.getpid()
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_run_lock.py -v
```

Expected: `ImportError: cannot import name 'acquire_lock'`

- [ ] **Step 3: Implement lock/run_lock.py**

```python
# lock/run_lock.py
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
            log.warning("Stale lock (PID %s, %.1f min) — reclaiming", pid, age_minutes)
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
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_run_lock.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add lock/run_lock.py tests/test_run_lock.py
git commit -m "feat: run lock — filelock with PID metadata and stale detection"
```

---

### Task 4: Newsletter Collector

**Files:**
- Create: `collector/newsletters.py`
- Test: `tests/test_newsletters.py`

Connects to Gmail IMAP. Lookback window derived from `last_successful_delivery`. Strips HTML to plain text. Deduplicates against ledger by Message-ID.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_newsletters.py
import pytest
from unittest.mock import MagicMock, patch
from collector.newsletters import fetch_newsletters

SAMPLE_RAW_EMAIL = (
    b"From: sender@example.com\r\n"
    b"Subject: Test Newsletter\r\n"
    b"Date: Mon, 20 Apr 2026 10:00:00 +0000\r\n"
    b"Message-ID: <test-msg-1@example>\r\n\r\n"
    b"<html><body><p>Hello <b>world</b>.</p></body></html>"
)


def _make_imap(raw_email):
    imap = MagicMock()
    imap.search.return_value = ("OK", [b"1"])
    imap.fetch.return_value = ("OK", [(b"1 (RFC822 {1234}", raw_email)])
    imap.select.return_value = ("OK", [])
    imap.login.return_value = ("OK", [])
    return imap


@patch("collector.newsletters.imaplib.IMAP4_SSL")
def test_fetch_newsletters_returns_list(mock_cls, config):
    mock_imap = _make_imap(SAMPLE_RAW_EMAIL)
    mock_cls.return_value.__enter__ = MagicMock(return_value=mock_imap)
    mock_cls.return_value.__exit__ = MagicMock(return_value=False)
    state = {"last_successful_delivery": None, "items": []}
    result = fetch_newsletters(config, state)
    assert isinstance(result, list)


@patch("collector.newsletters.imaplib.IMAP4_SSL")
def test_fetch_newsletters_strips_html(mock_cls, config):
    mock_imap = _make_imap(SAMPLE_RAW_EMAIL)
    mock_cls.return_value.__enter__ = MagicMock(return_value=mock_imap)
    mock_cls.return_value.__exit__ = MagicMock(return_value=False)
    state = {"last_successful_delivery": None, "items": []}
    result = fetch_newsletters(config, state)
    if result:
        assert "<html>" not in result[0]["body"]
        assert "Hello" in result[0]["body"]


@patch("collector.newsletters.imaplib.IMAP4_SSL")
def test_fetch_newsletters_deduplicates_against_state(mock_cls, config):
    mock_imap = _make_imap(SAMPLE_RAW_EMAIL)
    mock_cls.return_value.__enter__ = MagicMock(return_value=mock_imap)
    mock_cls.return_value.__exit__ = MagicMock(return_value=False)
    state = {
        "last_successful_delivery": None,
        "items": [{"id": "<test-msg-1@example>", "type": "newsletter",
                   "state": "delivered", "discovered_at": "2026-04-13T07:00:00Z",
                   "delivered_at": "2026-04-13T08:00:00Z"}],
    }
    result = fetch_newsletters(config, state)
    assert all(r["id"] != "<test-msg-1@example>" for r in result)
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_newsletters.py -v
```

Expected: `ImportError: cannot import name 'fetch_newsletters'`

- [ ] **Step 3: Implement collector/newsletters.py**

```python
# collector/newsletters.py
import email
import imaplib
import logging
from datetime import datetime, timezone, timedelta
from email.header import decode_header as _decode_header_raw

from bs4 import BeautifulSoup

log = logging.getLogger(__name__)


def _decode_header(value: str) -> str:
    parts = _decode_header_raw(value)
    result = []
    for part, charset in parts:
        if isinstance(part, bytes):
            result.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            result.append(part)
    return " ".join(result)


def _strip_html(html: str) -> str:
    return BeautifulSoup(html, "html.parser").get_text(separator=" ", strip=True)


def _get_body(msg) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            payload = part.get_payload(decode=True)
            if not payload:
                continue
            text = payload.decode("utf-8", errors="replace")
            if ct == "text/plain":
                return text
            if ct == "text/html":
                return _strip_html(text)
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            raw = payload.decode("utf-8", errors="replace")
            return _strip_html(raw) if "<html" in raw.lower() else raw
    return ""


def _since_date(state: dict, default_days: int) -> str:
    last = state.get("last_successful_delivery")
    if last:
        dt = datetime.fromisoformat(last.replace("Z", "+00:00")) - timedelta(days=1)
    else:
        dt = datetime.now(timezone.utc) - timedelta(days=default_days)
    return dt.strftime("%d-%b-%Y")


def fetch_newsletters(config: dict, state: dict) -> list:
    gmail = config["gmail"]
    senders = config["newsletters"]["senders"]
    existing_ids = {i["id"] for i in state.get("items", [])}
    since = _since_date(state, config["state"]["default_lookback_days"])
    results = []

    with imaplib.IMAP4_SSL(gmail["imap_server"]) as imap:
        imap.login(gmail["email"], gmail["app_password"])
        imap.select("INBOX")
        for sender in senders:
            _, data = imap.search(None, f'(FROM "{sender}" SINCE "{since}")')
            if not data or not data[0]:
                continue
            for num in data[0].split():
                _, raw_data = imap.fetch(num, "(RFC822)")
                if not raw_data or not raw_data[0]:
                    continue
                raw = raw_data[0][1] if isinstance(raw_data[0], tuple) else raw_data[0]
                msg = email.message_from_bytes(raw)
                msg_id = msg.get("Message-ID", "").strip()
                if not msg_id or msg_id in existing_ids:
                    continue
                results.append({
                    "id": msg_id,
                    "type": "newsletter",
                    "sender": sender,
                    "subject": _decode_header(msg.get("Subject", "")),
                    "date": msg.get("Date", ""),
                    "body": _get_body(msg),
                })
    log.info("Fetched %d new newsletters", len(results))
    return results
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_newsletters.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add collector/newsletters.py tests/test_newsletters.py
git commit -m "feat: newsletter collector — IMAP fetch, HTML strip, dedup"
```

---

### Task 5: Apify Scraper

**Files:**
- Create: `collector/apify_scraper.py`
- Test: `tests/test_apify_scraper.py`

Triggers Apify actor with sector × signal query combinations. Waits synchronously (weekly cron, no rush). Returns raw item list or raises `ApifyFetchError`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_apify_scraper.py
import pytest
from unittest.mock import MagicMock, patch
from collector.apify_scraper import fetch_via_apify, ApifyFetchError


def _make_apify_mock(items):
    client = MagicMock()
    run = {"defaultDatasetId": "ds-123"}
    client.actor.return_value.call.return_value = run
    client.dataset.return_value.iterate_items.return_value = iter(items)
    return client


@patch("collector.apify_scraper.ApifyClient")
def test_fetch_via_apify_returns_items(mock_cls, config):
    items = [
        {"url": "https://simscale.com/news", "title": "SimScale raises Series B"},
        {"url": "https://example.com/2", "title": "FEA startup hires ML team"},
    ]
    mock_cls.return_value = _make_apify_mock(items)
    result = fetch_via_apify(config)
    assert len(result) == 2
    assert result[0]["url"] == "https://simscale.com/news"


@patch("collector.apify_scraper.ApifyClient")
def test_fetch_via_apify_passes_timeout(mock_cls, config):
    mock_client = _make_apify_mock([])
    mock_cls.return_value = mock_client
    fetch_via_apify(config)
    call_kwargs = mock_client.actor.return_value.call.call_args
    assert call_kwargs.kwargs.get("timeout_secs") == 600


@patch("collector.apify_scraper.ApifyClient")
def test_fetch_via_apify_wraps_errors(mock_cls, config):
    mock_client = MagicMock()
    mock_client.actor.return_value.call.side_effect = Exception("API error")
    mock_cls.return_value = mock_client
    with pytest.raises(ApifyFetchError):
        fetch_via_apify(config)
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_apify_scraper.py -v
```

Expected: `ImportError: cannot import name 'fetch_via_apify'`

- [ ] **Step 3: Implement collector/apify_scraper.py**

```python
# collector/apify_scraper.py
import logging
from apify_client import ApifyClient

log = logging.getLogger(__name__)


class ApifyFetchError(Exception):
    pass


def _build_queries(config: dict) -> list:
    return [
        f"{sector} {signal}"
        for sector in config["keywords"]["sectors"]
        for signal in config["keywords"]["signals"]
    ]


def fetch_via_apify(config: dict) -> list:
    apify_cfg = config["apify"]
    queries = _build_queries(config)
    try:
        client = ApifyClient(apify_cfg["api_token"])
        run = client.actor(apify_cfg["actor_id"]).call(
            run_input={"search_queries": queries},
            timeout_secs=apify_cfg["timeout_secs"],
        )
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        log.info("Apify: fetched %d items", len(items))
        return items
    except Exception as e:
        raise ApifyFetchError(f"Apify fetch failed: {e}") from e
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_apify_scraper.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add collector/apify_scraper.py tests/test_apify_scraper.py
git commit -m "feat: Apify scraper — actor trigger, timeout, error wrapping"
```

---

### Task 6: RSS Fallback Scraper

**Files:**
- Create: `collector/rss_scraper.py`
- Test: `tests/test_rss_scraper.py`

Google News RSS feeds generated from sector × signal queries. Deduplicates URLs within a single run. Silently continues on per-feed errors.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_rss_scraper.py
import pytest
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
    """Same URL appearing in multiple feeds only included once."""
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_rss_scraper.py -v
```

Expected: `ImportError: cannot import name 'fetch_via_rss'`

- [ ] **Step 3: Implement collector/rss_scraper.py**

```python
# collector/rss_scraper.py
import logging
import urllib.parse
import feedparser

log = logging.getLogger(__name__)

_GOOGLE_NEWS = "https://news.google.com/rss/search?q={query}&hl=en&gl=US&ceid=US:en"


def _feed_urls(config: dict) -> list:
    return [
        _GOOGLE_NEWS.format(query=urllib.parse.quote(f"{sector} {signal}"))
        for sector in config["keywords"]["sectors"]
        for signal in config["keywords"]["signals"]
    ]


def fetch_via_rss(config: dict) -> list:
    seen = set()
    results = []
    for url in _feed_urls(config):
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                link = entry.get("link", "")
                if not link or link in seen:
                    continue
                seen.add(link)
                results.append({
                    "url": link,
                    "title": entry.get("title", ""),
                    "summary": entry.get("summary", ""),
                    "source": "rss",
                })
        except Exception as e:
            log.warning("RSS error for %s: %s", url, e)
    log.info("RSS fallback: %d items", len(results))
    return results
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_rss_scraper.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add collector/rss_scraper.py tests/test_rss_scraper.py
git commit -m "feat: RSS fallback scraper — Google News feeds, URL dedup"
```

---

### Task 7: Job Intel Orchestrator

**Files:**
- Create: `collector/job_intel.py`
- Test: `tests/test_job_intel.py`

Tries Apify first, falls back to RSS on `ApifyFetchError`. Tags each item with location (DE/EU/Global) by scanning title + summary + URL for geo keywords. Deduplicates against state ledger.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_job_intel.py
import pytest
from unittest.mock import patch
from collector.job_intel import fetch_job_intel
from collector.apify_scraper import ApifyFetchError

APIFY_ITEMS = [
    {"url": "https://simscale.com/news/1", "title": "SimScale Munich raises Series B"},
    {"url": "https://cae.fr/2", "title": "French CAE startup hires ML team in Paris"},
    {"url": "https://us-company.com/3", "title": "US digital twin startup closes round"},
]
RSS_ITEMS = [
    {"url": "https://rss.com/1", "title": "FEA news", "summary": "", "source": "rss"},
]


@patch("collector.job_intel.fetch_via_rss")
@patch("collector.job_intel.fetch_via_apify")
def test_uses_apify_as_primary(mock_apify, mock_rss, config):
    mock_apify.return_value = APIFY_ITEMS
    result = fetch_job_intel(config, {"last_successful_delivery": None, "items": []})
    mock_apify.assert_called_once()
    mock_rss.assert_not_called()
    assert len(result) == 3


@patch("collector.job_intel.fetch_via_rss")
@patch("collector.job_intel.fetch_via_apify")
def test_falls_back_to_rss_on_apify_error(mock_apify, mock_rss, config):
    mock_apify.side_effect = ApifyFetchError("quota exceeded")
    mock_rss.return_value = RSS_ITEMS
    result = fetch_job_intel(config, {"last_successful_delivery": None, "items": []})
    mock_rss.assert_called_once()
    assert len(result) == 1


@patch("collector.job_intel.fetch_via_rss")
@patch("collector.job_intel.fetch_via_apify")
def test_location_tagging(mock_apify, mock_rss, config):
    mock_apify.return_value = APIFY_ITEMS
    result = fetch_job_intel(config, {"last_successful_delivery": None, "items": []})
    by_url = {r["id"]: r["location"] for r in result}
    assert by_url["https://simscale.com/news/1"] == "DE"
    assert by_url["https://cae.fr/2"] == "EU"
    assert by_url["https://us-company.com/3"] == "Global"


@patch("collector.job_intel.fetch_via_rss")
@patch("collector.job_intel.fetch_via_apify")
def test_dedup_against_state(mock_apify, mock_rss, config):
    mock_apify.return_value = APIFY_ITEMS
    state = {
        "last_successful_delivery": None,
        "items": [{"id": "https://simscale.com/news/1", "type": "job_intel",
                   "state": "delivered", "discovered_at": "2026-04-13T07:00:00Z",
                   "delivered_at": "2026-04-13T08:00:00Z"}],
    }
    result = fetch_job_intel(config, state)
    assert all(r["id"] != "https://simscale.com/news/1" for r in result)
    assert len(result) == 2
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_job_intel.py -v
```

Expected: `ImportError: cannot import name 'fetch_job_intel'`

- [ ] **Step 3: Implement collector/job_intel.py**

```python
# collector/job_intel.py
import logging
from collector.apify_scraper import fetch_via_apify, ApifyFetchError
from collector.rss_scraper import fetch_via_rss

log = logging.getLogger(__name__)

_DE = ["germany", "german", "berlin", "munich", "münchen", "hamburg", "frankfurt", "stuttgart", "cologne", ".de"]
_EU = ["europe", "european", "france", "french", "paris", "netherlands", "sweden", "uk", "britain", "spain", "italy", ".eu"]


def _location(text: str) -> str:
    t = text.lower()
    if any(k in t for k in _DE):
        return "DE"
    if any(k in t for k in _EU):
        return "EU"
    return "Global"


def _normalize(raw: dict) -> dict:
    url = raw.get("url") or raw.get("link") or ""
    title = raw.get("title") or ""
    summary = raw.get("summary") or raw.get("description") or ""
    return {
        "id": url,
        "type": "job_intel",
        "url": url,
        "title": title,
        "summary": summary,
        "location": _location(f"{title} {summary} {url}"),
    }


def fetch_job_intel(config: dict, state: dict) -> list:
    existing_ids = {i["id"] for i in state.get("items", [])}
    try:
        raw = fetch_via_apify(config)
        log.info("Job intel: Apify (%d raw)", len(raw))
    except ApifyFetchError as e:
        log.warning("Apify failed (%s), using RSS fallback", e)
        raw = fetch_via_rss(config)
        log.info("Job intel: RSS fallback (%d raw)", len(raw))

    normalized = [_normalize(r) for r in raw]
    result = [i for i in normalized if i["id"] and i["id"] not in existing_ids]
    log.info("Job intel: %d after dedup", len(result))
    return result
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_job_intel.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add collector/job_intel.py tests/test_job_intel.py
git commit -m "feat: job intel orchestrator — Apify/RSS fallback, location tagging, dedup"
```

---

### Task 8: OpenClaw Summarizer

**Files:**
- Create: `summarizer/openclaw.py`
- Test: `tests/test_openclaw.py`

Per-item isolation: one timeout or error does not stop others. Extractive fallback (first N chars, `[PARTIAL]` prefix) when OpenClaw is unreachable. Input truncated to `max_input_chars` before sending.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_openclaw.py
import pytest
import requests
from unittest.mock import MagicMock, patch
from summarizer.openclaw import summarize_newsletters, summarize_job_intel, DEGRADED_PREFIX


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
    {"id": "https://ex.com/1", "title": "SimScale Munich raises Series B",
     "summary": "Munich startup...", "location": "DE", "url": "https://ex.com/1"},
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
    """First call times out, second succeeds — both items returned."""
    mock_post.side_effect = [
        requests.exceptions.Timeout(),
        requests.exceptions.Timeout(),  # retries
        requests.exceptions.Timeout(),  # retries
        _ok_response("good summary"),
        _ok_response("good summary"),
        _ok_response("good summary"),
    ]
    result = summarize_newsletters(NEWSLETTERS, config)
    assert len(result) == 2
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_openclaw.py -v
```

Expected: `ImportError: cannot import name 'summarize_newsletters'`

- [ ] **Step 3: Implement summarizer/openclaw.py**

```python
# summarizer/openclaw.py
import logging
import time
import requests

log = logging.getLogger(__name__)
DEGRADED_PREFIX = "[PARTIAL] "


def _call(prompt: str, config: dict) -> str:
    res = config["openclaw_resilience"]
    url = f"{config['openclaw']['base_url']}/api/generate"
    last_exc = None
    for attempt in range(res["max_retries"] + 1):
        try:
            r = requests.post(
                url,
                json={"model": "default", "prompt": prompt, "stream": False},
                timeout=res["timeout_seconds"],
            )
            r.raise_for_status()
            return r.json().get("response", "")
        except Exception as e:
            last_exc = e
            if attempt < res["max_retries"]:
                time.sleep(2 ** attempt)
    raise last_exc


def _extractive(text: str, chars: int) -> str:
    return DEGRADED_PREFIX + text[:chars].strip()


def summarize_newsletters(newsletters: list, config: dict) -> list:
    res = config["openclaw_resilience"]
    results = []
    for nl in newsletters:
        body = nl["body"][: res["max_input_chars"]]
        prompt = f"Summarize in 2-3 bullet point key takeaways.\n\nSubject: {nl['subject']}\n\n{body}"
        try:
            summary = _call(prompt, config)
        except Exception as e:
            log.warning("OpenClaw failed for '%s': %s", nl.get("subject"), e)
            summary = _extractive(nl["body"], res["degraded_extract_chars"])
        results.append({**nl, "summary": summary})
    return results


def summarize_job_intel(items: list, config: dict) -> list:
    res = config["openclaw_resilience"]
    results = []
    for item in items:
        text = f"{item.get('title', '')} — {item.get('summary', '')}"[: res["max_input_chars"]]
        prompt = (
            "In 1-3 sentences: what happened, who they are, where based, "
            f"relevance to computational engineering / AI / simulation.\n\n{text}"
        )
        try:
            summary = _call(prompt, config)
        except Exception as e:
            log.warning("OpenClaw failed for '%s': %s", item.get("url"), e)
            summary = _extractive(text, res["degraded_extract_chars"])
        results.append({**item, "summary": summary})
    return results
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_openclaw.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add summarizer/openclaw.py tests/test_openclaw.py
git commit -m "feat: OpenClaw summarizer — per-item isolation, retries, extractive fallback"
```

---

### Task 9: Email Builder

**Files:**
- Create: `formatter/email_builder.py`
- Create: `formatter/digest_template.html`
- Test: `tests/test_email_builder.py`

Jinja2 HTML template. Sections: newsletter highlights → DE intel → EU intel → Global intel → stats footer. Subject gets `[PARTIAL]` prefix if any summary is extractive.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_email_builder.py
import pytest
from formatter.email_builder import build_email, DEGRADED_PREFIX

NL = [{"subject": "AI Weekly", "sender": "ai@news.com", "date": "Mon 20 Apr",
       "summary": "- point 1\n- point 2"}]
JI = [
    {"title": "SimScale raises Series B", "url": "https://simscale.com",
     "location": "DE", "summary": "Munich-based SimScale raised EUR 20M."},
    {"title": "French CAE startup", "url": "https://cae.fr",
     "location": "EU", "summary": "Paris-based CAE startup hiring."},
    {"title": "US digital twin", "url": "https://us.com",
     "location": "Global", "summary": "US company raised funding."},
]


def test_returns_html_string(config):
    html, subject = build_email(NL, JI, config)
    assert "<html" in html.lower()
    assert "AI Weekly" in html


def test_subject_format(config):
    _, subject = build_email(NL, JI, config)
    assert "Weekly Digest" in subject


def test_de_before_eu_before_global(config):
    html, _ = build_email(NL, JI, config)
    assert html.index("SimScale") < html.index("French CAE") < html.index("US digital twin")


def test_stats_footer_present(config):
    html, _ = build_email(NL, JI, config)
    assert "1" in html  # 1 newsletter
    assert "3" in html  # 3 intel items


def test_partial_subject_prefix_when_degraded(config):
    degraded_nl = [{**NL[0], "summary": f"{DEGRADED_PREFIX}first 200 chars..."}]
    _, subject = build_email(degraded_nl, JI, config)
    assert subject.startswith(DEGRADED_PREFIX)
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_email_builder.py -v
```

Expected: `ImportError: cannot import name 'build_email'`

- [ ] **Step 3: Create formatter/digest_template.html**

```html
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
body { font-family: Arial, sans-serif; max-width: 700px; margin: 0 auto; color: #333; }
h1 { color: #2c3e50; }
h2 { color: #2980b9; border-bottom: 1px solid #eee; padding-bottom: 4px; }
h3 { color: #555; margin-bottom: 4px; }
.item { margin-bottom: 18px; }
.de  { border-left: 4px solid #27ae60; padding-left: 10px; }
.eu  { border-left: 4px solid #2980b9; padding-left: 10px; }
.gl  { border-left: 4px solid #7f8c8d; padding-left: 10px; }
.stats { background: #f8f9fa; padding: 12px; margin-top: 24px; font-size: 0.9em; color: #666; }
a { color: #2980b9; }
pre { white-space: pre-wrap; font-family: inherit; }
</style>
</head>
<body>
<h1>{{ subject }}</h1>

{% if newsletters %}
<h2>Newsletter Highlights</h2>
{% for nl in newsletters %}
<div class="item">
  <h3>{{ nl.subject }} &mdash; <small>{{ nl.sender }} ({{ nl.date }})</small></h3>
  <pre>{{ nl.summary }}</pre>
</div>
{% endfor %}
{% endif %}

{% if de_items %}
<h2>Germany &mdash; Job Intel</h2>
{% for item in de_items %}
<div class="item de">
  <strong><a href="{{ item.url }}">{{ item.title }}</a></strong>
  <p>{{ item.summary }}</p>
</div>
{% endfor %}
{% endif %}

{% if eu_items %}
<h2>Europe &mdash; Job Intel</h2>
{% for item in eu_items %}
<div class="item eu">
  <strong><a href="{{ item.url }}">{{ item.title }}</a></strong>
  <p>{{ item.summary }}</p>
</div>
{% endfor %}
{% endif %}

{% if global_items %}
<h2>Global &mdash; Job Intel</h2>
{% for item in global_items %}
<div class="item gl">
  <strong><a href="{{ item.url }}">{{ item.title }}</a></strong>
  <p>{{ item.summary }}</p>
</div>
{% endfor %}
{% endif %}

<div class="stats">
  {{ newsletter_count }} newsletter{{ 's' if newsletter_count != 1 else '' }} |
  {{ intel_count }} companies found |
  DE {{ de_count }} | EU {{ eu_count }} | Global {{ global_count }}
</div>
</body>
</html>
```

- [ ] **Step 4: Implement formatter/email_builder.py**

```python
# formatter/email_builder.py
from datetime import date
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

DEGRADED_PREFIX = "[PARTIAL] "
_TEMPLATE_DIR = Path(__file__).parent
_TEMPLATE_FILE = "digest_template.html"


def build_email(newsletter_summaries: list, job_intel_summaries: list, config: dict) -> tuple:
    today = date.today().strftime("%Y-%m-%d")
    subject = f"Weekly Digest — {today}"

    all_summaries = [s.get("summary", "") for s in newsletter_summaries + job_intel_summaries]
    if any(s.startswith(DEGRADED_PREFIX) for s in all_summaries):
        subject = DEGRADED_PREFIX + subject

    de = [i for i in job_intel_summaries if i.get("location") == "DE"]
    eu = [i for i in job_intel_summaries if i.get("location") == "EU"]
    gl = [i for i in job_intel_summaries if i.get("location") == "Global"]

    env = Environment(loader=FileSystemLoader(str(_TEMPLATE_DIR)))
    html = env.get_template(_TEMPLATE_FILE).render(
        subject=subject,
        newsletters=newsletter_summaries,
        de_items=de,
        eu_items=eu,
        global_items=gl,
        newsletter_count=len(newsletter_summaries),
        intel_count=len(job_intel_summaries),
        de_count=len(de),
        eu_count=len(eu),
        global_count=len(gl),
    )
    return html, subject
```

- [ ] **Step 5: Run tests to confirm they pass**

```bash
pytest tests/test_email_builder.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add formatter/email_builder.py formatter/digest_template.html tests/test_email_builder.py
git commit -m "feat: email builder — tiered HTML digest, DE/EU/Global order, degraded prefix"
```

---

### Task 10: SMTP Sender

**Files:**
- Create: `sender/smtp.py`
- Test: `tests/test_smtp.py`

Sends HTML digest via Gmail SMTP. On failure, saves HTML to `logs/` as fallback and returns `False` — pipeline must not crash on send failure.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_smtp.py
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from sender.smtp import send_email

HTML = "<html><body><p>Test digest content</p></body></html>"
SUBJECT = "Weekly Digest — 2026-04-20"


@patch("sender.smtp.smtplib.SMTP_SSL")
def test_send_email_returns_true_on_success(mock_cls, config):
    mock_smtp = MagicMock()
    mock_cls.return_value.__enter__ = MagicMock(return_value=mock_smtp)
    mock_cls.return_value.__exit__ = MagicMock(return_value=False)
    assert send_email(HTML, SUBJECT, config) is True
    mock_smtp.sendmail.assert_called_once()


@patch("sender.smtp.smtplib.SMTP_SSL")
def test_send_email_uses_correct_credentials(mock_cls, config):
    mock_smtp = MagicMock()
    mock_cls.return_value.__enter__ = MagicMock(return_value=mock_smtp)
    mock_cls.return_value.__exit__ = MagicMock(return_value=False)
    send_email(HTML, SUBJECT, config)
    mock_smtp.login.assert_called_once_with(
        config["gmail"]["email"], config["gmail"]["app_password"]
    )


@patch("sender.smtp.smtplib.SMTP_SSL")
def test_send_email_returns_false_and_saves_fallback(mock_cls, config, tmp_path):
    mock_cls.side_effect = Exception("SMTP refused")
    result = send_email(HTML, SUBJECT, config, fallback_dir=str(tmp_path))
    assert result is False
    saved = list(tmp_path.glob("*.html"))
    assert len(saved) == 1
    assert "Test digest content" in saved[0].read_text()
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_smtp.py -v
```

Expected: `ImportError: cannot import name 'send_email'`

- [ ] **Step 3: Implement sender/smtp.py**

```python
# sender/smtp.py
import logging
import smtplib
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

log = logging.getLogger(__name__)


def send_email(html: str, subject: str, config: dict, fallback_dir: str = "logs") -> bool:
    gmail = config["gmail"]
    send_to = config["digest"]["send_to"]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = gmail["email"]
    msg["To"] = send_to
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(gmail["email"], gmail["app_password"])
            smtp.sendmail(gmail["email"], send_to, msg.as_string())
        log.info("Digest sent to %s", send_to)
        return True
    except Exception as e:
        log.error("SMTP failed: %s — saving fallback", e)
        _save_fallback(html, fallback_dir)
        return False


def _save_fallback(html: str, fallback_dir: str) -> None:
    Path(fallback_dir).mkdir(parents=True, exist_ok=True)
    path = Path(fallback_dir) / f"digest-{date.today().isoformat()}.html"
    path.write_text(html)
    log.info("Fallback saved to %s", path)
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_smtp.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add sender/smtp.py tests/test_smtp.py
git commit -m "feat: SMTP sender — Gmail send with local HTML fallback"
```

---

### Task 11: Main Orchestrator

**Files:**
- Create: `main.py`
- Test: `tests/test_main.py`

Loads config with `${ENV_VAR}` expansion, acquires run lock, executes all 5 stages. Updates state only on successful send — items remain `discovered` if send fails so next run replays them.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_main.py
import pytest
from unittest.mock import MagicMock, patch


@patch("main.send_email", return_value=True)
@patch("main.build_email", return_value=("<html/>", "Weekly Digest — 2026-04-20"))
@patch("main.summarize_job_intel", return_value=[])
@patch("main.summarize_newsletters", return_value=[])
@patch("main.fetch_job_intel", return_value=[])
@patch("main.fetch_newsletters", return_value=[])
@patch("main.save_state")
@patch("main.load_state", return_value={"last_successful_delivery": None, "items": []})
@patch("main.load_config")
def test_full_pipeline_runs_without_error(
    mock_cfg, mock_load, mock_save, *_, config
):
    mock_cfg.return_value = config
    with patch("main.acquire_lock") as mock_lock:
        mock_lock.return_value.__enter__ = MagicMock(return_value=None)
        mock_lock.return_value.__exit__ = MagicMock(return_value=False)
        import main
        main.run()
    mock_save.assert_called()


@patch("main.send_email", return_value=False)
@patch("main.build_email", return_value=("<html/>", "Weekly Digest — 2026-04-20"))
@patch("main.summarize_job_intel", return_value=[])
@patch("main.summarize_newsletters", return_value=[])
@patch("main.fetch_job_intel", return_value=[])
@patch("main.fetch_newsletters", return_value=[])
@patch("main.save_state")
@patch("main.load_state", return_value={"last_successful_delivery": None, "items": []})
@patch("main.load_config")
def test_state_not_marked_delivered_on_send_failure(
    mock_cfg, mock_load, mock_save, *_, config
):
    mock_cfg.return_value = config
    with patch("main.acquire_lock") as mock_lock:
        mock_lock.return_value.__enter__ = MagicMock(return_value=None)
        mock_lock.return_value.__exit__ = MagicMock(return_value=False)
        import main
        main.run()
    # Only one save_state call (to persist discovered items), not the delivered update
    assert mock_save.call_count == 1
    saved = mock_save.call_args[0][2]
    assert saved["last_successful_delivery"] is None
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_main.py -v
```

Expected: `ModuleNotFoundError: No module named 'main'`

- [ ] **Step 3: Implement main.py**

```python
# main.py
import logging
import os
import yaml
from datetime import datetime, timezone
from pathlib import Path

from collector.newsletters import fetch_newsletters
from collector.job_intel import fetch_job_intel
from formatter.email_builder import build_email
from lock.run_lock import acquire_lock, LockHeldError
from sender.smtp import send_email
from state.ledger import (
    load_state, save_state, add_items, get_pending, mark_delivered, prune_state
)
from summarizer.openclaw import summarize_newsletters, summarize_job_intel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
log = logging.getLogger(__name__)


def load_config(path: str = "config.yaml") -> dict:
    raw = Path(path).read_text()
    for key, val in os.environ.items():
        raw = raw.replace(f"${{{key}}}", val)
    return yaml.safe_load(raw)


def run():
    config = load_config()
    state_path = config["state"]["file"]
    marker_path = str(Path(state_path).parent / ".initialized")

    try:
        with acquire_lock(config["lock"]["file"], config["lock"]["stale_minutes"]):
            _pipeline(config, state_path, marker_path)
    except LockHeldError as e:
        log.error("Lock held: %s", e)
        raise SystemExit(1)


def _pipeline(config: dict, state_path: str, marker_path: str):
    state = load_state(state_path, marker_path)

    # Stage 0: replay pending from prior crashed run
    pending = get_pending(state)
    log.info("Stage 0: %d pending items from prior run", len(pending))

    # Stage 1: newsletters
    newsletters = fetch_newsletters(config, state)
    log.info("Stage 1: %d new newsletters", len(newsletters))

    # Stage 2: job intel
    job_intel = fetch_job_intel(config, state)
    log.info("Stage 2: %d new job intel items", len(job_intel))

    # Persist all new discovered items
    all_new = newsletters + job_intel
    state = add_items(state, all_new)
    save_state(state_path, marker_path, state)

    # Build digest batch: pending + new
    nl_batch = [i for i in pending if i.get("type") == "newsletter"] + newsletters
    ji_batch = [i for i in pending if i.get("type") == "job_intel"] + job_intel

    # Stage 3: summarize
    nl_summaries = summarize_newsletters(nl_batch, config)
    ji_summaries = summarize_job_intel(ji_batch, config)
    log.info("Stage 3: %d nl summaries, %d intel summaries", len(nl_summaries), len(ji_summaries))

    # Stage 4: format + send
    html, subject = build_email(nl_summaries, ji_summaries, config)
    success = send_email(html, subject, config)

    if success:
        ts = datetime.now(timezone.utc).isoformat()
        state = mark_delivered(state, ts)
        state = prune_state(state, config["state"]["prune_after_days"])
        save_state(state_path, marker_path, state)
        log.info("Digest delivered. State updated.")
    else:
        log.error("Send failed. Items remain discovered for next run.")


if __name__ == "__main__":
    run()
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_main.py -v
```

Expected: all 2 tests PASS.

- [ ] **Step 5: Run full test suite**

```bash
pytest tests/ -v
```

Expected: all tests PASS across all modules.

- [ ] **Step 6: Commit**

```bash
git add main.py tests/test_main.py
git commit -m "feat: main orchestrator — 5-stage pipeline, state lifecycle, lock integration"
```

---

### Task 12: Deployment Guide

**Files:**
- Create: `docs/deployment.md`

- [ ] **Step 1: Create docs/deployment.md**

```markdown
# Deployment Guide

## Prerequisites

- Python 3.11+ on VPS (same VPS running OpenClaw)
- Gmail account with App Password: Google Account → Security → 2-Step Verification → App Passwords
- Apify account (free $5 tier sufficient for weekly runs)

## Setup

```bash
git clone https://github.com/Sumanthreddy-DE/weekly-digest.git
cd weekly-digest
pip install -r requirements.txt
cp .env.example .env
# fill in .env with real values
```

## Configure newsletter senders

Edit `config.yaml`:

```yaml
newsletters:
  senders:
    - newsletter@example.com
    - updates@somecompany.com
```

## Set environment variables

Edit `.env`:

```
GMAIL_EMAIL=your-email@gmail.com
GMAIL_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
OPENCLAW_BASE_URL=http://localhost:11434
APIFY_API_TOKEN=apify_api_xxxx
DIGEST_SEND_TO=your-email@gmail.com
```

Source it in cron or add to `/etc/environment`.

## Cron setup

```bash
crontab -e
```

Add:

```
0 8 * * 0 cd /path/to/weekly-digest && source .env && python main.py >> logs/digest.log 2>&1
```

Runs every Sunday at 8:00 AM server time.

## Manual test run

```bash
source .env && python main.py
```

## Monitoring

- **Logs:** `logs/digest.log`
- **Fallback digests:** `logs/digest-YYYY-MM-DD.html` (created when SMTP fails)
- **State:** `data/state.json` (human-readable JSON)
- **If state corrupted:** Delete `data/.initialized` to reset to first-run mode, or restore `data/state.json.bak`
```

- [ ] **Step 2: Commit**

```bash
git add docs/deployment.md
git commit -m "docs: deployment guide — cron, env vars, newsletter config, monitoring"
```

---

## Self-Review

### Spec Coverage

| Requirement | Task |
|---|---|
| Stage 0: replay discovered from prior run | Task 11 (`_pipeline`) |
| Stage 1: IMAP, lookback from `last_successful_delivery`, HTML strip, dedup | Task 4 |
| Stage 2: Apify primary, RSS fallback on error/timeout/quota | Tasks 5, 6, 7 |
| Location tagging DE/EU/Global | Task 7 |
| Stage 3: OpenClaw, per-item isolation, input truncation, extractive fallback | Task 8 |
| `[PARTIAL]` subject prefix in degraded mode | Tasks 8, 9 |
| Stage 4: tiered HTML (DE → EU → Global), stats footer | Task 9 |
| SMTP send + local HTML fallback | Task 10 |
| `state.json`: atomic write, backup, fail-closed on double corruption | Task 2 |
| Bootstrap marker `.initialized` | Task 2 |
| `filelock` run coordination + stale PID detection | Task 3 |
| Prune only `delivered` items >30 days — never `discovered` | Task 2 |
| `${ENV_VAR}` expansion in config | Task 11 |
| Cron + deployment docs | Task 12 |

All spec requirements covered.

### Placeholder Scan

No TBD, no "implement later", no "add appropriate error handling" — all steps have full code.

### Type Consistency

- `fetch_newsletters` → list of dicts with `id`, `type`, `body`, `subject`, `sender`, `date`
- `fetch_job_intel` → list of dicts with `id`, `type`, `url`, `title`, `summary`, `location`
- `add_items` expects `id` and `type` keys — both collectors set these ✓
- `summarize_newsletters` receives newsletter dicts, returns same dicts + `summary` key ✓
- `summarize_job_intel` receives job intel dicts, returns same dicts + `summary` key ✓
- `build_email` receives lists with `summary` + `subject`/`title` + `location` — consistent ✓
- `DEGRADED_PREFIX` defined in `openclaw.py` and `email_builder.py` as same string `"[PARTIAL] "` — import if needed or keep as constant in both (current approach is fine since they're independent modules)
