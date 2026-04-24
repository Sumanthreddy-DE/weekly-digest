import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import yaml

from collector.job_intel import fetch_job_intel
from collector.newsletters import fetch_newsletters
from formatter.email_builder import build_email
from lock.run_lock import LockHeldError, acquire_lock
from sender.smtp import send_email
from state.ledger import add_items, get_pending, load_state, mark_delivered, prune_state, save_state
from summarizer.openclaw import summarize_job_intel, summarize_newsletters

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s , %(message)s",
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

    pending = get_pending(state)
    log.info("Stage 0: %d pending items from prior run", len(pending))

    newsletters = fetch_newsletters(config, state)
    log.info("Stage 1: %d new newsletters", len(newsletters))

    job_intel = fetch_job_intel(config, state)
    log.info("Stage 2: %d new job intel items", len(job_intel))

    all_new = newsletters + job_intel
    state = add_items(state, all_new)
    save_state(state_path, marker_path, state)

    nl_batch = [i for i in pending if i.get("type") == "newsletter"] + newsletters
    ji_batch = [i for i in pending if i.get("type") == "job_intel"] + job_intel

    nl_summaries = summarize_newsletters(nl_batch, config)
    ji_summaries = summarize_job_intel(ji_batch, config)
    log.info("Stage 3: %d nl summaries, %d intel summaries", len(nl_summaries), len(ji_summaries))

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
