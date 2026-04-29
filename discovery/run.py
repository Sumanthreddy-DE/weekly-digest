from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

from discovery.config_loader import load_discovery_config
from discovery.reporter import write_reports

log = logging.getLogger(__name__)


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    cfg = load_discovery_config()
    out_path = Path(cfg["discovery"]["companies_file"])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps([], indent=2), encoding="utf-8")
    write_reports([], cfg["discovery"]["output_dir"])
    log.info("Discovery scaffold ready. No sources implemented yet.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
