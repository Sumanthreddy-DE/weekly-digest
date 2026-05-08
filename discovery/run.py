from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

from discovery.config_loader import load_discovery_config
from discovery.filters import evaluate
from discovery.reporter import write_reports
from discovery.sources import all_sources

log = logging.getLogger(__name__)


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    config_path = argv[0] if argv else "config.yaml"
    cfg = load_discovery_config(config_path)
    sources = all_sources(cfg, include_hard=cfg["discovery"].get("enable_hard_sources", False))
    out_path = Path(cfg["discovery"]["companies_file"])
    out_path.parent.mkdir(parents=True, exist_ok=True)

    companies = []
    cap = cfg["discovery"]["max_companies_total"]
    for source in sources:
        log.info("Source %s starting", source.name)
        try:
            for company in source.run():
                text = f"{company.name}. {company.ai_focus}. {' '.join(company.sectors)}"
                result = evaluate(text)
                if not result.passes_tier1:
                    continue
                if result.confidence == "low":
                    company.notes = "tier-1 only, low confidence"
                companies.append(company)
                if len(companies) >= cap:
                    log.warning("Hit cap of %d companies", cap)
                    break
        except Exception as exc:
            log.error("Source %s crashed: %s", source.name, exc)
        if len(companies) >= cap:
            break

    out_path.write_text(
        json.dumps([company.to_json() for company in companies], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    write_reports(companies, cfg["discovery"]["output_dir"])
    log.info("Wrote %d companies to %s", len(companies), out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
