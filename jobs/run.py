from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

from discovery.config_loader import load_discovery_config

log = logging.getLogger(__name__)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    cfg = load_discovery_config()
    if not cfg["jobs"]["enabled"]:
        log.info("Jobs scraper disabled in config")
        return 0
    out_path = Path(cfg["jobs"]["output_file"])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps([], indent=2), encoding="utf-8")
    report_path = Path(cfg["jobs"]["report_file"])
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("# Jobs - DE/EU\n", encoding="utf-8")
    log.info("Jobs scaffold ready. No sources implemented yet.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
