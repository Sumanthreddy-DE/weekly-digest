import json
import logging
import os
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path

log = logging.getLogger(__name__)


def load_state(state_path: str, marker_path: str) -> dict:
    def _try_load(path: str):
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
    json.loads(Path(tmp).read_text())
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
            and datetime.fromisoformat(item["delivered_at"].replace("Z", "+00:00")) < cutoff
        )
    ]
    return {**state, "items": kept}
