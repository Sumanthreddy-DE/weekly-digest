# Implementation Plan — Discovery + Jobs Tracker

**Date:** 2026-04-29
**Spec:** `docs/superpowers/specs/2026-04-29-discovery-and-jobs-design.md`
**Target implementer:** GPT-5.4 agent on VPS
**Runtime LLM:** qwen3:8b / GLM-4.7 / Minimax-M2.7 via Ollama-compatible endpoint at `OPENCLAW_BASE_URL`

This plan is granular (option C). Every module includes file path, public functions, signatures, pseudocode for non-trivial logic, and matching tests.

---

## Phase 0 — Repo prep (single commit)

### 0.1 Directory layout

```
discovery/
  __init__.py
  run.py                    # entrypoint
  config_loader.py          # reads config.yaml + .env, validates discovery section
  filters.py                # tier-1 / tier-2 / tier-3 keyword logic
  models.py                 # Company, Job, Checkpoint dataclasses
  ollama_extractor.py       # format:json LLM extractor wrapper
  reporter.py               # writes reports/*.md
  sources/
    __init__.py
    base.py                 # SourceBase abstract class
    eu_startups.py
    yc_companies.py
    berlin_ai_map.py
    bayern_innovativ.py
    deutsche_startups.py
    plug_and_play_munich.py
    ai_made_in_germany.py
    tech_eu.py
    sifted.py
    google_news.py
    hn_hiring.py
jobs/
  __init__.py
  run.py
  models.py
  filters.py
  sources/
    __init__.py
    base.py
    careers_page.py
    hn_hiring.py
    stepstone.py
    wellfound.py
    otta.py
data/
  reports/                  # gitignored
  checkpoints/              # gitignored
tests/
  discovery/
    test_filters.py
    test_models.py
    test_ollama_extractor.py
    test_checkpoint.py
    test_eu_startups.py
    test_google_news.py
    test_reporter.py
  jobs/
    test_filters.py
    test_careers_page.py
    test_stepstone.py
```

### 0.2 Update `.gitignore`

Add: `data/reports/`, `data/checkpoints/`, `data/companies.json`, `data/jobs.json`.

### 0.3 Update `requirements.txt`

Add (pin minor versions):
- `httpx>=0.27,<0.28` — async-capable HTTP
- `tenacity>=8.2,<9` — retry decorators
- `lxml>=5.1` — fast HTML parser for BeautifulSoup
- (already present): `requests`, `beautifulsoup4`, `feedparser`, `jinja2`, `pyyaml`, `python-dotenv`, `filelock`

### 0.4 Extend `config.yaml`

Append `discovery:` and `jobs:` sections per spec § Configuration.

### 0.5 Test runner

`pytest -q` should still pass existing 43 tests. New tests added in later phases.

**Acceptance:** `pytest -q` green; `python -c "import discovery, jobs"` succeeds.

---

## Phase 1 — Models + checkpoint + config

### 1.1 `discovery/models.py`

```python
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Literal, Optional

GeoTier = Literal["DE", "EU", "GLOBAL"]
SourceExtractor = Literal[
    "custom-eu-startups", "custom-yc", "custom-berlin-ai", "custom-bayern",
    "custom-deutsche-startups", "custom-plug-and-play", "custom-ai-made-de",
    "custom-tech-eu", "llm-ollama", "google-news-en", "google-news-de",
    "llm-failed",
]

@dataclass
class SourceRef:
    url: str
    fetched_at: str           # ISO-8601
    extractor: SourceExtractor

@dataclass
class Company:
    name: str
    homepage: Optional[str]
    country: Optional[str]    # ISO-3166-1 alpha-2
    city: Optional[str]
    geo_tier: GeoTier
    sectors: list[str]
    ai_focus: str
    stage: Optional[str]
    size: Optional[str]
    sources: list[SourceRef]
    last_seen_at: str
    notes: Optional[str] = None

    def to_json(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_json(d: dict) -> "Company":
        d = dict(d)
        d["sources"] = [SourceRef(**s) for s in d.get("sources", [])]
        return Company(**d)
```

### 1.2 `discovery/checkpoint.py`

```python
from pathlib import Path
import json, tempfile, os
from dataclasses import dataclass, asdict
from typing import Optional

@dataclass
class Checkpoint:
    source: str
    started_at: str
    last_completed_page: int
    last_completed_url: Optional[str]
    items_emitted: int
    status: str               # in_progress | completed | failed
    error: Optional[str] = None

def checkpoint_path(checkpoint_dir: str, source: str) -> Path:
    return Path(checkpoint_dir) / f"{source}.json"

def read(checkpoint_dir: str, source: str) -> Optional[Checkpoint]:
    p = checkpoint_path(checkpoint_dir, source)
    if not p.exists():
        return None
    return Checkpoint(**json.loads(p.read_text()))

def write(checkpoint_dir: str, cp: Checkpoint) -> None:
    p = checkpoint_path(checkpoint_dir, cp.source)
    p.parent.mkdir(parents=True, exist_ok=True)
    # atomic: tmp file then rename
    fd, tmp = tempfile.mkstemp(dir=p.parent, prefix=p.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(asdict(cp), f, indent=2)
        os.replace(tmp, p)
    except Exception:
        if Path(tmp).exists():
            Path(tmp).unlink()
        raise
```

### 1.3 `discovery/config_loader.py`

Reuses existing `state/config.py` env-var expansion. Adds:

```python
def load_discovery_config(path: str = "config.yaml") -> dict:
    cfg = load_config(path)         # existing helper
    if "discovery" not in cfg:
        raise ValueError("config.yaml missing 'discovery' section")
    if "jobs" not in cfg:
        raise ValueError("config.yaml missing 'jobs' section")
    return cfg
```

### 1.4 Tests

**`tests/discovery/test_models.py`**
- `test_company_to_from_json_roundtrip` — build Company, dump, reload, assert equal.
- `test_company_rejects_invalid_geo_tier` — pass `geo_tier="INVALID"`, expect TypeError or ValueError (Literal enforced via runtime check; if not enforced by dataclass alone, add validation in `__post_init__`).

**`tests/discovery/test_checkpoint.py`**
- `test_checkpoint_write_then_read` — write, read, assert equality.
- `test_checkpoint_atomic_no_partial` — simulate write failure mid-flight (mock `os.replace` to raise), assert no `.tmp` left and original file untouched.
- `test_checkpoint_missing_returns_none` — `read()` on absent source returns None.

**Acceptance:** all phase-1 tests green.

---

## Phase 2 — Filters (Tier-1 / Tier-2 / Tier-3)

### 2.1 `discovery/filters.py`

```python
from dataclasses import dataclass

# Loaded from config.yaml at import time? No — pass via function args for testability.

@dataclass
class FilterResult:
    passes_tier1: bool
    matched_tier1: list[str]      # which keywords hit
    tier2_score: int              # count of tier-2 matches
    tier3_tools: list[str]        # which tools mentioned
    confidence: str               # "high" | "low"

TIER1_EN_DE = {
    "ai_engineering": ["AI for engineering", "KI im Ingenieurwesen"],
    "ml_simulation": ["machine learning for simulation", "maschinelles Lernen Simulation"],
    "physics_informed_ml": ["physics-informed machine learning", "physik-informiertes maschinelles Lernen"],
    "ai_cae": ["AI-driven CAE", "KI-gestützte CAE", "AI for CAE"],
    "ai_cad": ["AI for CAD", "KI für CAD"],
    "computational_engineering_ai": ["computational engineering AI", "rechnergestützte Konstruktion KI"],
    "digital_twin": ["digital twin", "digitaler Zwilling"],
    "generative_design": ["generative design", "generatives Design"],
    "topology_opt_ai": ["topology optimization AI", "KI Topologieoptimierung"],
    "structural_mechanics": ["structural mechanics", "Strukturmechanik"],
    "structural_engineering": ["structural engineering", "Bauingenieurwesen", "Tragwerksplanung"],
    "fea_software": ["FEA software", "FEM Software"],
    "finite_element": ["finite element analysis", "Finite-Elemente-Analyse"],
    "mechanical_reasoning": ["mechanical reasoning", "mechanisches Schließen"],
    "component_design": ["component design", "Bauteilauslegung"],
    "assembly_design": ["assembly design", "Baugruppenkonstruktion"],
    "homogenization": ["homogenization", "Homogenisierung"],
    "composite_materials": ["composite materials", "Verbundwerkstoffe", "Composites"],
    "fiber_composites": ["fiber-reinforced composites", "faserverstärkte Verbundwerkstoffe", "CFRP", "CFK"],
    "lightweight": ["lightweight structures", "Leichtbau", "Leichtbaustrukturen"],
    "aerospace": ["aerospace", "Luft- und Raumfahrt"],
    "aircraft_structures": ["aircraft structures", "Flugzeugstrukturen"],
    "injection_moulding": ["injection moulding", "Spritzguss"],
    "plastics_engineering": ["plastics engineering", "Kunststofftechnik"],
    "manufacturing_ai": ["manufacturing AI", "KI in der Fertigung"],
    "industrialization": ["industrialization", "Industrialisierung"],
    "production_engineering": ["production engineering", "Produktionstechnik"],
    "prototype_design": ["prototype design", "Prototypenentwicklung"],
    "hydraulics": ["hydraulics", "Hydraulik"],
    "packaging": ["packaging industry", "Verpackungsindustrie"],
}

TIER2 = [
    "physics simulation", "CFD", "mesh generation",
    "FEA", "FEM", "multi-physics",
    "CAD", "CAE", "PLM", "MBSE",
    "Ansys", "Creo", "NX", "Solidworks", "Abaqus", "COMSOL", "OpenFOAM", "Simcenter",
    "generative AI for design", "neural surrogate", "surrogate model",
    "materials informatics", "materials genomics",
]

TIER3_TOOLS = [
    "Ansys", "Creo", "NX", "Solidworks", "Abaqus", "COMSOL", "OpenFOAM",
    "Simcenter", "MATLAB", "PyTorch", "JAX", "TensorFlow",
]

CONFIDENCE_THRESHOLD = 1   # >=1 tier-2 hit → high confidence

def evaluate(text: str) -> FilterResult:
    """Case-insensitive substring search. Text should be company description + sources."""
    haystack = text.lower()
    matched = []
    for key, variants in TIER1_EN_DE.items():
        if any(v.lower() in haystack for v in variants):
            matched.append(key)
    tier2_hits = sum(1 for kw in TIER2 if kw.lower() in haystack)
    tools = [t for t in TIER3_TOOLS if t.lower() in haystack]
    return FilterResult(
        passes_tier1=bool(matched),
        matched_tier1=matched,
        tier2_score=tier2_hits,
        tier3_tools=tools,
        confidence="high" if tier2_hits >= CONFIDENCE_THRESHOLD else "low",
    )
```

### 2.2 Tests — `tests/discovery/test_filters.py`

- `test_tier1_english_match` — text contains "AI for engineering" → passes_tier1, matched includes `ai_engineering`.
- `test_tier1_german_match` — text contains "Verbundwerkstoffe" → passes_tier1, matched includes `composite_materials`.
- `test_tier1_no_match` — text "we sell shoes" → not passes_tier1.
- `test_tier2_score` — text with "Ansys" + "CFD" → tier2_score=2 (note: "Ansys" also in tier-3 tools).
- `test_tier3_tool_extraction` — text with "we use PyTorch and Abaqus" → tier3_tools = ["Abaqus", "PyTorch"] (any order; assert as set).
- `test_confidence_low_when_no_tier2` — tier1 hit, no tier2 → confidence="low".
- `test_confidence_high_when_tier2_present` — tier1+tier2 → "high".
- `test_case_insensitive` — "VERBUNDWERKSTOFFE" matches.

**Acceptance:** all phase-2 tests green.

---

## Phase 3 — Ollama extractor

### 3.1 `discovery/ollama_extractor.py`

```python
import json, logging
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

log = logging.getLogger(__name__)

EXTRACT_PROMPT = """You are a data extraction tool. Given the text below, extract any companies that blend AI/ML with mechanical, structural, composite, aerospace, packaging, hydraulics, CAE, CAD, or FEA.

Return STRICT JSON, no prose. Schema:
{
  "companies": [
    {
      "name": "string",
      "homepage": "string or null",
      "country": "ISO 3166-1 alpha-2 or null",
      "city": "string or null",
      "ai_focus": "string (1-2 sentences)",
      "sectors": ["list of sector tags"]
    }
  ]
}

If no companies found, return {"companies": []}.

TEXT:
"""

class OllamaExtractError(Exception):
    pass

@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=2, min=2, max=8),
    retry=retry_if_exception_type((requests.exceptions.RequestException, OllamaExtractError)),
)
def _call_ollama(base_url: str, model: str, prompt: str, timeout: int) -> str:
    url = f"{base_url}/api/generate"
    r = requests.post(
        url,
        json={"model": model, "prompt": prompt, "format": "json", "stream": False},
        timeout=timeout,
    )
    r.raise_for_status()
    return r.json().get("response", "")

def extract_companies(text: str, config: dict) -> list[dict]:
    """Returns list of dicts matching schema in EXTRACT_PROMPT, or [] on failure."""
    cfg = config["discovery"]["ollama_extractor"]
    base_url = config["openclaw"]["base_url"]
    prompt = EXTRACT_PROMPT + text[:8000]    # cap input
    try:
        raw = _call_ollama(base_url, cfg["model"], prompt, cfg["timeout_seconds"])
        parsed = json.loads(raw)
        return parsed.get("companies", [])
    except json.JSONDecodeError as e:
        log.warning("Ollama returned invalid JSON: %s", e)
        return []
    except Exception as e:
        log.warning("Ollama extract failed: %s", e)
        return []
```

### 3.2 Tests — `tests/discovery/test_ollama_extractor.py`

Mock `requests.post` with `unittest.mock.patch`. Provide fake responses.

- `test_extract_valid_json` — mock returns `{"response": "{\"companies\": [{\"name\": \"FooCo\", ...}]}"}` → returns one company.
- `test_extract_invalid_json_returns_empty` — mock returns `{"response": "not json"}` → returns [].
- `test_extract_network_error_retries_then_fails` — mock raises ConnectionError twice → returns [] after exhausting retries.
- `test_extract_truncates_long_input` — text > 8000 chars, assert prompt sent ≤ 8000 + prefix.
- `test_extract_uses_format_json_flag` — assert `format: "json"` is in posted body.

**Acceptance:** all phase-3 tests green.

---

## Phase 4 — Source base + first source (EU-Startups, EASY)

### 4.1 `discovery/sources/base.py`

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterator
from datetime import datetime
from discovery.models import Company
from discovery.checkpoint import Checkpoint, read as cp_read, write as cp_write

class SourceBase(ABC):
    name: str = ""
    geo_tier: str = "GLOBAL"
    extractor: str = "custom"

    def __init__(self, config: dict):
        self.config = config
        self.checkpoint_dir = config["discovery"]["checkpoint_dir"]
        self.rss_delay = config["discovery"]["rss_delay_seconds"]

    @abstractmethod
    def iter_pages(self, start_page: int) -> Iterator[tuple[int, list[Company]]]:
        """Yield (page_number, list_of_companies). Implementations handle their own HTTP + parsing."""

    def run(self) -> tuple[int, str]:
        """Run with checkpoint resume. Returns (items_emitted, status)."""
        cp = cp_read(self.checkpoint_dir, self.name)
        start_page = (cp.last_completed_page + 1) if (cp and cp.status == "in_progress") else 1
        if cp and cp.status == "completed":
            return cp.items_emitted, "completed"
        items = cp.items_emitted if cp else 0
        try:
            for page_num, companies in self.iter_pages(start_page):
                items += len(companies)
                # caller writes to companies.json; here we just checkpoint
                cp_write(self.checkpoint_dir, Checkpoint(
                    source=self.name,
                    started_at=cp.started_at if cp else datetime.utcnow().isoformat(),
                    last_completed_page=page_num,
                    last_completed_url=None,
                    items_emitted=items,
                    status="in_progress",
                ))
                yield from companies     # caller iterates run()
            cp_write(self.checkpoint_dir, Checkpoint(
                source=self.name,
                started_at=cp.started_at if cp else datetime.utcnow().isoformat(),
                last_completed_page=page_num,
                last_completed_url=None,
                items_emitted=items,
                status="completed",
            ))
            return items, "completed"
        except Exception as e:
            cp_write(self.checkpoint_dir, Checkpoint(
                source=self.name,
                started_at=cp.started_at if cp else datetime.utcnow().isoformat(),
                last_completed_page=page_num if "page_num" in dir() else 0,
                last_completed_url=None,
                items_emitted=items,
                status="failed",
                error=str(e),
            ))
            return items, "failed"
```

NOTE for implementer: above `run()` mixes generator and tuple-return — refactor to a clean iterator that yields companies and writes checkpoint on each page. Use a context-manager pattern. The pseudocode shows intent; implementer picks the cleanest Python idiom.

### 4.2 `discovery/sources/eu_startups.py`

EU-Startups directory: https://www.eu-startups.com/directory/

Page structure (verify at impl time):
- Listing pages: `?_page=N`
- Each card: company name, country, sector tag, website link, short description.
- Likely 50+ pages, 24 entries per page.

```python
from .base import SourceBase
from discovery.models import Company, SourceRef
from datetime import datetime
import requests, time
from bs4 import BeautifulSoup

class EUStartupsSource(SourceBase):
    name = "eu_startups"
    geo_tier = "EU"
    extractor = "custom-eu-startups"
    BASE = "https://www.eu-startups.com/directory/"

    def iter_pages(self, start_page: int):
        max_pages = self.config["discovery"]["sources"]["eu_startups"]["max_pages"]
        for page_num in range(start_page, max_pages + 1):
            url = f"{self.BASE}?_page={page_num}"
            r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0 ai-eng-tracker/0.1"})
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "lxml")
            cards = soup.select("div.directory-listing-item")     # verify selector at impl
            if not cards:
                return
            companies = []
            now = datetime.utcnow().isoformat()
            for card in cards:
                name = card.select_one(".company-name").get_text(strip=True)
                website = card.select_one("a.website-link")
                homepage = website["href"] if website else None
                country = card.select_one(".country").get_text(strip=True) if card.select_one(".country") else None
                sector_tags = [t.get_text(strip=True) for t in card.select(".sector-tag")]
                description = card.select_one(".description").get_text(strip=True) if card.select_one(".description") else ""
                companies.append(Company(
                    name=name,
                    homepage=homepage,
                    country=self._iso_country(country),
                    city=None,
                    geo_tier="DE" if country == "Germany" else "EU",
                    sectors=sector_tags,
                    ai_focus=description,
                    stage=None, size=None,
                    sources=[SourceRef(url=url, fetched_at=now, extractor=self.extractor)],
                    last_seen_at=now,
                    notes=None,
                ))
            yield page_num, companies
            time.sleep(self.rss_delay)

    @staticmethod
    def _iso_country(name: str | None) -> str | None:
        # small map; expand at impl time
        m = {"Germany": "DE", "France": "FR", "Spain": "ES", ...}
        return m.get(name) if name else None
```

### 4.3 Tests — `tests/discovery/test_eu_startups.py`

- `test_parse_listing_page` — feed fixture HTML (`tests/fixtures/eu_startups_page1.html`), assert 24 companies parsed, each has name + homepage.
- `test_iso_country_mapping` — known countries map; unknown → None.
- `test_pagination_stops_when_no_cards` — fixture with 0 cards → iter_pages stops.
- `test_checkpoint_resume` — write checkpoint with `last_completed_page=3, status=in_progress`, run with mocked HTTP for pages 4-5, assert HTTP only called for 4 and 5.

**Acceptance:** EUStartups produces ≥ 50 EU companies in dry-run against live site (manual smoke test, not CI).

---

## Phase 5 — Remaining EASY/MEDIUM sources

For each: same structure as EU-Startups. Implementer follows pattern. Plan lists the per-source verification steps.

### 5.1 `yc_companies.py`
- URL: `https://www.ycombinator.com/companies?industry=Industrials,Hardware,Manufacturing`
- API: YC has a JSON endpoint at the same URL with `?format=json` (verify); else parse HTML.
- Filter: only companies whose `industry` includes Industrial / Manufacturing / Hardware tags AND whose description matches Tier-1.
- `geo_tier = "GLOBAL"` (most YC are US).

### 5.2 `berlin_ai_map.py`
- URL: `https://merantix.com/companies/berlin-ai-map/`
- Single page; parse all entries. Each entry: name, homepage, AI focus.
- `geo_tier = "DE"`.

### 5.3 `bayern_innovativ.py`
- URL: cluster-listing page (verify exact URL at impl). May require JS render — if so, fall back to LLM extraction on rendered HTML via `defuddle`.
- Filter: members tagged Mechatronik / Luft- und Raumfahrt / Composites.
- `geo_tier = "DE"`.

### 5.4 `deutsche_startups.py`
- URL: `https://www.deutsche-startups.de/startups/`
- Paginate via `?paged=N`.
- Filter sector tag in {"Industrie", "MaschinenBau", "Mobilität", "Hardware"}.
- `geo_tier = "DE"`.

### 5.5 `plug_and_play_munich.py`
- URL: `https://www.plugandplaytechcenter.com/munich/portfolio/`
- Single or few pages.
- `geo_tier = "DE"`.

### 5.6 `ai_made_in_germany.py`
- URL: `https://ai.bundesnetzagentur.de/`
- May be a registry with downloadable CSV/JSON. Prefer official export over scrape.
- `geo_tier = "DE"`.

### 5.7 `tech_eu.py`
- URL: `https://tech.eu/category/`
- Index-style; per-article LLM extract.
- `geo_tier = "EU"`.

### Tests per source

Each source gets at least:
- `test_parse_<source>_page` — fixture HTML → expected companies parsed.
- `test_<source>_filter_applied` — entries that don't match Tier-1 are dropped post-filter.

Fixtures saved under `tests/fixtures/<source>/` as captured `.html` files (anonymise where appropriate).

**Acceptance:** all EASY/MEDIUM sources can run independently and produce non-empty output.

---

## Phase 6 — HARD sources (behind feature flag)

### 6.1 `google_news.py`

```python
class GoogleNewsSource(SourceBase):
    name_de = "google_news_de"
    name_en = "google_news_en"
    extractor = "google-news-de"  # or -en

    QUERIES_DE = [
        "KI Maschinenbau", "KI Strukturmechanik", "KI Verbundwerkstoffe",
        "KI Leichtbau", "KI Luft- und Raumfahrt", "digitaler Zwilling",
        "KI in der Fertigung", "physik-informiertes maschinelles Lernen",
        # ... full list from spec
    ]
    QUERIES_EN = [
        "AI mechanical engineering startup", "AI for CAE",
        "physics-informed machine learning startup", "AI composite materials",
        # ... full list from spec
    ]

    def iter_pages(self, start_page):
        queries = self.QUERIES_DE if self.geo == "DE" else self.QUERIES_EN
        hl = "de" if self.geo == "DE" else "en"
        gl = "DE" if self.geo == "DE" else "GB"
        for i, q in enumerate(queries[start_page-1:], start=start_page):
            url = f"https://news.google.com/rss/search?q={urlencode_q(q)}&hl={hl}&gl={gl}"
            feed = feedparser.parse(url)
            companies = []
            for entry in feed.entries[:20]:
                text = f"{entry.title}. {entry.summary}"
                # LLM extract
                extracted = ollama_extractor.extract_companies(text, self.config)
                for c in extracted:
                    companies.append(self._to_company(c, entry.link, q))
            yield i, companies
            time.sleep(self.rss_delay)
```

### 6.2 `hn_hiring.py`

- Resolve current "Ask HN: Who is hiring?" thread by hitting `https://hn.algolia.com/api/v1/search?query=Ask+HN+Who+is+hiring&tags=story` and picking newest.
- Fetch thread comments via Algolia API.
- Per comment, run `ollama_extractor.extract_companies` on text.
- Skip comments that don't pass Tier-1 filter post-extraction.
- `extractor = "llm-ollama"`.

### 6.3 `sifted.py`

- Crawl index page, fetch each article URL, defuddle to clean text, LLM extract.
- Slow; behind flag.

### 6.4 Tests

- `test_google_news_de_query_url` — assert URL contains `hl=de&gl=DE` for DE source.
- `test_google_news_en_query_url` — assert URL contains `hl=en&gl=GB` for EU source.
- `test_hn_hiring_resolves_latest_thread` — mock Algolia API, assert latest thread URL picked.
- `test_hard_sources_disabled_by_default` — load default config, assert `enable_hard_sources = false`, `run.py` skips them.

**Acceptance:** HARD sources off by default; flipping flag runs them; output non-empty for at least one HARD source on smoke test.

---

## Phase 7 — Reporter (markdown reports)

### 7.1 `discovery/reporter.py`

```python
def write_reports(companies: list[Company], output_dir: str) -> None:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    de = [c for c in companies if c.geo_tier == "DE"]
    eu = [c for c in companies if c.geo_tier == "EU"]
    glob = [c for c in companies if c.geo_tier == "GLOBAL"]
    _write_de_deep(de, Path(output_dir) / "01-germany.md")
    _write_eu_scan(eu, Path(output_dir) / "02-european-union.md")
    _write_global_ref(glob, Path(output_dir) / "03-global.md")

def _write_de_deep(companies, path):
    """Per-company section: ## Name\n- homepage\n- city\n- sectors\n- ai_focus\n- sources"""
    lines = ["# Germany — Deep Tier", ""]
    for c in companies:
        lines.append(f"## {c.name}")
        lines.append(f"- **Homepage**: {c.homepage or 'unknown'}")
        lines.append(f"- **City**: {c.city or 'unknown'}")
        lines.append(f"- **Sectors**: {', '.join(c.sectors) or 'unknown'}")
        lines.append(f"- **AI focus**: {c.ai_focus}")
        lines.append(f"- **Sources**: " + ", ".join(s.url for s in c.sources))
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")

def _write_eu_scan(companies, path):
    """Compact table: name | country | sectors | homepage | source"""
    lines = ["# European Union — Scan Tier", "",
             "| Name | Country | Sectors | Homepage | Source |",
             "|---|---|---|---|---|"]
    for c in companies:
        sectors = ", ".join(c.sectors[:3]) or "-"
        src = c.sources[0].url if c.sources else "-"
        lines.append(f"| {c.name} | {c.country or '-'} | {sectors} | {c.homepage or '-'} | {src} |")
    path.write_text("\n".join(lines), encoding="utf-8")

def _write_global_ref(companies, path):
    """Bulleted list."""
    lines = ["# Global — Reference Tier", ""]
    for c in companies:
        sectors = ", ".join(c.sectors[:2]) or "-"
        lines.append(f"- **{c.name}** ({sectors}) — {c.homepage or 'unknown'}")
    path.write_text("\n".join(lines), encoding="utf-8")
```

### 7.2 Tests — `tests/discovery/test_reporter.py`

- `test_write_reports_creates_three_files` — pass mixed list, assert all three .md files exist.
- `test_de_deep_format` — load 01-germany.md, assert each Company has its `## Name` heading + homepage line.
- `test_eu_scan_table_header` — file contains markdown table header.
- `test_global_ref_bullet_format` — each line starts with `- **`.

**Acceptance:** reports render readable markdown, no broken pipes, no missing fields.

---

## Phase 8 — Discovery entrypoint

### 8.1 `discovery/run.py`

```python
import logging, sys
from pathlib import Path
import json
from discovery.config_loader import load_discovery_config
from discovery.sources import all_sources
from discovery.filters import evaluate
from discovery.reporter import write_reports
from discovery.models import Company

log = logging.getLogger(__name__)

def main(argv=None):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    cfg = load_discovery_config()
    enabled_hard = cfg["discovery"].get("enable_hard_sources", False)
    sources = all_sources(cfg, include_hard=enabled_hard)
    out_path = Path(cfg["discovery"]["companies_file"])
    out_path.parent.mkdir(parents=True, exist_ok=True)

    all_companies: list[Company] = []
    cap = cfg["discovery"]["max_companies_total"]

    for src in sources:
        log.info("Source %s starting", src.name)
        try:
            for company in src.run():
                # post-filter
                text = f"{company.name}. {company.ai_focus}. {' '.join(company.sectors)}"
                fr = evaluate(text)
                if not fr.passes_tier1:
                    continue
                if fr.confidence == "low":
                    company.notes = "tier-1 only, low confidence"
                all_companies.append(company)
                if len(all_companies) >= cap:
                    log.warning("Hit cap of %d companies", cap)
                    break
            log.info("Source %s done, total so far: %d", src.name, len(all_companies))
        except Exception as e:
            log.error("Source %s crashed: %s", src.name, e)
            continue
        if len(all_companies) >= cap:
            break

    # write companies.json
    out_path.write_text(json.dumps([c.to_json() for c in all_companies], indent=2, ensure_ascii=False), encoding="utf-8")
    write_reports(all_companies, cfg["discovery"]["output_dir"])
    log.info("Wrote %d companies → %s and reports → %s", len(all_companies), out_path, cfg["discovery"]["output_dir"])

if __name__ == "__main__":
    sys.exit(main())
```

### 8.2 `discovery/sources/__init__.py`

```python
def all_sources(cfg, include_hard=False):
    from .eu_startups import EUStartupsSource
    from .yc_companies import YCCompaniesSource
    from .berlin_ai_map import BerlinAIMapSource
    from .bayern_innovativ import BayernInnovativSource
    from .deutsche_startups import DeutscheStartupsSource
    from .plug_and_play_munich import PlugAndPlayMunichSource
    from .ai_made_in_germany import AIMadeInGermanySource
    from .tech_eu import TechEUSource
    out = []
    sc = cfg["discovery"]["sources"]
    if sc["eu_startups"]["enabled"]: out.append(EUStartupsSource(cfg))
    if sc["yc_companies"]["enabled"]: out.append(YCCompaniesSource(cfg))
    if sc["berlin_ai_map"]["enabled"]: out.append(BerlinAIMapSource(cfg))
    if sc["bayern_innovativ"]["enabled"]: out.append(BayernInnovativSource(cfg))
    if sc["deutsche_startups"]["enabled"]: out.append(DeutscheStartupsSource(cfg))
    if sc["plug_and_play_munich"]["enabled"]: out.append(PlugAndPlayMunichSource(cfg))
    if sc["ai_made_in_germany"]["enabled"]: out.append(AIMadeInGermanySource(cfg))
    if sc["tech_eu"]["enabled"]: out.append(TechEUSource(cfg))
    if include_hard:
        from .sifted import SiftedSource
        from .google_news import GoogleNewsSource
        from .hn_hiring import HNHiringSource
        if sc["sifted"]["enabled"]: out.append(SiftedSource(cfg))
        if sc["google_news_de"]["enabled"]: out.append(GoogleNewsSource(cfg, geo="DE"))
        if sc["google_news_en"]["enabled"]: out.append(GoogleNewsSource(cfg, geo="EN"))
        if sc["hn_who_is_hiring"]["enabled"]: out.append(HNHiringSource(cfg))
    return out
```

### 8.3 Test — end-to-end

`tests/discovery/test_run_smoke.py` — mock `requests.get` for one EASY source returning a fixture HTML, run `main()` against a tmp config, assert `companies.json` written, `01-germany.md` written.

**Acceptance:** `python -m discovery.run` runs end-to-end on real network for at least 2 EASY sources, produces ≥ 50 companies, no uncaught exceptions.

---

## Phase 9 — Jobs scraper

### 9.1 `jobs/models.py`

`Job` dataclass per spec § Data model.

### 9.2 `jobs/filters.py`

Reuse `discovery/filters.py` Tier-1 logic on `role_title` + job description.

```python
DE_EU_COUNTRIES = {"DE", "AT", "CH", "NL", "FR", "ES", "IT", "PL", "SE", "DK", "FI", "NO", "BE", "IE", "PT", "CZ"}
ROLE_TITLE_AI_KW = ["machine learning", "ml engineer", "ai engineer", "research engineer",
                    "computational engineer", "simulation engineer", "data scientist"]

def is_ai_eng_role(title: str, desc: str) -> bool:
    title_l = title.lower()
    if not any(kw in title_l for kw in ROLE_TITLE_AI_KW):
        return False
    fr = evaluate(f"{title} {desc}")
    return fr.passes_tier1

def is_de_eu(country: str | None) -> bool:
    return country in DE_EU_COUNTRIES if country else False
```

### 9.3 `jobs/sources/careers_page.py`

For each company in `companies.json`:
- Fetch `homepage`. Look for "/careers", "/jobs", "/karriere".
- If found, fetch that page. Try generic parsers (Greenhouse, Lever, Workable, Personio, SmartRecruiters).
- Detection by domain: `boards.greenhouse.io/<slug>`, `jobs.lever.co/<slug>`, etc.
- If unknown template, fall back to LLM extract on the page text.

### 9.4 `jobs/sources/stepstone.py`, `wellfound.py`, `otta.py`

Each is a custom parser. Spec lists representative URLs; implementer verifies query params at impl time.

- StepStone search: `https://www.stepstone.de/jobs/?ke=AI+Engineer&ws=Germany`
- Wellfound: `https://wellfound.com/jobs?query=ml+engineer&location_id[]=germany`
- Otta: `https://app.otta.com/jobs/all?genericSubFunction[]=ml-engineer`

### 9.5 `jobs/sources/hn_hiring.py`

Same as discovery's HN-hiring source, but emits Job records (one per comment that has a clear role offer).

### 9.6 `jobs/run.py`

```python
def main():
    cfg = load_discovery_config()
    if not cfg["jobs"]["enabled"]:
        log.info("Jobs scraper disabled in config")
        return 0
    companies = load_companies(cfg["discovery"]["companies_file"])
    jobs: list[Job] = []
    for src in jobs_sources(cfg, companies):
        for job in src.run():
            if not is_ai_eng_role(job.role_title, job.notes or ""):
                continue
            if not is_de_eu(job.country):
                continue
            jobs.append(job)
    write_jobs(jobs, cfg["jobs"]["output_file"], cfg["jobs"]["report_file"])
```

### 9.7 Tests

- `test_is_ai_eng_role` — title "ML Engineer" + desc with "structural mechanics" → True.
- `test_is_ai_eng_role_excludes_marketing` — title "Marketing Manager" → False.
- `test_is_de_eu` — DE/AT/CH → True; US → False.
- `test_careers_page_greenhouse_parser` — fixture Greenhouse JSON → list of Jobs parsed.
- `test_stepstone_parser` — fixture HTML → Jobs parsed with country=DE.

**Acceptance:** `python -m jobs.run` against a fixture `companies.json` produces non-empty `data/jobs.json` for ≥ 5 DE/EU AI-eng roles.

---

## Phase 10 — Verification + handoff

### 10.1 Smoke test (manual)

1. `pytest -q` — all green.
2. `python -m discovery.run` with EASY sources only → expect ≥ 100 companies in 30 min.
3. Inspect `data/reports/01-germany.md` — sanity check 5 entries by hand.
4. Flip `enable_hard_sources: true`, rerun — expect ≥ 200 companies in 1.5-2.5 h.
5. Crash mid-run (Ctrl+C), restart → checkpoint resume works.
6. `python -m jobs.run` → expect ≥ 30 DE/EU jobs in `data/jobs.json`.

### 10.2 Handoff to VPS agent

- Commit spec + plan files to git.
- Push to GitHub.
- VPS agent (GPT-5.4) pulls repo, reads spec + plan, implements phase by phase.
- Each phase commit on its own branch / PR for review.

### 10.3 Renaming (post-handoff)

After VPS agent finishes Phase 10, do discrete commit:
- Rename GitHub repo `weekly-digest` → `ai-eng-tracker`.
- Update `README.md` heading.
- Update `CLAUDE.md` project name reference.
- Local: `git remote set-url origin git@github.com:Sumanthreddy-DE/ai-eng-tracker.git`.

---

## Out-of-scope safeguards

- Do NOT modify `collector/`, `summarizer/`, `formatter/`, `sender/`, `state/`, `lock/`, `main.py`. They stay paused, intact.
- Do NOT touch existing 43 tests. They must remain green throughout.
- Do NOT add Apify code paths. Token stays in `.env` for future revisit only.
- Do NOT add SMTP send / email render code paths.

---

## Risk register

| Risk | Mitigation |
|---|---|
| Source HTML structure changes | Per-source try/except; mark `failed`, keep going. Fix selector at next run. |
| Ollama returns malformed JSON | One retry with stricter prompt; on second fail, log raw and skip. |
| Long scrape times out network | Per-source 30-min timeout from config. |
| German keyword too broad → noise | Tier-2 confidence score downgrades to `low`, surfaces in `notes` for manual review. |
| YC / EU-Startups rate-limit / block | 2-sec delay; user-agent string; if blocked, mark source `failed`. |
| Disk fills with checkpoints | Cleaned at start of each fresh run (or by hand). |
| Hard sources too slow | Default `enable_hard_sources: false`. User opts in. |

---

## Implementation order summary

1. Phase 0 — repo prep
2. Phase 1 — models, checkpoint, config
3. Phase 2 — filters
4. Phase 3 — Ollama extractor
5. Phase 4 — first source (EU-Startups)
6. Phase 5 — remaining EASY/MEDIUM sources
7. Phase 6 — HARD sources (gated)
8. Phase 7 — reporter
9. Phase 8 — discovery entrypoint + smoke test
10. Phase 9 — jobs scraper
11. Phase 10 — verification + handoff
12. (post) — rename repo
