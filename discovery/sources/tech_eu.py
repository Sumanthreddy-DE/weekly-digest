from discovery.sources.base import SourceBase


class TechEUSource(SourceBase):
    name = "tech_eu"
    geo_tier = "EU"
    extractor = "custom-tech-eu"

    def iter_pages(self, start_page: int):
        return iter(())
