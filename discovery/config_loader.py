from __future__ import annotations

from main import load_config


REQUIRED_TOP_LEVEL_KEYS = {"discovery", "jobs"}


def load_discovery_config(path: str = "config.yaml") -> dict:
    config = load_config(path)
    missing = [key for key in REQUIRED_TOP_LEVEL_KEYS if key not in config]
    if missing:
        raise ValueError(f"config.yaml missing required sections: {', '.join(sorted(missing))}")
    return config
