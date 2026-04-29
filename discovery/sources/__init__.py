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
    if source_cfg["eu_startups"]["enabled"]:
        sources.append(EUStartupsSource(cfg))
    if source_cfg["yc_companies"]["enabled"]:
        sources.append(YCCompaniesSource(cfg))
    if source_cfg["berlin_ai_map"]["enabled"]:
        sources.append(BerlinAIMapSource(cfg))
    if source_cfg["bayern_innovativ"]["enabled"]:
        sources.append(BayernInnovativSource(cfg))
    if source_cfg["deutsche_startups"]["enabled"]:
        sources.append(DeutscheStartupsSource(cfg))
    if source_cfg["plug_and_play_munich"]["enabled"]:
        sources.append(PlugAndPlayMunichSource(cfg))
    if source_cfg["ai_made_in_germany"]["enabled"]:
        sources.append(AIMadeInGermanySource(cfg))
    if source_cfg["tech_eu"]["enabled"]:
        sources.append(TechEUSource(cfg))
    if include_hard:
        if source_cfg["sifted"]["enabled"]:
            sources.append(SiftedSource(cfg))
        if source_cfg["google_news_de"]["enabled"]:
            sources.append(GoogleNewsSource(cfg, geo="DE"))
        if source_cfg["google_news_en"]["enabled"]:
            sources.append(GoogleNewsSource(cfg, geo="EN"))
        if source_cfg["hn_who_is_hiring"]["enabled"]:
            sources.append(HNHiringSource(cfg))
    return sources
