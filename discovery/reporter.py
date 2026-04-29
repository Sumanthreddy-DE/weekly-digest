from __future__ import annotations

from pathlib import Path

from discovery.models import Company


def write_reports(companies: list[Company], output_dir: str) -> None:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    de_companies = [company for company in companies if company.geo_tier == "DE"]
    eu_companies = [company for company in companies if company.geo_tier == "EU"]
    global_companies = [company for company in companies if company.geo_tier == "GLOBAL"]

    _write_de_deep(de_companies, out_dir / "01-germany.md")
    _write_eu_scan(eu_companies, out_dir / "02-european-union.md")
    _write_global_ref(global_companies, out_dir / "03-global.md")


def _write_de_deep(companies: list[Company], path: Path) -> None:
    lines = ["# Germany - Deep Tier", ""]
    for company in companies:
        lines.extend(
            [
                f"## {company.name}",
                f"- **Homepage**: {company.homepage or 'unknown'}",
                f"- **City**: {company.city or 'unknown'}",
                f"- **Sectors**: {', '.join(company.sectors) or 'unknown'}",
                f"- **AI focus**: {company.ai_focus}",
                f"- **Sources**: {', '.join(source.url for source in company.sources) or 'unknown'}",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_eu_scan(companies: list[Company], path: Path) -> None:
    lines = [
        "# European Union - Scan Tier",
        "",
        "| Name | Country | Sectors | Homepage | Source |",
        "|---|---|---|---|---|",
    ]
    for company in companies:
        sectors = ", ".join(company.sectors[:3]) or "-"
        source = company.sources[0].url if company.sources else "-"
        lines.append(
            f"| {company.name} | {company.country or '-'} | {sectors} | {company.homepage or '-'} | {source} |"
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_global_ref(companies: list[Company], path: Path) -> None:
    lines = ["# Global - Reference Tier", ""]
    for company in companies:
        sectors = ", ".join(company.sectors[:2]) or "-"
        lines.append(f"- **{company.name}** ({sectors}) - {company.homepage or 'unknown'}")
    path.write_text("\n".join(lines), encoding="utf-8")
