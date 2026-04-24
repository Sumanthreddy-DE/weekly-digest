# Deployment Guide

## Prerequisites

- Python 3.11+ on VPS (same VPS running OpenClaw)
- Gmail account with App Password: Google Account -> Security -> 2-Step Verification -> App Passwords
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

```bash
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

```bash
0 8 * * 0 cd /path/to/weekly-digest && set -a && . ./.env && set +a && python main.py >> logs/digest.log 2>&1
```

Runs every Sunday at 8:00 AM server time.

## Manual test run

```bash
set -a && . ./.env && set +a && python main.py
```

## Monitoring

- Logs: `logs/digest.log`
- Fallback digests: `logs/digest-YYYY-MM-DD.html` (created when SMTP fails)
- State: `data/state.json` (human-readable JSON)
- If state corrupted: restore `data/state.json.bak`
