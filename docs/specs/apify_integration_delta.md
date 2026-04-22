# Newsletter Weekly Digest — Apify Integration Delta

**Date:** 2026-04-22
**Status:** SUPERSEDED — Apify integration has been merged into the main design spec (`2026-04-20-newsletter-weekly-digest-design.md`) with auto-fallback to RSS. This doc is kept as historical reference only. The main spec is the source of truth.
**Author:** Sumanth & Perplexity AI

*Note: This document only outlines the architectural and code changes required to integrate the Apify platform into your existing 2026-04-20 design spec. All other stages (Newsletters, Summarizer, Formatter) remain identical. You can feed this directly to another AI agent to update your code.*

---

## Architecture (Delta)

*Change: Offload the scraping layer to Apify's cloud. The local Python script now acts as an API client rather than performing the raw HTTP requests and HTML parsing for job intel.*

```
┌─────────────┐     ┌──────────────┐     ┌───────────┐     ┌────────────┐
│ Gmail IMAP  │────>│              │────>│           │────>│            │
│(newsletters)│     │   Collector  │     │ Summarizer│     │  Formatter │──> Email
│             │     │  (Python)    │     │ (OpenClaw)│     │  (HTML)    │
│ Apify Cloud │────>│              │────>│           │────>│            │
│ (Actors/API)│     │              │     │           │     │            │
└─────────────┘     └──────────────┘     └───────────┘     └────────────┘
```

---

## Stage 2: Collector — Job Intel Scraping (Revised)

Instead of maintaining `feedparser` and managing IP blocks locally, `collector/job_intel.py` will use the official `apify-client` to trigger scraping jobs.

### Workflow Changes
1. **Trigger Actor:** The script calls the Apify API using your `$APIFY_API_TOKEN` to start a pre-built Actor (e.g., an RSS Extractor or Article Extractor).
2. **Pass Inputs:** Pass the search query combinations (Sectors × Signals) as the `run_input` JSON to the Actor.
3. **Synchronous Wait:** Since your script runs weekly on a cron job, it can synchronously wait for the Apify Actor to finish using `client.actor('actor_id').call(run_input=...)`.
4. **Fetch Dataset:** Once the run completes, fetch the resulting items directly from the run's default dataset and pass them to OpenClaw.

### Deduplication
- Apify handles URL deduplication within the scrape itself.
- Your local `state.json` remains the absolute source of truth for *delivery*. You will filter Apify's returned dataset against `state.json` before passing the items to Stage 3 to ensure you don't send duplicate emails.

---

## Configuration (config.yaml Additions)

Add an `apify` block to your YAML. The API token must be loaded from environment variables to keep it secure, exactly like your Gmail App Password.

```yaml
apify:
  api_token: "${APIFY_API_TOKEN}"
  job_scraper_actor_id: "apify/rss-feed-scraper" # or a specific article extractor
  timeout_secs: 600 # 10-minute max wait for scraping to finish
```

---

## Dependencies (Delta)

**Additions:**
- `apify-client` — Official Python SDK to trigger runs and fetch datasets.

**Removals/Changes:**
- `feedparser` — (Remove) Apify handles RSS.
- `requests` — (Keep for OpenClaw API if not using a specific LLM client, but no longer needed for RSS fetching).
- `beautifulsoup4` — (Keep ONLY for Stage 1 Gmail HTML stripping; no longer needed for web scraping).

---

## Project Structure (Delta)

```text
weekly-digest/
├── collector/
│   ├── newsletters.py
│   └── job_intel.py     # REWRITTEN: Now imports apify_client, triggers Actor, returns dataset
```

### Code Snippet Example for `job_intel.py`
```python
from apify_client import ApifyClient

def fetch_job_intel(api_token, actor_id, search_queries):
    client = ApifyClient(api_token)

    # Start the actor and wait for it to finish
    run = client.actor(actor_id).call(run_input={"search_queries": search_queries})

    # Fetch the results from the dataset
    return list(client.dataset(run["defaultDatasetId"]).iterate_items())
```
