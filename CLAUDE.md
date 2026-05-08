# Project: ai-eng-tracker (formerly weekly-digest)

AI-in-engineering company + jobs tracker. Discovery sources (EU-Startups, YC, Berlin AI map, Bayern Innovativ, Deutsche Startups, Plug and Play Munich, AI Made in Germany, Tech.eu, HN Who is Hiring, Google News DE/EN, Sifted) -> tiered companies list (DE/EU/Global) + DE/EU jobs scraper (careers pages, StepStone, Wellfound, Otta, HN). Runs locally during dev; VPS cron later. Repo renamed 2026-05-07; folder still `weekly-digest` on disk.

**Paused:** original newsletter weekly-digest pipeline (collector, summarizer, formatter, sender, state, lock, main.py). Code retained on disk, not invoked.

## Project-specific overrides

- **Use `imaplib` + `smtplib` (stdlib), NOT `gws` CLI.** App Password is simpler for cron deployment on VPS — no OAuth flow, no token refresh, no browser dependency. The user-global Rulebook says "gmail tasks -> use gws-gmail skills" — that rule does NOT apply in this project. Stick with `imaplib` unless it breaks; only then revisit gws.
- **OpenClaw runs 24/7 on user's VPS.** Endpoint configured via `OPENCLAW_BASE_URL` env var. Ollama-compatible `/api/generate` API.

## Status (2026-04-29)

- Phase 1 build complete. 43/43 tests passing locally on Windows.
- Pre-deployment. Awaiting: Apify token, Gmail App Password, newsletter sender list.
- Target first run: Sunday 2026-05-03.

## Key files

- `main.py` — pipeline orchestrator (5 stages + replay)
- `collector/` — Gmail IMAP, Apify, RSS fallback
- `summarizer/openclaw.py` — LLM with retry/timeout/extractive fallback
- `formatter/email_builder.py` + `digest_template.html` — Jinja2 HTML
- `sender/smtp.py` — Gmail SMTP, fallback to local HTML on failure
- `state/ledger.py` — single-file `state.json`, atomic writes, `.bak` recovery
- `lock/run_lock.py` — cross-platform exclusive lock, sidecar `.meta` for PID/timestamp
- `config.yaml` — all config (env vars expanded at load)
- `docs/specs/2026-04-20-newsletter-weekly-digest-design.md` — source-of-truth design
- `docs/superpowers/plans/2026-04-24-weekly-digest.md` — implementation plan
- `docs/deployment.md` — VPS setup + cron

## Secrets (env vars only — never commit)

- `GMAIL_EMAIL`
- `GMAIL_APP_PASSWORD`
- `OPENCLAW_BASE_URL`
- `APIFY_API_TOKEN`
- `DIGEST_SEND_TO`

## Run

```bash
python -m pip install -r requirements.txt
set -a && . ./.env && set +a && python main.py
```

## Test

```bash
pytest -q
```
