from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

from discovery.config_loader import load_discovery_config
from jobs.filters import is_ai_eng_role, is_de_eu
from jobs.sources.careers_page import CareersPageSource
from jobs.sources.hn_hiring import HNHiringJobsSource
from jobs.sources.otta import OttaSource
from jobs.sources.stepstone import StepStoneSource
from jobs.sources.wellfound import WellfoundSource

log = logging.getLogger(__name__)


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    config_path = argv[0] if argv else "config.yaml"
    cfg = load_discovery_config(config_path)
    if not cfg["jobs"]["enabled"]:
        log.info("Jobs scraper disabled in config")
        return 0

    companies_path = Path(cfg["discovery"]["companies_file"])
    companies = json.loads(companies_path.read_text()) if companies_path.exists() else []

    sources = []
    source_cfg = cfg["jobs"]["sources"]
    if source_cfg["careers_pages"]["enabled"]:
        sources.append(CareersPageSource(cfg, companies))
    if source_cfg["stepstone"]["enabled"]:
        sources.append(StepStoneSource(cfg))
    if source_cfg["wellfound"]["enabled"]:
        sources.append(WellfoundSource(cfg))
    if source_cfg["otta"]["enabled"]:
        sources.append(OttaSource(cfg))
    if source_cfg["hn_hiring"]["enabled"]:
        sources.append(HNHiringJobsSource(cfg))

    jobs = []
    for source in sources:
        for job in source.run():
            if not is_ai_eng_role(job.role_title, job.notes or ""):
                continue
            if not is_de_eu(job.country):
                continue
            jobs.append(job)

    out_path = Path(cfg["jobs"]["output_file"])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps([job.to_json() for job in jobs], indent=2), encoding="utf-8")
    report_path = Path(cfg["jobs"]["report_file"])
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Jobs - DE/EU", "", "| Company | Role | Country | URL |", "|---|---|---|---|"]
    for job in jobs:
        lines.append(f"| {job.company_name} | {job.role_title} | {job.country or '-'} | {job.url} |")
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log.info("Wrote %d jobs to %s", len(jobs), out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
