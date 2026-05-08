from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Checkpoint:
    source: str
    started_at: str
    last_completed_page: int
    last_completed_url: Optional[str]
    items_emitted: int
    status: str
    error: Optional[str] = None


def checkpoint_path(checkpoint_dir: str, source: str) -> Path:
    return Path(checkpoint_dir) / f"{source}.json"


def read_checkpoint(checkpoint_dir: str, source: str) -> Optional[Checkpoint]:
    path = checkpoint_path(checkpoint_dir, source)
    if not path.exists():
        return None
    return Checkpoint(**json.loads(path.read_text()))


def write_checkpoint(checkpoint_dir: str, checkpoint: Checkpoint) -> None:
    path = checkpoint_path(checkpoint_dir, checkpoint.source)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(asdict(checkpoint), handle, indent=2)
        os.replace(tmp_path, path)
    except Exception:
        if Path(tmp_path).exists():
            Path(tmp_path).unlink()
        raise
