# Discovery + Jobs Tracker — Design Spec

**Date:** 2026-04-29
**Status:** Approved
**Author:** Sumanth
**Project (current name):** weekly-digest
**Project (target name):** ai-eng-tracker (rename in discrete commit later)

---

## Problem

Current weekly-digest pipeline only surfaces companies that announce funding or hiring in the past 7 days. That misses the actual goal: a target list of AI-first companies in mechanical / structural / composite / aerospace / packaging / hydraulics / CAE sectors, in DE first, EU second, global as reference. Many target companies are small, never make news, but are exactly the relevant employers for an AI-in-engineering job hunt.

The pipeline also has no job-posting collection — only company news. Job postings are the actionable end-goal.

## Goals

1. **Discovery mode (one-shot)**: build a master list of 300-500 companies blending AI/ML with mechanical / structural / composite / aerospace / packaging / hydraulics / CAE / CAD / FEA. Tier by geography (DE deep / EU scan / Global reference).
2. **Jobs mode**: scrape job postings from those companies' careers pages + open job boards, filter for AI-in-engineering roles in DE/EU.
3. **Hand off to VPS**: deliverables are spec + plan files committed to repo. A GPT-5.4 agent on VPS implements. Runtime LLM (Ollama) is qwen3:8b / GLM-4.7 / Minimax-M2.7 (open-source only).

## Non-goals

- Newsletter ingestion stays paused (existing code retained, not invoked).
- Email digest delivery stays paused (no SMTP).
- No Apify (free actor `apify/rss-feed-scraper` doesn't exist; token saved in `.env` for future).
- No LinkedIn scraping (ToS / blocking).
- No funding-round tracking as primary signal. Funding may be one signal among many but not the gate.
- No company de-duplication / merging logic at first run — revisit only if duplicates pile up.
- No automatic re-run cadence yet — script runs by hand. Cadence options listed in "Future modes".

---

## Scope

### Two new pipelines

**A. Discovery script** (`discovery/`)
- Input: keyword tiers (this doc), source list (this doc).
- Output: `data/companies.json` (master list) + tiered markdown reports.
- Runtime: 1.5-2.5 hours per full run (acceptable, runs by hand).
- Idempotent: per-page checkpoint, restart-from-checkpoint on crash.

**B. Jobs script** (`jobs/`)
- Input: `data/companies.json` (companies' careers pages) + open job boards.
- Output: `data/jobs.json` + `data/reports/jobs-DE-EU.md`.
- Runs after discovery, or independently against existing `companies.json`.

### Existing code retained (paused)

`collector/` (newsletter), `summarizer/openclaw.py`, `formatter/`, `sender/`, `state/`, `lock/`, `main.py` — keep on disk. Not invoked by new scripts. Revisit later.

---

## Architecture — Hybrid (Approach C)

```
┌──────────────────────────┐
│  Source list (this doc)  │
└────┬─────────────────────┘
     │
     ├── easy:    custom parsers   (EU-Startups directory, YC list, Berlin AI map, Bayern Innovativ)
     ├── medium:  custom + LLM     (Sifted articles, AI Made in Germany, structured careers pages)
     └── hard:    LLM-driven       (HN, messy blog posts, Google News snippets)
                  ┌─────────────────────────┐
                  │ Ollama format:json call │
                  │ qwen3:8b / GLM-4.7      │
                  │ extract company fields  │
                  └─────────────────────────┘
                            │
     ┌──────────────────────┴──────────────────────┐
     │   Per-source collector                       │
     │   - Fetches list page                        │
     │   - Paginates (per-page checkpoint)          │
     │   - Emits raw company records                │
     └──────────────────────┬──────────────────────┘
                            │
     ┌──────────────────────┴──────────────────────┐
     │   Filter (Tier-1 sector + Tier-2 domain)     │
     │   - English + German keyword variants        │
     │   - Sector match required                    │
     │   - Geography tag (DE / EU / Global)         │
     └──────────────────────┬──────────────────────┘
                            │
     ┌──────────────────────┴──────────────────────┐
     │   companies.json (append-only within run)    │
     │   reports/01-germany.md (deep)               │
     │   reports/02-european-union.md (scan)        │
     │   reports/03-global.md (reference)           │
     └─────────────────────────────────────────────┘
```

Per-source decision tree:
- Source has structured HTML / API → custom parser (BeautifulSoup, requests).
- Source is a blog or messy article → fetch HTML, strip with `defuddle` or `BeautifulSoup`, pass cleaned text to Ollama with `format: json`, parse the JSON response.
- Source is Google News → fetch RSS, pass each item's title + summary to Ollama for company extraction.

---

## Data model

### `data/companies.json` (master list)

JSON array. Append-only within one run. Re-run replaces file (caller may diff old vs new manually).

```json
{
  "name": "string (canonical company name)",
  "homepage": "string (url) | null",
  "country": "string (ISO 3166-1 alpha-2) | null",
  "city": "string | null",
  "geo_tier": "DE | EU | GLOBAL",
  "sectors": ["composite_materials", "structural_mechanics"],
  "ai_focus": "string (1-2 sentences, what AI/ML they do)",
  "stage": "string | null (seed/series-a/public/unknown)",
  "size": "string | null (1-10 / 11-50 / 51-200 / 201+ / unknown)",
  "sources": [
    {"url": "string", "fetched_at": "ISO-8601", "extractor": "custom-eu-startups | llm-ollama | google-news-en | google-news-de"}
  ],
  "last_seen_at": "ISO-8601",
  "notes": "string | null (raw extractor output for human review)"
}
```

### `data/jobs.json`

```json
{
  "id": "sha256(company_name + role + posted_at)",
  "company_name": "string",
  "role_title": "string",
  "role_title_normalized": "string (lowercased, stopwords removed)",
  "is_ai_eng": "boolean (passes Tier-1+Tier-2 filter)",
  "country": "string | null",
  "city": "string | null",
  "remote": "boolean | null",
  "posted_at": "ISO-8601 | null",
  "url": "string",
  "source": "string (careers-page | hn-hiring | stepstone | wellfound | otta)",
  "fetched_at": "ISO-8601"
}
```

### Checkpoint format — `data/checkpoints/<source-name>.json`

```json
{
  "source": "string",
  "started_at": "ISO-8601",
  "last_completed_page": 7,
  "last_completed_url": "string",
  "items_emitted": 142,
  "status": "in_progress | completed | failed",
  "error": "string | null"
}
```

Restart logic: on script start, for each source, read checkpoint. If `status == in_progress`, resume from `last_completed_page + 1`. If `failed`, retry once from same page. If `completed`, skip until forced refresh.

---

## Sources — discovery

Difficulty marks: **EASY** (structured HTML / official directory), **MEDIUM** (semi-structured, mixed content), **HARD** (free-form text, requires LLM extraction).

### Germany (DE)

| Source | URL | Difficulty | Method | Notes |
|---|---|---|---|---|
| Bayern Innovativ company DB | https://www.bayern-innovativ.de/de/netzwerke-und-thinknet | EASY | custom parser | Mech / aerospace cluster |
| Berlin AI Map | https://merantix.com/companies/berlin-ai-map/ | EASY | custom parser | AI startups in Berlin |
| AI Made in Germany | https://ai.bundesnetzagentur.de/ | MEDIUM | custom + LLM fallback | Federal AI registry |
| Plug and Play Munich portfolio | https://www.plugandplaytechcenter.com/munich/ | MEDIUM | custom parser | Mobility + manufacturing focus |
| German startup directory (deutsche-startups.de) | https://www.deutsche-startups.de/startups/ | MEDIUM | custom parser, paginate | Filter sector tags |
| Google News (DE) | https://news.google.com/rss/search?q=KI+Maschinenbau&hl=de&gl=DE | HARD | RSS + LLM extract | Bilingual queries |

### European Union (EU)

| Source | URL | Difficulty | Method | Notes |
|---|---|---|---|---|
| EU-Startups directory | https://www.eu-startups.com/directory/ | EASY | custom parser, paginate | Filter sector |
| Sifted articles | https://sifted.eu/ | HARD | scrape index, defuddle + LLM | AI/deeptech coverage |
| Tech.eu | https://tech.eu/ | MEDIUM | custom + LLM | Funding + company news |
| Google News (EU EN) | https://news.google.com/rss/search?q=AI+engineering+startup+europe&hl=en&gl=GB | HARD | RSS + LLM extract | English query |

### Global reference

| Source | URL | Difficulty | Method | Notes |
|---|---|---|---|---|
| Y Combinator companies (filter: Industrial, Manufacturing, Hardware) | https://www.ycombinator.com/companies | EASY | custom parser, filter tags | Reference tier only |
| Hacker News "Who is hiring" | https://news.ycombinator.com/item?id=<latest-hiring-thread> | HARD | scrape thread, LLM extract per comment | Resolve `<latest-hiring-thread>` at runtime by querying the "Ask HN: Who is hiring?" search; fall back to user-supplied URL if resolution fails |

Sources marked HARD ship behind a feature flag (`config.discovery.enable_hard_sources: false` by default). User reviews easy/medium output first; flips flag if coverage is weak.

---

## Sources — jobs

| Source | URL | Difficulty | Method | Notes |
|---|---|---|---|---|
| Company careers pages | (from `companies.json`) | MEDIUM | custom + LLM fallback | One handler per template; LLM for unknown |
| HN "Who is hiring" | (current month thread) | HARD | scrape thread, LLM extract per comment | DE/EU/remote filter post-extract |
| StepStone | https://www.stepstone.de/ | MEDIUM | custom parser | German job board |
| Wellfound (AngelList) | https://wellfound.com/jobs | MEDIUM | custom parser | Startup-focused |
| Otta | https://app.otta.com/jobs | MEDIUM | custom parser | EU startups |

Out of scope: indeed.de (anti-bot), GreenJobs (low signal for AI-eng).

---

## Keyword tiers (filter)

### Tier-1 — Sector match (REQUIRED)

A company / job qualifies only if at least one Tier-1 keyword matches the source text. EN + DE variants both checked.

**Core (AI × engineering)**
| English | German |
|---|---|
| AI for engineering | KI im Ingenieurwesen |
| machine learning for simulation | maschinelles Lernen Simulation |
| physics-informed machine learning | physik-informiertes maschinelles Lernen |
| AI-driven CAE | KI-gestützte CAE |
| AI for CAD | KI für CAD |
| computational engineering AI | rechnergestützte Konstruktion KI |
| digital twin | digitaler Zwilling |
| generative design | generatives Design |
| topology optimization AI | KI Topologieoptimierung |

**Mechanical / structural**
| English | German |
|---|---|
| structural mechanics | Strukturmechanik |
| structural engineering | Bauingenieurwesen, Tragwerksplanung |
| FEA software | FEM Software |
| finite element analysis | Finite-Elemente-Analyse |
| mechanical reasoning | mechanisches Schließen |
| component design | Bauteilauslegung |
| assembly design | Baugruppenkonstruktion |
| homogenization | Homogenisierung |

**Composites / lightweight / aerospace**
| English | German |
|---|---|
| composite materials | Verbundwerkstoffe, Composites |
| fiber-reinforced composites | faserverstärkte Verbundwerkstoffe |
| CFRP | CFK |
| lightweight structures | Leichtbau, Leichtbaustrukturen |
| aerospace | Luft- und Raumfahrt |
| aircraft structures | Flugzeugstrukturen |

**Manufacturing / industrial**
| English | German |
|---|---|
| injection moulding | Spritzguss |
| plastics engineering | Kunststofftechnik |
| manufacturing AI | KI in der Fertigung |
| industrialization | Industrialisierung |
| production engineering | Produktionstechnik |
| prototype design | Prototypenentwicklung |
| hydraulics | Hydraulik |
| packaging industry | Verpackungsindustrie |

### Tier-2 — Domain post-filter (raises confidence)

Used to score a company once Tier-1 matches. Tier-2 hits boost a "domain confidence" score; below threshold → mark as `notes: "tier-1 only, low confidence"` and let user review.

- physics simulation, CFD, mesh generation
- FEA, FEM, multi-physics
- CAD, CAE, PLM, MBSE
- Ansys, Creo, NX, Solidworks, Abaqus, COMSOL, OpenFOAM, Simcenter
- generative AI for design, neural surrogate, surrogate model
- materials informatics, materials genomics

### Tier-3 — Tool tags (informational, not a filter gate)

Recorded if mentioned. Used to enrich `notes` field. Examples: `Ansys`, `Creo`, `NX`, `Solidworks`, `Abaqus`, `COMSOL`, `OpenFOAM`, `Simcenter`, `MATLAB`, `PyTorch`, `JAX`, `TensorFlow`.

### Bilingual scraping rule

For every Google News query, fire two requests:
- `hl=en&gl=US` (or `gl=GB` for EU) — English keyword
- `hl=de&gl=DE` — German keyword

For careers pages on `.de` domains, prefer German keyword match before English.

---

## Output

### `data/reports/01-germany.md` — DEEP tier

Per-company entry: name, homepage, city, sectors (tags), AI focus (1-2 sentences), stage/size if known, source URLs, "why relevant" line, "open roles" link if jobs scraper ran. ~30-50 entries expected.

### `data/reports/02-european-union.md` — SCAN tier

Compact table: name | country | sectors | homepage | source. ~100-200 entries.

### `data/reports/03-global.md` — REFERENCE tier

Bulleted list, ~150-300 entries. Just name + sector + URL. User skims for inspiration.

### `data/reports/jobs-DE-EU.md` — JOBS tier

Table: company | role | location | remote | posted | url | source. Filtered to DE/EU only, AI-eng roles.

### Output language

English. Preserve German technical terms verbatim (e.g., "Leichtbau", "Tragwerksplanung", "Verbundwerkstoffe") — do not translate.

---

## Error handling & resilience

- **Per-page checkpoint** (option B from brainstorm). Each source writes checkpoint after every page (~25 companies).
- **Crash recovery**: on restart, read checkpoint, resume from `last_completed_page + 1`.
- **Network errors**: retry 3x with exponential backoff (2s, 4s, 8s). Then mark source `failed`, continue to next source.
- **LLM extraction failures**: if Ollama returns invalid JSON, retry once with stricter prompt. If still bad, log raw text to `notes`, mark `extractor: "llm-failed"`, continue.
- **Rate limits**: 2-second delay between RSS / page fetches. Per-domain politeness.
- **No silent failures**: every source logs `started`, `pages_completed`, `items_emitted`, `status`, `error`.

---

## Configuration

Add to `config.yaml`:

```yaml
discovery:
  enable_hard_sources: false
  max_companies_total: 600           # safety cap; truncate beyond
  rss_delay_seconds: 2
  per_source_timeout_seconds: 1800   # 30 min per source
  checkpoint_dir: "data/checkpoints"
  output_dir: "data/reports"
  companies_file: "data/companies.json"
  ollama_extractor:
    model: "qwen3:8b"                # configurable: GLM-4.7, Minimax-M2.7
    format: "json"
    timeout_seconds: 90
    max_retries: 1
  sources:
    eu_startups: { enabled: true, max_pages: 50 }
    yc_companies: { enabled: true, tags: ["industrial", "manufacturing", "hardware"] }
    berlin_ai_map: { enabled: true }
    bayern_innovativ: { enabled: true }
    deutsche_startups: { enabled: true, max_pages: 30 }
    plug_and_play_munich: { enabled: true }
    sifted: { enabled: false }       # HARD
    tech_eu: { enabled: true }
    ai_made_in_germany: { enabled: true }
    google_news_de: { enabled: false }    # HARD
    google_news_en: { enabled: false }    # HARD
    hn_who_is_hiring: { enabled: false }  # HARD

jobs:
  enabled: true
  output_file: "data/jobs.json"
  report_file: "data/reports/jobs-DE-EU.md"
  geo_filter: ["DE", "AT", "CH", "NL", "FR", "ES", "IT", "PL", "SE", "DK", "FI", "NO", "BE", "IE", "PT", "CZ"]
  sources:
    careers_pages: { enabled: true }
    hn_hiring: { enabled: false }    # HARD
    stepstone: { enabled: true }
    wellfound: { enabled: true }
    otta: { enabled: true }
```

---

## Future modes (suggest, do not implement)

User runs script by hand for now. Possible future cadences (to revisit later):

1. **Monthly cron** — full discovery rerun, diff against last month's `companies.json`, email new entries.
2. **Quarterly cron + weekly jobs** — discovery quarterly (slow-changing), jobs weekly.
3. **Triggered rerun** — user kicks off via CLI flag when they want a fresh batch.

Manual review queue: user reviews `notes: "tier-1 only, low confidence"` entries by hand. No automated reviewer.

---

## Renaming

`weekly-digest` → `ai-eng-tracker`. Defer to discrete commit after spec + plan land. Touches: repo name on GitHub, `pyproject.toml` (if added later), `README.md` heading, no source code paths.

---

## Open / deferred items

- Repo rename — discrete commit, post-spec.
- Newsletter side — paused indefinitely.
- Apify — paused. Token in `.env` for future.
- Company merge / dedupe — only revisit if duplicates pile up across sources.
- Cadence automation — manual for now.
- HN-hiring monthly thread URL — resolved at runtime.

---

## Acceptance criteria

1. Running `python -m discovery.run` with default config produces `data/companies.json` with ≥ 200 entries within 2.5 hours, no uncaught exceptions, all enabled sources reach `status: completed` or explicit `failed`.
2. `data/reports/01-germany.md` has ≥ 20 DE entries, each with homepage + at least one sector tag.
3. Crash mid-run, restart with same command → resumes from last checkpoint, does not redo completed sources, final output identical (modulo time-dependent fields).
4. Running `python -m jobs.run` against existing `companies.json` produces `data/jobs.json` with ≥ 30 DE/EU AI-eng roles.
5. All filters use both EN and DE keywords for `.de` and DE Google News sources.
6. Logs show per-source: `started_at`, `pages_completed`, `items_emitted`, `status`.
