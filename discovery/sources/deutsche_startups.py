from discovery.sources.base import SourceBase


class DeutscheStartupsSource(SourceBase):
    name = "deutsche_startups"
    geo_tier = "DE"
    extractor = "custom-deutsche-startups"

    def iter_pages(self, start_page: int):
        return iter(())
