# Newsletter Weekly Digest — Design Spec

**Date:** 2026-04-20
**Status:** Approved
**Author:** Sumanth

---

## Problem

Sumanth receives 3-5 newsletters per week but rarely reads them. Additionally, he's job-hunting in AI/ML for engineering, simulation, digital twins, and CAE — but has no systematic way to track companies raising funding or hiring in these sectors across Europe.

## Solution

A Python script running on VPS via weekly cron job that:

1. Ingests newsletter emails from Gmail
2. Scrapes the web for job-relevant company intel
3. Summarizes everything with OpenClaw (self-hosted LLM)
4. Sends a tiered HTML email digest every Sunday morning

Target read time: 10-15 minutes (~2000-3000 words).

---

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌───────────┐     ┌────────────┐
│ Gmail IMAP   │────>│              │────>│           │────>│            │
│ (newsletters)│     │   Collector  │     │ Summarizer│     │  Formatter │──> Email
│              │     │              │     │ (OpenClaw) │     │  (HTML)    │
│ Web Scrapers │────>│              │────>│           │────>│            │
│ (job intel)  │     │              │     │           │     │            │
└─────────────┘     └──────────────┘     └───────────┘     └────────────┘
```

Five stages, each its own module. Single Python entry point. Cron runs Sunday 8:00 AM.

---

## Stage 0: Replay Pending Items

Before any collection, load `state.json` and gather all items with state `discovered` (unsent from prior crashed/failed runs). These form the initial digest batch. New items from Stage 1 and Stage 2 are merged alongside them.

This ensures crashed `discovered` items are always picked up — they're loaded first, then new items added.

---

## Stage 1: Collector — Newsletter Ingestion

- Config file (YAML) lists newsletter sender addresses — manually maintained
- Connects to Gmail via IMAP (`imaplib`), fetches emails from listed senders
- **Lookback window:** derived from `last_successful_delivery` timestamp in `state.json` + 1 day buffer. First run ever defaults to 7 days. This is the single source of truth for how far back to fetch — no hardcoded day counts elsewhere.
- Before processing, dedup fetched emails against `state.json` — skip any Message-ID already in state (whether `discovered` or `delivered`)
- Extracts body content — strips HTML to clean text, preserves links
- Gmail App Password for auth (env var, never in config)

**Per newsletter stored in memory:**
- Sender name
- Subject line
- Date received
- Clean text body
- Original links
- Gmail Message-ID (stable dedup key)

No database. In-memory during pipeline run. Durable state tracked in `state.json`.

---

## Stage 2: Collector — Job Intel Scraping

### Sources — Two-Tier with Auto-Fallback

**Primary: Apify Cloud (free $5 tier)**

Uses `apify-client` Python SDK to trigger pre-built actors (RSS extractor, article extractor) on Apify's cloud infrastructure. Better coverage than raw RSS — actors handle pagination, JS-rendered pages, and deeper article extraction.

- Script calls Apify API with search query combinations
- Synchronous wait for actor to finish (weekly batch, no rush)
- Fetch results from actor's default dataset
- Apify handles URL deduplication within the scrape itself

**Fallback: Local RSS Scraping (free, no API key)**

If Apify fails (402 quota exceeded, API error, timeout), automatically fall back to local RSS:

1. **Google News RSS** — query-based feeds
2. **TechCrunch RSS** — startup/funding news, keyword-filtered
3. **Crunchbase News RSS** — funding rounds
4. **EU-Startups RSS** — European startup focus

**Fallback trigger (auto-detect):**
```python
try:
    # timeout_secs from config (default 600s) — prevents stuck actors holding run lock
    run = client.actor(actor_id).call(
        run_input={"search_queries": queries},
        timeout_secs=config["apify"]["timeout_secs"],
    )
    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    log.info("Apify: fetched %d items", len(items))
except (ApifyClientError, TimeoutError) as e:
    log.warning("Apify unavailable (%s), falling back to RSS", e)
    items = fetch_via_rss(queries)
```

Timeout, quota errors, and API failures all trigger the same RSS fallback path. No unbounded waits.

**Important: Job-intel is best-effort regardless of source.** Neither Apify nor RSS guarantees catching every article. Apify is significantly better (deeper scraping, more sources), but both capture what's available at poll time. Acceptable for a personal tool.

**Monitoring:** Each run logs:
- Which source was used (Apify or RSS fallback)
- Number of items found per source
- If any source returns zero items for 2+ consecutive runs → log warning

### Keywords (config-driven)

```yaml
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
```

Sectors x signals x regions = search query combinations. Passed to Apify actor or used to generate RSS feed URLs (fallback).

### Location Extraction

- Parse article text for country/city mentions
- Tag each result: DE / EU / Global
- Sort by priority: Germany first, then EU, then Global

### Deduplication

- All job-intel URLs tracked in `state.json` (same ledger as newsletters)
- Before adding newly scraped items, check `state.json` for matching URLs in any state (`discovered` or `delivered`) — skip duplicates
- Items auto-pruned from ledger after 30 days

---

## Stage 3: Summarizer

- Batch content by category (newsletters vs job intel)
- Send to OpenClaw with structured prompts:
  - Newsletters: "Summarize each newsletter in 2-3 key takeaways"
  - Job intel: "For each item: what happened, who they are, where based, relevance to computational engineering / AI / simulation"

### Tiered Depth

| Relevance | Depth | Example |
|-----------|-------|---------|
| High — DE company, direct sector match | 4-5 sentences + company URL | SimScale raises Series B |
| Medium — EU company or adjacent sector | 2-3 sentences | French CAE startup hires ML team |
| Low — Global or loosely related | 1 sentence | US digital twin company funding |

### Relevance Scoring

Simple weighted keyword overlap:
- More keyword matches = higher score
- Location multiplier: DE (3x) > EU (2x) > Global (1x)
- No ML needed — just arithmetic in Python

### Token Management

If content exceeds single prompt limit, chunk by category. Newsletters and job intel summarized separately.

---

## Stage 4: Formatter & Sender

### Email Structure (HTML)

```
Subject: Weekly Digest — [date]

--- NEWSLETTER HIGHLIGHTS ---

[Newsletter Name] — [date]
- Key takeaway 1
- Key takeaway 2
- Key takeaway 3

--- GERMANY — JOB INTEL ---

> CompanyX raised EUR 5M Series A (Munich)
  CAE simulation platform for automotive...
  [link]

--- EUROPE — JOB INTEL ---

> ...

--- GLOBAL — JOB INTEL ---

> ...

--- STATS ---
4 newsletters | 12 companies found
DE 3 | EU 5 | Global 4
```

### Sending

- Python `smtplib` with Gmail App Password
- Fallback: save digest as local markdown on VPS + log error

---

## Configuration

### config.yaml

```yaml
gmail:
  email: "your-email@gmail.com"
  app_password: "${GMAIL_APP_PASSWORD}"
  imap_server: "imap.gmail.com"

newsletters:
  - "sender1@example.com"
  - "sender2@example.com"

openclaw:
  base_url: "http://localhost:PORT"

apify:
  api_token: "${APIFY_API_TOKEN}"
  actor_id: "apify/rss-feed-scraper"  # or article extractor
  timeout_secs: 600  # 10-minute max wait

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
  send_to: "your-email@gmail.com"
  send_day: "sunday"
  send_hour: 8

state:
  file: "data/state.json"
  prune_after_days: 30
  default_lookback_days: 7  # only used on first run ever

lock:
  file: "data/run.lock"
  stale_minutes: 30

openclaw_resilience:
  timeout_seconds: 60
  max_retries: 2
  max_input_chars: 4000
  degraded_extract_chars: 200
```

### Secrets

Gmail App Password stored as environment variable only. Never in config or code.

### Scheduling

```
0 8 * * 0 cd /path/to/weekly-digest && python main.py >> logs/digest.log 2>&1
```

---

## Project Structure

```
weekly-digest/
├── main.py              # entry point — orchestrates all stages
├── config.yaml          # all configuration
├── collector/
│   ├── __init__.py
│   ├── newsletters.py   # Gmail IMAP fetch + HTML stripping
│   ├── job_intel.py     # orchestrates Apify (primary) + RSS (fallback)
│   ├── apify_scraper.py # Apify actor trigger + dataset fetch
│   └── rss_scraper.py   # local RSS fallback (feedparser)
├── summarizer/
│   ├── __init__.py
│   └── openclaw.py      # LLM summarization via OpenClaw
├── formatter/
│   ├── __init__.py
│   └── email_builder.py # HTML email construction + tiered layout
├── sender/
│   ├── __init__.py
│   └── smtp.py          # email sending + fallback to local file
├── data/
│   ├── state.json           # single delivery ledger — all items, all states (auto-generated)
│   ├── .initialized         # bootstrap marker — created after first successful delivery
│   └── run.lock             # exclusive file lock with PID metadata (transient)
├── logs/                # cron output logs
├── tests/               # unit + integration tests
├── requirements.txt
└── docs/
    └── specs/
        └── 2026-04-20-newsletter-weekly-digest-design.md
```

---

## Dependencies

- `imaplib` (stdlib) — Gmail IMAP
- `email` (stdlib) — email parsing
- `smtplib` (stdlib) — sending email
- `feedparser` — RSS feed parsing
- `beautifulsoup4` — HTML stripping
- `requests` — HTTP for RSS feeds
- `pyyaml` — config parsing
- `jinja2` — HTML email templating
- `filelock` — cross-platform exclusive file locking (Linux + Windows)
- `apify-client` — Apify Python SDK for triggering actors and fetching datasets

---

## Reliability & Fault Tolerance

### Single Delivery Ledger — `state.json`

One file tracks ALL items (newsletters by Message-ID, job intel by canonical URL):

```json
{
  "last_successful_delivery": "2026-04-20T08:05:00Z",
  "items": [
    {"id": "<msg-id-123@gmail>", "type": "newsletter", "state": "delivered", "discovered_at": "..."},
    {"id": "https://example.com/article", "type": "job_intel", "state": "discovered", "discovered_at": "..."}
  ]
}
```

**States:** `discovered` → `delivered`

**Collection phase:**
- Fetch newsletters using lookback window (see Stage 1)
- Fetch job-intel from RSS feeds
- Before adding any item: check `state.json` for matching ID in ANY state (`discovered` or `delivered`) — skip if exists
- Write new items with state `discovered` to `state.json`

**Delivery phase:**
- After successful email send: flip all `discovered` → `delivered` + update `last_successful_delivery` timestamp
- Atomic write: write to temp file, then `os.replace()` (atomic on all OS)

**Crash recovery:**
- Stage 0 (replay) loads all `discovered` items from ledger into current batch before new collection
- Items stuck in `discovered` from crashed prior run are always re-included in next digest
- No data loss: items are tracked from moment of discovery and replayed until delivered

**Pruning rules:**
- Only prune `delivered` items older than 30 days
- Never prune `discovered` items — unsent entries stay in ledger indefinitely until delivered or manually removed
- Even if pipeline is broken for months, unsent items survive (worst case: ~1000 entries after a year, negligible)

**State file integrity:**

1. **Validate before replace:** After writing temp file, read it back and parse JSON. If parse fails → keep old file, log error, abort state update.
2. **Backup on every successful run:** Before writing new state, copy `state.json` → `state.json.bak`. One known-good previous version always on disk.
3. **Startup recovery sequence:**
   - Try loading `state.json` → proceed
   - If corrupt/missing → try `state.json.bak` → proceed with warning
   - If both corrupt/missing → check for bootstrap marker (`data/.initialized`):
     - Marker **MISSING** → first-ever run. Create empty ledger, use `default_lookback_days`, proceed. Create marker after first successful delivery.
     - Marker **EXISTS** → system ran before, state was lost. **FAIL CLOSED**. Log critical error, send alert email (plain text, no LLM — subject: `[CRITICAL] weekly-digest state corrupted, manual recovery needed`), exit non-zero. Operator must manually intervene.
   - Log which recovery path was used

**Guarantees:**
- Missed Sunday → Monday rerun uses `last_successful_delivery` timestamp, catches all newsletters
- Job-intel is best-effort — RSS feeds are snapshots, missed runs may lose articles that aged out of feeds
- Double run → items already in ledger (any state) are skipped during collection
- Crash before send → Stage 0 replay picks up stranded `discovered` items on next run
- Crash after send but before state update → worst case one duplicate digest (acceptable weekly)
- Pipeline down for weeks → unsent `discovered` items never pruned, delivered on next successful run
- State file corruption → automatic fallback to backup; double corruption → fail closed, no silent data loss
- No separate `seen_urls.json` or `newsletter_seen.json` — one ledger, one truth

### Run Coordination — Exclusive File Lock

Uses `filelock` library (cross-platform: Linux + Windows):

```python
from filelock import FileLock, Timeout

lock = FileLock("data/run.lock", timeout=0)  # non-blocking
try:
    with lock:
        # write PID + timestamp metadata to lock file
        # run pipeline
        pass
except Timeout:
    # another instance is running — check if stale
    metadata = read_lock_metadata("data/run.lock")
    if is_process_dead(metadata["pid"]) and lock_age > 30 minutes:
        # stale lock from crashed run — force remove and re-acquire
        lock.acquire(timeout=0)
    else:
        # healthy holder — abort with log message
        log.error("Another instance is running (PID %s). Aborting.", metadata["pid"])
        sys.exit(1)
```

**Stale detection (cross-platform):**
- Linux: `os.kill(pid, 0)` — signal 0 checks if process exists
- Windows: `ctypes.windll.kernel32.OpenProcess()` — check PID validity
- Both: age threshold of 30 minutes as safety net

**Guarantees:**
- Concurrent cron starts → second instance detects live holder, aborts
- Crashed prior run → stale lock detected by dead PID + age, safely reclaimed
- No race conditions → `filelock` uses OS-level exclusive locking

### OpenClaw Fault Tolerance — Per-Item Isolation + Degraded Mode

- **Timeouts:** 60s per summarization request
- **Retries:** 2 retries with exponential backoff per request
- **Item-level chunking:** Each newsletter and each job-intel batch summarized independently. One failure doesn't kill others
- **Input truncation:** If a single newsletter exceeds 4000 chars, truncate before sending to LLM
- **Degraded mode:** If OpenClaw is completely unreachable after 3 connection attempts:
  - Still send digest with extractive summaries — first 200 chars of each newsletter + full headlines for job intel
  - Subject line prefix: `[PARTIAL]` to signal incomplete summarization
- **Per-item fallback:** If one item times out but OpenClaw is otherwise up, that item gets extractive treatment, rest summarized normally

**Guarantees:**
- OpenClaw down → still get useful (rougher) digest
- One huge newsletter → truncated, rest unaffected
- Slow response → times out, extractive fallback, pipeline continues

---

## Non-Goals (Phase 1)

- No web UI or dashboard
- No auto-discovery of newsletter senders (manual config)
- No ML-based relevance scoring (keyword overlap only)
- No Obsidian integration
- No real-time alerts (weekly batch only)

---

## Future Enhancements (Phase 2+)

- Auto-detect newsletter senders from Gmail labels/filters
- Exa API for deeper web search (if free RSS insufficient)
- Obsidian archive of past digests
- Click tracking — which links you actually open, to refine relevance
- WhatsApp content extractor integration (feeds YouTube links into summarizer)
