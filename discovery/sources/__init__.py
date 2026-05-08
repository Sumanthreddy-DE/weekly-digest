from discovery.sources.ai_made_in_germany import AIMadeInGermanySource
from discovery.sources.bayern_innovativ import BayernInnovativSource
from discovery.sources.berlin_ai_map import BerlinAIMapSource
from discovery.sources.deutsche_startups import DeutscheStartupsSource
from discovery.sources.eu_startups import EUStartupsSource
from discovery.sources.google_news import GoogleNewsSource
from discovery.sources.hn_hiring import HNHiringSource
from discovery.sources.plug_and_play_munich import PlugAndPlayMunichSource
from discovery.sources.sifted import SiftedSource
from discovery.sources.tech_eu import TechEUSource
from discovery.sources.yc_companies import YCCompaniesSource


def all_sources(cfg: dict, include_hard: bool = False):
    sources = []
    source_cfg = cfg["discovery"]["sources"]
    if source_cfg.get("eu_startups", {}).get("enabled"):
        sources.append(EUStartupsSource(cfg))
    if source_cfg.get("yc_companies", {}).get("enabled"):
        sources.append(YCCompaniesSource(cfg))
    if source_cfg.get("berlin_ai_map", {}).get("enabled"):
        sources.append(BerlinAIMapSource(cfg))
    if source_cfg.get("bayern_innovativ", {}).get("enabled"):
        sources.append(BayernInnovativSource(cfg))
    if source_cfg.get("deutsche_startups", {}).get("enabled"):
        sources.append(DeutscheStartupsSource(cfg))
    if source_cfg.get("plug_and_play_munich", {}).get("enabled"):
        sources.append(PlugAndPlayMunichSource(cfg))
    if source_cfg.get("ai_made_in_germany", {}).get("enabled"):
        sources.append(AIMadeInGermanySource(cfg))
    if source_cfg.get("tech_eu", {}).get("enabled"):
        sources.append(TechEUSource(cfg))
    if include_hard:
        if source_cfg.get("sifted", {}).get("enabled"):
            sources.append(SiftedSource(cfg))
        if source_cfg.get("google_news_de", {}).get("enabled"):
            sources.append(GoogleNewsSource(cfg, geo="DE"))
        if source_cfg.get("google_news_en", {}).get("enabled"):
            sources.append(GoogleNewsSource(cfg, geo="EN"))
        if source_cfg.get("hn_who_is_hiring", {}).get("enabled"):
            sources.append(HNHiringSource(cfg))
    return sources
